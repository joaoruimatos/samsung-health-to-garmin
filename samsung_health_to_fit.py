#!/usr/bin/env python3
"""Convert Samsung Health exported exercise data into Garmin-compatible FIT files.

This script is based on and adapted from the data-reading/merging approach used by
FromSamToGarm's exercises.py (https://github.com/PhilippImhof/FromSamToGarm), but
writes FIT Activity files using Garmin's official Python FIT SDK.

License: GPL-3.0-only (see LICENSE in this repository).

Requirements:
    Python 3.9+ recommended
    garmin-fit-sdk >= 21.200.0,<22  (Encoder was added in 21.200.0)

Run this script from the root of an extracted Samsung Health export, or pass
--source to that folder. The expected Samsung layout is roughly:

    com.samsung.shealth.exercise.<id>.csv
    jsons/com.samsung.shealth.exercise/<first-char-of-uuid>/
        <uuid>.com.samsung.health.exercise.location_data.json
        <uuid>.com.samsung.health.exercise.live_data.json

The source Samsung export is never modified.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import json
import math
import re
import sys
import zlib
from pathlib import Path
from typing import Any, Iterable

# Garmin's FIT SDK is loaded lazily so reference-only commands (for example
# --list-types) and CSV-detection tests can run without importing the SDK.
# Actual FIT encoding/verification still requires garmin-fit-sdk >= 21.200.0.
Decoder = None
Encoder = None
Stream = None
Profile = None
FIT_EPOCH_S = 631065600  # FIT epoch offset from Unix epoch, in seconds.


def load_fit_sdk() -> None:
    """Load Garmin's official FIT Python SDK when FIT work is requested."""
    global Decoder, Encoder, Stream, Profile, FIT_EPOCH_S
    if Encoder is not None and Decoder is not None and Stream is not None and Profile is not None:
        return

    try:
        from garmin_fit_sdk import Decoder as _Decoder, Encoder as _Encoder, FIT_EPOCH_S as _FIT_EPOCH_S, Stream as _Stream
        from garmin_fit_sdk.profile import Profile as _Profile
    except (ImportError, AttributeError) as exc:
        raise ConversionError(
            "Garmin FIT SDK with Encoder support is required.\n"
            "Install the project dependencies in PowerShell with:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
            "or directly with:\n"
            '  py -m pip install --upgrade "garmin-fit-sdk>=21.200.0,<22"\n'
            f"Original import error: {exc}"
        ) from exc

    Decoder = _Decoder
    Encoder = _Encoder
    Stream = _Stream
    Profile = _Profile
    FIT_EPOCH_S = _FIT_EPOCH_S


# ---------------------------------------------------------------------------
# Samsung exercise type -> FIT sport / sub_sport mapping.
#
# Some Samsung types are more specific than FIT's sport/sub_sport model.
# In those cases this table chooses the closest Garmin category.
# You can edit this table if you prefer a different Garmin classification.
# ---------------------------------------------------------------------------
SAMSUNG_TO_FIT: dict[str, tuple[str, str, str]] = {
    "1001": ("Walking", "walking", "generic"),
    "1002": ("Running", "running", "generic"),
    "10006": ("Sit-ups", "training", "strength_training"),
    "10007": ("Circuit training, moderate effort", "training", "cardio_training"),
    "11007": ("Cycling", "cycling", "generic"),
    "13001": ("Hiking", "hiking", "generic"),
    "14001": ("Swimming, general (not lap swimming)", "swimming", "generic"),
    "15002": ("Weight machine", "training", "strength_training"),
    "15003": ("Exercise bike", "cycling", "indoor_cycling"),
    "15005": ("Treadmill (jogging/walking)", "running", "treadmill"),
}

# ---------------------------------------------------------------------------
# SUGGESTED REFERENCE MAPPINGS FOR OTHER DOCUMENTED SAMSUNG NUMERIC IDS
#
# These are intentionally COMMENTED OUT and are NOT enabled by default.
# They were matched against Samsung's legacy numeric EXERCISE_TYPE table and
# Garmin FIT's published sport/sub_sport enums. Many are exact names, but some
# are only the closest available Garmin category. Test before bulk importing.
#
# Samsung source:
#   https://developer.samsung.com/health/android/data/api-reference/EXERCISE_TYPE.html
# Garmin FIT profile source:
#   https://github.com/garmin/fit-python-sdk/blob/main/garmin_fit_sdk/profile.py
#
# Confidence labels:
#   exact       - Garmin has a direct sport/sub_sport equivalent
#   close       - very similar Garmin category, but not identical
#   approximate - no direct Garmin equivalent; semantic fallback
#   custom      - Samsung custom type; inspect the custom title/type yourself
#
# To enable one, copy/uncomment the dictionary entry into SAMSUNG_TO_FIT above.
# ---------------------------------------------------------------------------
# "0": ("Custom type", "generic", "generic"),  # custom
# "2001": ("Baseball, general", "baseball", "generic"),  # exact
# "2002": ("Softball, general", "baseball", "generic"),  # close
# "2003": ("Cricket", "cricket", "generic"),  # exact
# "3001": ("Golf, general", "golf", "generic"),  # exact
# "3002": ("Billiards", "generic", "generic"),  # approximate
# "3003": ("Bowling, alley", "generic", "generic"),  # approximate
# "4001": ("Hockey", "hockey", "generic"),  # close
# "4002": ("Rugby, touch, non-competitive", "rugby", "generic"),  # exact
# "4003": ("Basketball, general", "basketball", "generic"),  # exact
# "4004": ("Football, general (Soccer)", "soccer", "generic"),  # exact
# "4005": ("Handball, general", "team_sport", "generic"),  # approximate
# "4006": ("American football, general, touch", "american_football", "generic"),  # exact
# "5001": ("Volleyball, general", "volleyball", "generic"),  # exact
# "5002": ("Beach volleyball", "volleyball", "generic"),  # close
# "6001": ("Squash, general", "racket", "squash"),  # exact
# "6002": ("Tennis, general", "tennis", "generic"),  # exact
# "6003": ("Badminton, competitive", "racket", "badminton"),  # exact
# "6004": ("Table tennis", "racket", "table_tennis"),  # exact
# "6005": ("Racquetball, general", "racket", "racquetball"),  # exact
# "7001": ("T'ai chi, general (deprecated)", "training", "flexibility_training"),  # approximate
# "7002": ("Boxing, in ring", "boxing", "generic"),  # exact
# "7003": ("Martial arts, moderate pace", "mixed_martial_arts", "generic"),  # close
# "8001": ("Ballet, general", "dance", "generic"),  # close
# "8002": ("Dancing, general", "dance", "generic"),  # exact
# "8003": ("Ballroom dancing, fast", "dance", "generic"),  # close
# "9001": ("Pilates", "fitness_equipment", "pilates"),  # exact
# "9002": ("Yoga", "training", "yoga"),  # exact
# "10001": ("Stretching", "training", "flexibility_training"),  # exact
# "10002": ("Jump rope, moderate pace", "jump_rope", "generic"),  # exact
# "10003": ("Hula-hooping", "training", "cardio_training"),  # approximate
# "10004": ("Push-ups (Press-ups)", "training", "strength_training"),  # close
# "10005": ("Pull-ups (Chin-up)", "training", "strength_training"),  # close
# "10008": ("Mountain climbers", "training", "cardio_training"),  # approximate
# "10009": ("Jumping Jacks", "training", "cardio_training"),  # approximate
# "10010": ("Burpee", "hiit", "generic"),  # close
# "10011": ("Bench press", "training", "strength_training"),  # close
# "10012": ("Squats", "training", "strength_training"),  # close
# "10013": ("Lunges", "training", "strength_training"),  # close
# "10014": ("Leg presses", "training", "strength_training"),  # close
# "10015": ("Leg extensions", "training", "strength_training"),  # close
# "10016": ("Leg curls", "training", "strength_training"),  # close
# "10017": ("Back extensions", "training", "strength_training"),  # close
# "10018": ("Lat pull-downs", "training", "strength_training"),  # close
# "10019": ("Deadlifts", "training", "strength_training"),  # close
# "10020": ("Shoulder presses", "training", "strength_training"),  # close
# "10021": ("Front raises", "training", "strength_training"),  # close
# "10022": ("Lateral raises", "training", "strength_training"),  # close
# "10023": ("Crunches", "training", "strength_training"),  # close
# "10024": ("Leg raises", "training", "strength_training"),  # close
# "10025": ("Plank", "training", "strength_training"),  # close
# "10026": ("Arm curls", "training", "strength_training"),  # close
# "10027": ("Arm extensions", "training", "strength_training"),  # close
# "11001": ("Inline skating, moderate pace", "inline_skating", "generic"),  # exact
# "11002": ("Hang gliding", "hang_gliding", "generic"),  # exact
# "11003": ("Pistol shooting", "shooting", "generic"),  # close
# "11004": ("Archery, non-hunting", "archery", "generic"),  # exact
# "11005": ("Horseback riding, general", "horseback_riding", "generic"),  # exact
# "11008": ("Flying disc, general, playing", "generic", "generic"),  # approximate
# "11009": ("Roller skating", "inline_skating", "generic"),  # approximate
# "12001": ("Aerobics, general", "training", "cardio_training"),  # close
# "13002": ("Rock climbing, low to moderate difficulty", "rock_climbing", "generic"),  # exact
# "13003": ("Backpacking", "hiking", "rucking"),  # close
# "13004": ("Mountain biking, general", "cycling", "mountain"),  # exact
# "13005": ("Orienteering", "running", "navigate"),  # approximate
# "14002": ("Aquarobics", "training", "cardio_training"),  # approximate
# "14003": ("Canoeing, general, for pleasure", "canoeing", "generic"),  # exact
# "14004": ("Sailing, leisure, ocean sailing", "sailing", "generic"),  # exact
# "14005": ("Scuba diving, general", "diving", "generic"),  # close
# "14006": ("Snorkeling", "snorkeling", "generic"),  # exact
# "14007": ("Kayaking, moderate effort", "kayaking", "generic"),  # exact
# "14008": ("Kitesurfing", "kitesurfing", "generic"),  # exact
# "14009": ("Rafting", "rafting", "generic"),  # exact
# "14010": ("Rowing machine, general, for pleasure", "rowing", "indoor_rowing"),  # close
# "14011": ("Windsurfing, general", "windsurfing", "generic"),  # exact
# "14012": ("Yachting, leisure", "sailing", "generic"),  # close
# "14013": ("Water skiing", "water_skiing", "generic"),  # exact
# "15001": ("Step machine", "fitness_equipment", "stair_climbing"),  # exact
# "15004": ("Rowing machine", "rowing", "indoor_rowing"),  # exact
# "15006": ("Elliptical trainer, moderate effort", "fitness_equipment", "elliptical"),  # exact
# "16001": ("Cross-country skiing, general", "cross_country_skiing", "generic"),  # exact
# "16002": ("Skiing, general, downhill, moderate effort", "alpine_skiing", "generic"),  # close
# "16003": ("Ice dancing", "ice_skating", "generic"),  # close
# "16004": ("Ice skating, general", "ice_skating", "generic"),  # exact
# "16006": ("Ice hockey, general", "hockey", "ice"),  # exact
# "16007": ("Snowboarding, general, moderate effort", "snowboarding", "generic"),  # exact
# "16008": ("Alpine skiing, general, moderate effort", "alpine_skiing", "generic"),  # exact
# "16009": ("Snowshoeing, moderate effort", "snowshoeing", "generic"),  # exact

# ---------------------------------------------------------------------------
# SAMSUNG HEALTH DATA SDK NAMED ENUMS — FUTURE REFERENCE ONLY
#
# IMPORTANT: The current Samsung export parser reads LEGACY NUMERIC exercise IDs
# such as "1001", "1002" and "13001". The newer Samsung Health Data SDK uses
# named PredefinedExerciseType enum values instead. These lines are comments only;
# they are NOT parsed or enabled by this converter.
#
# Samsung new enum source:
#   https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/-exercise-type/-predefined-exercise-type/index.html
# Samsung migration example (legacy 1002 -> PredefinedExerciseType.RUNNING):
#   https://developer.samsung.com/health/data/migration-guide/exercise-app-example.html
# Garmin FIT profile source:
#   https://github.com/garmin/fit-python-sdk/blob/main/garmin_fit_sdk/profile.py
#
# Format below:
#   ENUM_NAME -> suggested Garmin sport/sub_sport  [closest legacy ID, confidence]
#
# UNDEFINED                -> generic/generic  [no direct legacy ID, approximate]
# OTHER                    -> generic/generic  [no direct legacy ID, custom]
# WALKING                  -> walking/generic  [1001, exact]
# RUNNING                  -> running/generic  [1002, exact]
# STAIR_CLIMBING           -> floor_climbing/generic  [no direct legacy ID, exact]
# TRACK_RUNNING            -> running/track  [no direct legacy ID, exact]
# BASEBALL                 -> baseball/generic  [2001, exact]
# SOFTBALL                 -> baseball/generic  [2002, close]
# CRICKET                  -> cricket/generic  [2003, exact]
# GOLF                     -> golf/generic  [3001, exact]
# BOWLING                  -> generic/generic  [3003, approximate]
# HOCKEY                   -> hockey/generic  [4001, close]
# RUGBY                    -> rugby/generic  [4002, exact]
# BASKETBALL               -> basketball/generic  [4003, exact]
# SOCCER                   -> soccer/generic  [4004, exact]
# HANDBALL                 -> team_sport/generic  [4005, approximate]
# AMERICAN_FOOTBALL        -> american_football/generic  [4006, exact]
# VOLLEYBALL               -> volleyball/generic  [5001, exact]
# BEACH_VOLLEYBALL         -> volleyball/generic  [5002, close]
# SQUASH                   -> racket/squash  [6001, exact]
# TENNIS                   -> tennis/generic  [6002, exact]
# BADMINTON                -> racket/badminton  [6003, exact]
# TABLE_TENNIS             -> racket/table_tennis  [6004, exact]
# RACQUETBALL              -> racket/racquetball  [6005, exact]
# BOXING                   -> boxing/generic  [7002, exact]
# MARTIAL_ARTS             -> mixed_martial_arts/generic  [7003, close]
# BALLET                   -> dance/generic  [8001, close]
# DANCING                  -> dance/generic  [8002, exact]
# BALLROOM_DANCING         -> dance/generic  [8003, close]
# PILATES                  -> fitness_equipment/pilates  [9001, exact]
# YOGA                     -> training/yoga  [9002, exact]
# STRETCHING               -> training/flexibility_training  [10001, exact]
# JUMP_ROPE                -> jump_rope/generic  [10002, exact]
# HULA_HOOPING             -> training/cardio_training  [10003, approximate]
# PUSH_UPS                 -> training/strength_training  [10004, close]
# PULL_UPS                 -> training/strength_training  [10005, close]
# SIT_UPS                  -> training/strength_training  [10006, close]
# CIRCUIT_TRAINING         -> training/cardio_training  [10007, close]
# MOUNTAIN_CLIMBERS        -> training/cardio_training  [10008, approximate]
# JUMPING_JACKS            -> training/cardio_training  [10009, approximate]
# BURPEES                  -> hiit/generic  [10010, close]
# BENCH_PRESS              -> training/strength_training  [10011, close]
# SQUATS                   -> training/strength_training  [10012, close]
# LUNGES                   -> training/strength_training  [10013, close]
# LEG_PRESSES              -> training/strength_training  [10014, close]
# LEG_EXTENSIONS           -> training/strength_training  [10015, close]
# LEG_CURLS                -> training/strength_training  [10016, close]
# BACK_EXTENSIONS          -> training/strength_training  [10017, close]
# LAT_PULLDOWNS            -> training/strength_training  [10018, close]
# DEADLIFTS                -> training/strength_training  [10019, close]
# SHOULDER_PRESSES         -> training/strength_training  [10020, close]
# FRONT_RAISES             -> training/strength_training  [10021, close]
# LATERAL_RAISES           -> training/strength_training  [10022, close]
# CRUNCH                   -> training/strength_training  [10023, close]
# LEG_RAISES               -> training/strength_training  [10024, close]
# PLANK                    -> training/strength_training  [10025, close]
# ARM_CURLS                -> training/strength_training  [10026, close]
# ARM_EXTENSIONS           -> training/strength_training  [10027, close]
# SKATERS                  -> training/cardio_training  [no direct legacy ID, approximate]
# HIGH_KNEES               -> training/cardio_training  [no direct legacy ID, approximate]
# INLINE_SKATING           -> inline_skating/generic  [11001, exact]
# HANG_GLIDING             -> hang_gliding/generic  [11002, exact]
# ARCHERY                  -> archery/generic  [11004, exact]
# HORSEBACK_RIDING         -> horseback_riding/generic  [11005, exact]
# BIKING                   -> cycling/generic  [11007, exact]
# FLYING_DISC              -> generic/generic  [11008, approximate]
# ROLLER_SKATING           -> inline_skating/generic  [11009, approximate]
# AEROBICS                 -> training/cardio_training  [12001, close]
# HIKING                   -> hiking/generic  [13001, exact]
# ROCK_CLIMBING            -> rock_climbing/generic  [13002, exact]
# BACKPACKING              -> hiking/rucking  [13003, close]
# MOUNTAIN_BIKING          -> cycling/mountain  [13004, exact]
# ORIENTEERING             -> running/navigate  [13005, approximate]
# POOL_SWIMMING            -> swimming/lap_swimming  [no direct legacy ID, close]
# AQUA_AEROBICS            -> training/cardio_training  [14002, approximate]
# CANOEING                 -> canoeing/generic  [14003, exact]
# SAILING                  -> sailing/generic  [14004, exact]
# SCUBA_DIVING             -> diving/generic  [14005, close]
# SNORKELING               -> snorkeling/generic  [14006, exact]
# KAYAKING                 -> kayaking/generic  [14007, exact]
# KITESURFING              -> kitesurfing/generic  [14008, exact]
# RAFTING                  -> rafting/generic  [14009, exact]
# ROWING                   -> rowing/generic  [no direct legacy ID, exact]
# WINDSURFING              -> windsurfing/generic  [14011, exact]
# YACHTING                 -> sailing/generic  [14012, close]
# WATER_SKIING             -> water_skiing/generic  [14013, exact]
# STEP_MACHINE             -> fitness_equipment/stair_climbing  [15001, exact]
# WEIGHT_MACHINE           -> training/strength_training  [15002, close]
# STATIONARY_BIKING        -> cycling/indoor_cycling  [15003, exact]
# ROWING_MACHINE           -> rowing/indoor_rowing  [15004, exact]
# TREADMILL                -> running/treadmill  [15005, close]
# ELLIPTICAL               -> fitness_equipment/elliptical  [15006, exact]
# STAIR_CLIMBING_MACHINE   -> fitness_equipment/stair_climbing  [no direct legacy ID, exact]
# CROSS_COUNTRY_SKIING     -> cross_country_skiing/generic  [16001, exact]
# SKIING                   -> alpine_skiing/generic  [16002, close]
# ICE_DANCING              -> ice_skating/generic  [16003, close]
# ICE_SKATING              -> ice_skating/generic  [16004, exact]
# ICE_HOCKEY               -> hockey/ice  [16006, exact]
# SNOWBOARDING             -> snowboarding/generic  [16007, exact]
# ALPINE_SKIING            -> alpine_skiing/generic  [16008, exact]
# SNOWSHOEING              -> snowshoeing/generic  [16009, exact]
# TRIATHLON                -> multisport/triathlon  [no direct legacy ID, exact]
# DUATHLON                 -> multisport/duathlon  [no direct legacy ID, exact]
# AQUATHLON                -> multisport/swim_run  [no direct legacy ID, close]
# AQUABIKE                 -> multisport/generic  [no direct legacy ID, approximate]
# CROSS_TRIATHLON          -> multisport/triathlon  [no direct legacy ID, close]
# CROSS_DUATHLON           -> multisport/duathlon  [no direct legacy ID, close]
# BREAK                    -> generic/generic  [no direct legacy ID, approximate]
# COOL_DOWN                -> training/generic  [no direct legacy ID, approximate]
# WARM_UP                  -> training/generic  [no direct legacy ID, approximate]
# TRANSITION               -> transition/generic  [no direct legacy ID, exact]
# ZUMBA                    -> dance/generic  [no direct legacy ID, close]
# OPEN_WATER_SWIMMING      -> swimming/open_water  [no direct legacy ID, exact]
#
# See SAMSUNG_EXERCISE_TYPES.md for the same reference as a readable table.
# Do not wire these enum strings into SAMSUNG_TO_FIT until the parser is updated to
# actually read the newer Health Data SDK representation.
# ---------------------------------------------------------------------------
EXERCISE_PREFIX = "com.samsung.health.exercise."


class ConversionError(RuntimeError):
    pass


def finite_number(value: Any) -> float | None:
    """Return a finite float, or None for blanks/invalid/non-finite values."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in {"null", "none", "nan"}:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def positive_number(value: Any) -> float | None:
    number = finite_number(value)
    if number is None or number <= 0:
        return None
    return number


def first_value(row: dict[str, str], *names: str, default: str = "") -> str:
    """Get the first present column from a Samsung CSV row."""
    for name in names:
        if name in row:
            value = row[name]
            return "" if value is None else value.strip()
    return default


def truthy_reference(value: Any) -> bool:
    """Samsung reference columns are usually filenames/IDs; blanks mean no data."""
    if value is None:
        return False
    text = str(value).strip().lower()
    return text not in {"", "0", "false", "none", "null", "nan", "[]", "{}"}


PRIMARY_EXERCISE_NAME = re.compile(
    r"^com\.samsung\.shealth\.exercise\.[^.]+\.csv$", re.IGNORECASE
)


def looks_like_primary_exercise_csv(path: Path) -> bool:
    """Return True when the file header contains the core exercise columns.

    Samsung exports may also include files such as exercise.extension, exercise.route,
    exercise.weather and periodization files. Those share the same filename prefix but
    are not the main recorded-exercise table.
    """
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as f:
            # Samsung exports usually have one metadata line before the real CSV header.
            sample = "\n".join(f.readline() for _ in range(3)).lower()
    except OSError:
        return False

    required = ("exercise_type", "start_time", "datauuid")
    return all(token in sample for token in required)


def find_exercise_csv(source: Path, explicit: Path | None) -> Path:
    """Find the main Samsung Health exercise CSV automatically.

    Newer Samsung exports contain several similarly named files, for example:
      com.samsung.shealth.exercise.<timestamp>.csv
      com.samsung.shealth.exercise.extension.<timestamp>.csv
      com.samsung.shealth.exercise.route.<timestamp>.csv
      com.samsung.shealth.exercise.weather.<timestamp>.csv

    Prefer the plain exercise.<export-id>.csv filename and verify its header. If the
    filename pattern is unusual, fall back to identifying the file by its core columns.
    """
    if explicit:
        path = explicit if explicit.is_absolute() else source / explicit
        if not path.is_file():
            raise ConversionError(f"Exercise CSV not found: {path}")
        if not looks_like_primary_exercise_csv(path):
            raise ConversionError(
                f"The selected file does not look like the main Samsung exercise CSV: {path}"
            )
        return path

    matches = sorted(source.glob("com.samsung.shealth.exercise.*.csv"))
    if not matches:
        raise ConversionError(
            "No com.samsung.shealth.exercise.*.csv file found in the source folder."
        )

    # Normal/current export naming: only one component after 'exercise.'.
    plain_named = [p for p in matches if PRIMARY_EXERCISE_NAME.match(p.name)]
    valid_plain = [p for p in plain_named if looks_like_primary_exercise_csv(p)]
    if len(valid_plain) == 1:
        return valid_plain[0]

    # Fallback for older/unusual naming: identify the table from its header.
    valid_by_header = [p for p in matches if looks_like_primary_exercise_csv(p)]
    if len(valid_by_header) == 1:
        return valid_by_header[0]

    if len(valid_by_header) > 1:
        names = "\n  ".join(p.name for p in valid_by_header)
        raise ConversionError(
            "More than one CSV looks like a primary Samsung exercise table. "
            "Specify the intended file with --exercise-csv:\n  " + names
        )

    names = "\n  ".join(p.name for p in matches)
    raise ConversionError(
        "Samsung exercise-related CSV files were found, but none contained the expected "
        "exercise_type/start_time/datauuid columns. Candidates:\n  " + names
    )


def read_samsung_csv(path: Path) -> list[dict[str, str]]:
    """Read Samsung's exercise CSV, tolerating the extra first metadata line."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        first_line = f.readline()
        # Older Samsung exports have a metadata/version line before the real header.
        # If the first line already looks like the header, rewind; otherwise keep it skipped.
        if "exercise_type" in first_line and "start_time" in first_line:
            f.seek(0)
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ConversionError(f"Could not read a CSV header from {path}")
        return [
            {str(k).strip(): "" if v is None else str(v).strip() for k, v in row.items() if k}
            for row in reader
        ]


def normalize_exercise(row: dict[str, str]) -> dict[str, str]:
    """Normalize the column names used by different Samsung export revisions."""
    p = EXERCISE_PREFIX
    datauuid = first_value(row, p + "datauuid", "datauuid")
    start_time = first_value(row, p + "start_time", "start_time")
    exercise_type = first_value(row, p + "exercise_type", "exercise_type")

    if not datauuid or not start_time or not exercise_type:
        missing = [
            name
            for name, value in (
                ("datauuid", datauuid),
                ("start_time", start_time),
                ("exercise_type", exercise_type),
            )
            if not value
        ]
        raise ConversionError(f"Exercise row is missing required field(s): {', '.join(missing)}")

    return {
        "datauuid": datauuid,
        "start_time": start_time,
        "end_time": first_value(row, p + "end_time", "end_time"),
        "time_offset": first_value(row, p + "time_offset", "time_offset"),
        "exercise_type": exercise_type,
        "duration": first_value(row, p + "duration", "duration"),
        "distance": first_value(row, p + "distance", "distance"),
        # FromSamToGarm used total_calorie. Some exports/API variants use calorie.
        "total_calorie": first_value(
            row, "total_calorie", p + "total_calorie", p + "calorie", "calorie"
        ),
        "mean_heart_rate": first_value(row, p + "mean_heart_rate", "mean_heart_rate"),
        "max_heart_rate": first_value(row, p + "max_heart_rate", "max_heart_rate"),
        "min_heart_rate": first_value(row, p + "min_heart_rate", "min_heart_rate"),
        "mean_speed": first_value(row, p + "mean_speed", "mean_speed"),
        "max_speed": first_value(row, p + "max_speed", "max_speed"),
        "mean_cadence": first_value(row, p + "mean_cadence", "mean_cadence"),
        "max_cadence": first_value(row, p + "max_cadence", "max_cadence"),
        "location_data": first_value(row, p + "location_data", "location_data"),
        "live_data": first_value(row, p + "live_data", "live_data"),
    }


def parse_samsung_datetime(value: str) -> dt.datetime:
    """Parse Samsung start/end timestamps. Naive text timestamps are treated as UTC.

    This deliberately matches the original FromSamToGarm behaviour, which appended Z
    to the Samsung export's start_time value.
    """
    value = value.strip()
    if not value:
        raise ConversionError("Blank Samsung timestamp")

    numeric = finite_number(value)
    if numeric is not None and value.replace(".", "", 1).lstrip("+-").isdigit():
        # Heuristic: Samsung epoch values are commonly milliseconds.
        unix_seconds = numeric / 1000.0 if abs(numeric) > 100_000_000_000 else numeric
        return dt.datetime.fromtimestamp(unix_seconds, tz=dt.timezone.utc)

    cleaned = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(cleaned)
    except ValueError:
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = dt.datetime.strptime(value, fmt)
                break
            except ValueError:
                pass
        if parsed is None:
            raise ConversionError(f"Unsupported Samsung timestamp: {value!r}")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def unix_seconds_to_fit(unix_seconds: float) -> int:
    return int(round(unix_seconds)) - FIT_EPOCH_S


def datetime_to_fit(value: dt.datetime) -> int:
    return unix_seconds_to_fit(value.timestamp())


def unix_ms_to_fit(value: Any) -> int:
    number = finite_number(value)
    if number is None:
        raise ConversionError(f"Invalid millisecond timestamp: {value!r}")
    return unix_seconds_to_fit(number / 1000.0)


def parse_time_offset_seconds(value: str) -> int | None:
    """Best-effort parser for Samsung's optional UTC offset field."""
    if not value:
        return None
    text = value.strip()
    if ":" in text:
        sign = -1 if text.startswith("-") else 1
        text = text.lstrip("+-")
        try:
            hours, minutes = text.split(":", 1)
            return sign * (int(hours) * 3600 + int(minutes) * 60)
        except ValueError:
            return None

    number = finite_number(text)
    if number is None:
        return None
    # Old Samsung Health SDK fields commonly represented time offset in milliseconds.
    if abs(number) > 86_400:
        number /= 1000.0
    if abs(number) <= 86_400:
        return int(round(number))
    return None


def load_json_if_present(source: Path, uuid: str, kind: str, indicated: str) -> list[dict[str, Any]]:
    if not truthy_reference(indicated):
        return []
    if not uuid:
        return []
    path = (
        source
        / "jsons"
        / "com.samsung.shealth.exercise"
        / uuid[0]
        / f"{uuid}.com.samsung.health.exercise.{kind}.json"
    )
    if not path.is_file():
        print(f"  WARNING: {kind} was referenced but file is missing: {path}", file=sys.stderr)
        return []
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  WARNING: could not read {path.name}: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print(f"  WARNING: expected a JSON list in {path.name}; ignoring it.", file=sys.stderr)
        return []
    return [item for item in data if isinstance(item, dict)]


def nearest_timestamp(target: int, sorted_timestamps: list[int]) -> int:
    """Find nearest timestamp in O(log n), unlike the original linear scan."""
    if not sorted_timestamps:
        return target
    pos = bisect.bisect_left(sorted_timestamps, target)
    candidates: list[int] = []
    if pos < len(sorted_timestamps):
        candidates.append(sorted_timestamps[pos])
    if pos:
        candidates.append(sorted_timestamps[pos - 1])
    return min(candidates, key=lambda x: abs(x - target))


def merge_location_and_live_data(
    location_data: list[dict[str, Any]], live_data: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """Merge Samsung GPS and live sensor data by millisecond Unix timestamp.

    This preserves the useful behaviour from FromSamToGarm: live sensor points are
    attached to the nearest GPS point when GPS exists, and heart rate is forward-filled
    after the first valid reading so Garmin does not display artificial zero-HR gaps.
    """
    merged: dict[int, dict[str, Any]] = {}

    for entry in location_data:
        ts_num = finite_number(entry.get("start_time"))
        if ts_num is None:
            continue
        ts = int(round(ts_num))
        point = merged.setdefault(ts, {})
        for key in ("latitude", "longitude", "altitude", "distance", "speed"):
            number = finite_number(entry.get(key))
            if number is not None:
                point[key] = number

    location_timestamps = sorted(merged)

    for entry in live_data:
        ts_num = finite_number(entry.get("start_time"))
        if ts_num is None:
            continue
        original_ts = int(round(ts_num))
        ts = nearest_timestamp(original_ts, location_timestamps) if location_timestamps else original_ts
        point = merged.setdefault(ts, {})
        for key in ("distance", "cadence", "heart_rate", "speed", "altitude"):
            number = finite_number(entry.get(key))
            if number is not None and key not in point:
                point[key] = number

    # Forward-fill HR only after the first real HR sample.
    last_hr: int | None = None
    for ts in sorted(merged):
        point = merged[ts]
        hr = finite_number(point.get("heart_rate"))
        if hr is not None and hr > 0:
            last_hr = int(round(hr))
            point["heart_rate"] = last_hr
        elif last_hr is not None:
            point["heart_rate"] = last_hr

    return dict(sorted(merged.items()))


def degrees_to_semicircles(degrees: float) -> int:
    return int(round(degrees * ((2**31) / 180.0)))


def clamp_uint8(value: Any) -> int | None:
    number = finite_number(value)
    if number is None or number <= 0:
        return None
    return max(1, min(254, int(round(number))))


def merged_to_fit_records(merged: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert merged Samsung points to FIT RECORD messages, at most one per second."""
    # FIT's normal timestamp field has whole-second precision. Merge any Samsung points
    # that collapse into the same FIT second instead of emitting duplicate-second records.
    by_fit_second: dict[int, dict[str, Any]] = {}

    for unix_ms, point in merged.items():
        fit_ts = unix_ms_to_fit(unix_ms)
        record = by_fit_second.setdefault(
            fit_ts, {"mesg_num": Profile["mesg_num"]["RECORD"], "timestamp": fit_ts}
        )

        lat = finite_number(point.get("latitude"))
        lon = finite_number(point.get("longitude"))
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            record["position_lat"] = degrees_to_semicircles(lat)
            record["position_long"] = degrees_to_semicircles(lon)

        altitude = finite_number(point.get("altitude"))
        if altitude is not None:
            record["enhanced_altitude"] = altitude

        distance = finite_number(point.get("distance"))
        if distance is not None and distance >= 0:
            record["distance"] = distance

        speed = finite_number(point.get("speed"))
        if speed is not None and speed >= 0:
            record["enhanced_speed"] = speed

        hr = clamp_uint8(point.get("heart_rate"))
        if hr is not None:
            record["heart_rate"] = hr

        cadence = clamp_uint8(point.get("cadence"))
        if cadence is not None:
            record["cadence"] = cadence

    return [by_fit_second[key] for key in sorted(by_fit_second)]


def summary_hr(records: Iterable[dict[str, Any]]) -> tuple[int | None, int | None]:
    values = [int(r["heart_rate"]) for r in records if "heart_rate" in r]
    if not values:
        return None, None
    return int(round(sum(values) / len(values))), max(values)


def add_if(message: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        message[key] = value


def safe_uint16(value: Any) -> int | None:
    number = finite_number(value)
    if number is None or number < 0:
        return None
    return max(0, min(65534, int(round(number))))


def build_fit_messages(
    exercise: dict[str, str],
    source: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    load_fit_sdk()
    uuid = exercise["datauuid"]
    samsung_type = exercise["exercise_type"]
    label, sport, sub_sport = SAMSUNG_TO_FIT.get(
        samsung_type, (f"Samsung exercise {samsung_type}", "generic", "generic")
    )

    start_dt = parse_samsung_datetime(exercise["start_time"])
    start_fit = datetime_to_fit(start_dt)

    duration_ms = positive_number(exercise["duration"])
    timer_seconds = duration_ms / 1000.0 if duration_ms is not None else None

    end_dt: dt.datetime | None = None
    if exercise.get("end_time"):
        try:
            end_dt = parse_samsung_datetime(exercise["end_time"])
        except ConversionError:
            end_dt = None

    elapsed_seconds: float | None = None
    if end_dt is not None:
        candidate = (end_dt - start_dt).total_seconds()
        if candidate > 0:
            elapsed_seconds = candidate
    if timer_seconds is None and elapsed_seconds is not None:
        timer_seconds = elapsed_seconds
    if elapsed_seconds is None and timer_seconds is not None:
        elapsed_seconds = timer_seconds
    if timer_seconds is None:
        timer_seconds = 0.0
    if elapsed_seconds is None:
        elapsed_seconds = timer_seconds

    location = load_json_if_present(source, uuid, "location_data", exercise["location_data"])
    live = load_json_if_present(source, uuid, "live_data", exercise["live_data"])
    merged = merge_location_and_live_data(location, live)
    records = merged_to_fit_records(merged)

    # Ensure the FIT Activity has Record messages even for gym activities with no GPS/live data.
    nominal_end_fit = start_fit + max(1, int(round(elapsed_seconds)))
    if not records:
        records = [
            {"mesg_num": Profile["mesg_num"]["RECORD"], "timestamp": start_fit},
            {"mesg_num": Profile["mesg_num"]["RECORD"], "timestamp": nominal_end_fit},
        ]
    else:
        # Keep source points in chronological order and make summary end time cover them.
        records.sort(key=lambda r: r["timestamp"])

    last_record_fit = records[-1]["timestamp"]
    end_fit = max(nominal_end_fit, last_record_fit)
    elapsed_seconds = max(float(elapsed_seconds), float(end_fit - start_fit))
    timer_seconds = max(0.0, min(float(timer_seconds), elapsed_seconds))
    if timer_seconds == 0.0:
        timer_seconds = elapsed_seconds

    total_distance = positive_number(exercise["distance"])
    if total_distance is None:
        record_distances = [finite_number(r.get("distance")) for r in records]
        valid_distances = [d for d in record_distances if d is not None and d >= 0]
        if valid_distances:
            total_distance = max(valid_distances)

    calories = finite_number(exercise["total_calorie"])
    total_calories = safe_uint16(calories) if calories is not None and calories >= 0 else None

    avg_hr = clamp_uint8(exercise["mean_heart_rate"])
    max_hr = clamp_uint8(exercise["max_heart_rate"])
    if avg_hr is None or max_hr is None:
        computed_avg_hr, computed_max_hr = summary_hr(records)
        avg_hr = avg_hr or computed_avg_hr
        max_hr = max_hr or computed_max_hr

    avg_speed = positive_number(exercise["mean_speed"])
    if avg_speed is None and total_distance is not None and timer_seconds > 0:
        avg_speed = total_distance / timer_seconds
    max_speed = positive_number(exercise["max_speed"])

    avg_cadence = clamp_uint8(exercise["mean_cadence"])
    max_cadence = clamp_uint8(exercise["max_cadence"])

    serial = zlib.crc32(uuid.encode("utf-8")) & 0xFFFFFFFF
    if serial == 0:
        serial = 1

    messages: list[dict[str, Any]] = []

    messages.append(
        {
            "mesg_num": Profile["mesg_num"]["FILE_ID"],
            "type": "activity",
            "manufacturer": "development",
            "product": 0,
            "time_created": start_fit,
            "serial_number": serial,
        }
    )

    messages.append(
        {
            "mesg_num": Profile["mesg_num"]["DEVICE_INFO"],
            "device_index": "creator",
            "manufacturer": "development",
            "product": 0,
            "product_name": "Samsung Health FIT Import",
            "serial_number": serial,
            "software_version": 1.0,
            "timestamp": start_fit,
        }
    )

    messages.append(
        {
            "mesg_num": Profile["mesg_num"]["EVENT"],
            "timestamp": start_fit,
            "event": "timer",
            "event_type": "start",
        }
    )

    messages.extend(records)

    messages.append(
        {
            "mesg_num": Profile["mesg_num"]["EVENT"],
            "timestamp": end_fit,
            "event": "timer",
            "event_type": "stop",
        }
    )

    lap: dict[str, Any] = {
        "mesg_num": Profile["mesg_num"]["LAP"],
        "message_index": 0,
        "timestamp": end_fit,
        "start_time": start_fit,
        "total_elapsed_time": elapsed_seconds,
        "total_timer_time": timer_seconds,
        "sport": sport,
        "sub_sport": sub_sport,
    }
    add_if(lap, "total_distance", total_distance)
    add_if(lap, "total_calories", total_calories)
    add_if(lap, "avg_heart_rate", avg_hr)
    add_if(lap, "max_heart_rate", max_hr)
    add_if(lap, "avg_speed", avg_speed)
    add_if(lap, "max_speed", max_speed)
    add_if(lap, "avg_cadence", avg_cadence)
    add_if(lap, "max_cadence", max_cadence)
    messages.append(lap)

    session: dict[str, Any] = {
        "mesg_num": Profile["mesg_num"]["SESSION"],
        "message_index": 0,
        "timestamp": end_fit,
        "start_time": start_fit,
        "total_elapsed_time": elapsed_seconds,
        "total_timer_time": timer_seconds,
        "sport": sport,
        "sub_sport": sub_sport,
        "first_lap_index": 0,
        "num_laps": 1,
    }
    add_if(session, "total_distance", total_distance)
    add_if(session, "total_calories", total_calories)
    add_if(session, "avg_heart_rate", avg_hr)
    add_if(session, "max_heart_rate", max_hr)
    add_if(session, "avg_speed", avg_speed)
    add_if(session, "max_speed", max_speed)
    add_if(session, "avg_cadence", avg_cadence)
    add_if(session, "max_cadence", max_cadence)
    messages.append(session)

    activity: dict[str, Any] = {
        "mesg_num": Profile["mesg_num"]["ACTIVITY"],
        "timestamp": end_fit,
        "num_sessions": 1,
        "total_timer_time": timer_seconds,
    }
    offset_seconds = parse_time_offset_seconds(exercise.get("time_offset", ""))
    if offset_seconds is not None:
        activity["local_timestamp"] = end_fit + offset_seconds
    messages.append(activity)

    meta = {
        "uuid": uuid,
        "samsung_type": samsung_type,
        "label": label,
        "sport": sport,
        "sub_sport": sub_sport,
        "start_date": start_dt.date().isoformat(),
        "records": len(records),
        "distance": total_distance,
        "calories": total_calories,
        "unknown_type": samsung_type not in SAMSUNG_TO_FIT,
    }
    return messages, meta


def encode_fit(messages: list[dict[str, Any]], destination: Path) -> None:
    load_fit_sdk()
    encoder = Encoder()
    for message in messages:
        encoder.write_mesg(message)
    data = encoder.close()
    destination.write_bytes(data)


def verify_fit(path: Path, expected_sport: str, expected_sub_sport: str) -> tuple[bool, str]:
    """Decode the just-written FIT file and verify CRC + core activity structure."""
    try:
        load_fit_sdk()
        decoder = Decoder(Stream.from_file(str(path)))
        if not decoder.is_fit():
            return False, "FIT header check failed"

        decoder = Decoder(Stream.from_file(str(path)))
        if not decoder.check_integrity():
            return False, "FIT size/CRC integrity check failed"

        decoder = Decoder(Stream.from_file(str(path)))
        messages, errors = decoder.read()
        if errors:
            return False, "decoder error(s): " + "; ".join(map(str, errors))

        sessions = messages.get("session_mesgs", [])
        laps = messages.get("lap_mesgs", [])
        activities = messages.get("activity_mesgs", [])
        records = messages.get("record_mesgs", [])
        if len(sessions) != 1:
            return False, f"expected 1 session, decoded {len(sessions)}"
        if len(laps) < 1:
            return False, "no lap message decoded"
        if len(activities) != 1:
            return False, f"expected 1 activity message, decoded {len(activities)}"
        if len(records) < 1:
            return False, "no record messages decoded"

        decoded_sport = sessions[0].get("sport")
        decoded_sub_sport = sessions[0].get("sub_sport")
        if decoded_sport != expected_sport:
            return False, f"sport decoded as {decoded_sport!r}, expected {expected_sport!r}"
        if decoded_sub_sport != expected_sub_sport:
            return False, (
                f"sub_sport decoded as {decoded_sub_sport!r}, "
                f"expected {expected_sub_sport!r}"
            )
        return True, f"CRC/decode OK; {len(records)} records; {decoded_sport}/{decoded_sub_sport}"
    except Exception as exc:  # verification should report, not abort the whole batch
        return False, f"verification exception: {exc}"


def filename_for(meta: dict[str, Any]) -> str:
    safe_uuid = str(meta["uuid"]).replace("/", "_").replace("\\", "_")
    return f"{meta['samsung_type']}_{meta['start_date']}_{safe_uuid}.fit"


def print_mapping() -> None:
    print("Samsung -> Garmin FIT mapping")
    for code, (label, sport, sub_sport) in SAMSUNG_TO_FIT.items():
        print(f"  {code:>5}  {label:<42} -> {sport}/{sub_sport}")


def parse_types(value: str | None) -> set[str] | None:
    if not value:
        return None
    types = {item.strip() for item in value.split(",") if item.strip()}
    return types or None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Samsung Health exercise export data to Garmin FIT Activity files."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.cwd(),
        help="Root of extracted Samsung Health export (default: current directory).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output folder (default: <source>/fit_exports).",
    )
    parser.add_argument(
        "--exercise-csv",
        type=Path,
        default=None,
        help="Specific Samsung exercise CSV, useful if more than one is present.",
    )
    parser.add_argument(
        "--types",
        help="Comma-separated Samsung exercise type codes to convert, e.g. 13001,1001.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Convert at most N matching activities (recommended for the first test run).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite FIT files that already exist.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-write FIT CRC/decode verification.",
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="Print the built-in Samsung -> FIT mapping and exit.",
    )
    args = parser.parse_args()

    if args.list_types:
        print_mapping()
        return 0

    source = args.source.expanduser().resolve()
    if not source.is_dir():
        print(f"ERROR: source folder does not exist: {source}", file=sys.stderr)
        return 2
    output = (args.output or (source / "fit_exports")).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    try:
        exercise_csv = find_exercise_csv(source, args.exercise_csv)
        rows = read_samsung_csv(exercise_csv)
        exercises = [normalize_exercise(row) for row in rows]
    except (ConversionError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    selected_types = parse_types(args.types)
    if selected_types is not None:
        exercises = [e for e in exercises if e["exercise_type"] in selected_types]
    if args.limit is not None:
        if args.limit < 1:
            print("ERROR: --limit must be >= 1", file=sys.stderr)
            return 2
        exercises = exercises[: args.limit]

    print(f"Source: {source}")
    print(f"Exercise CSV: {exercise_csv.name}")
    print(f"Output: {output}")
    print(f"Activities selected: {len(exercises)}")
    if not exercises:
        print("Nothing to convert.")
        return 0

    converted = 0
    skipped = 0
    failed = 0
    verification_failed = 0
    unknown_types: set[str] = set()

    for index, exercise in enumerate(exercises, start=1):
        try:
            messages, meta = build_fit_messages(exercise, source)
            if meta["unknown_type"]:
                unknown_types.add(meta["samsung_type"])
            dest = output / filename_for(meta)
            prefix = (
                f"[{index}/{len(exercises)}] {meta['start_date']} "
                f"{meta['samsung_type']} {meta['label']} -> "
                f"{meta['sport']}/{meta['sub_sport']}"
            )

            if dest.exists() and not args.overwrite:
                print(prefix + f"  SKIP (exists: {dest.name})")
                skipped += 1
                continue

            encode_fit(messages, dest)
            converted += 1

            if args.no_verify:
                print(prefix + f"  WROTE {dest.name} ({meta['records']} records)")
            else:
                ok, detail = verify_fit(dest, meta["sport"], meta["sub_sport"])
                if ok:
                    print(prefix + f"  OK ({detail})")
                else:
                    verification_failed += 1
                    print(prefix + f"  VERIFY FAILED: {detail}", file=sys.stderr)
        except Exception as exc:
            failed += 1
            print(
                f"[{index}/{len(exercises)}] FAILED {exercise.get('datauuid', '?')}: {exc}",
                file=sys.stderr,
            )

    print("\nSummary")
    print(f"  Converted: {converted}")
    print(f"  Skipped existing: {skipped}")
    print(f"  Conversion failures: {failed}")
    print(f"  Verification failures: {verification_failed}")
    if unknown_types:
        print(
            "  WARNING: unknown Samsung type(s) were exported as generic/generic: "
            + ", ".join(sorted(unknown_types))
        )
        print(
            "  See the commented suggested mappings below SAMSUNG_TO_FIT and the README. "
            "Enable/review the matching entry before importing to Garmin."
        )

    if failed or verification_failed:
        print("\nDo NOT bulk-import to Garmin until the failures above are resolved.")
        return 1

    print("\nAll written FIT files passed the requested checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
