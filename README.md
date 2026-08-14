# Samsung Health → Garmin Connect Migration Tools

A small set of Python tools for migrating historical Samsung Health data into Garmin Connect.

The repository focuses on two jobs:

1. **Recorded workouts → Garmin FIT files** with proper Garmin activity types such as Walking, Hiking, Running and Cycling.
2. **Daily activity history → Garmin/Fitbit-style CSV files** for steps, distance, calories, floors and activity minutes.

> **Important:** these are community tools, not official Samsung or Garmin software. Always test with a few files before importing years of history.

## Why this project exists

[FromSamToGarm](https://github.com/PhilippImhof/FromSamToGarm) already provides a very useful way to migrate Samsung Health data to Garmin Connect. Its exercise converter writes TCX files, however, and TCX only gives Garmin a very limited activity-type choice (`Running`, `Biking`, or `Other`). That means walks, hikes and many other activities arrive as **Other**.

This project keeps/adapts the useful Samsung Health parsing approach from FromSamToGarm while adding:

- FIT output using Garmin's official Python FIT SDK;
- specific Garmin sport/sub-sport mappings;
- automatic FIT verification after writing;
- automatic detection of the correct main Samsung exercise CSV even when newer Samsung exports contain `exercise.extension`, `exercise.route`, `exercise.weather`, and similar files;
- support for newer Samsung daily calorie date formats;
- explicit missing-data modes for daily activity CSVs.

See [ATTRIBUTION.md](ATTRIBUTION.md) for details.

## Files

| File | Purpose |
|---|---|
| `samsung_health_to_fit.py` | Converts recorded Samsung Health exercises to Garmin-compatible `.fit` Activity files. |
| `activity_fixed_v4.py` | Converts Samsung daily activity history to Garmin/Fitbit-style CSV files. |
| `requirements.txt` | Runtime dependency declaration for FIT encoding/verification. |
| `DEPENDENCIES.md` | Dependency, licensing, offline-cache, and test setup details. |
| `setup.ps1` | Creates `.venv`, installs requirements, and can create/use a private local dependency cache. |
| `run_tests.ps1` | Runs the full test suite using the project virtual environment. |
| `ATTRIBUTION.md` | Credits and upstream-project notes. |
| `SAMSUNG_EXERCISE_TYPES.md` | Legacy numeric IDs and newer Health Data SDK enum reference. |
| `.github/workflows/tests.yml` | GitHub Actions workflow that installs dependencies and runs the full tests. |
| `LICENSE` | GNU GPL v3 license. |

## What is not included

- Sleep migration is not handled here.
- Weight conversion is not duplicated here. The original [FromSamToGarm](https://github.com/PhilippImhof/FromSamToGarm) project includes `weight.py` for that purpose.

## Dependencies at a glance

- **Python 3.10+ recommended.**
- **`garmin-fit-sdk>=21.200.0,<22`** is required by `samsung_health_to_fit.py` for FIT encoding and verification. Garmin added the Python `Encoder` in 21.200.0.
- `activity_fixed_v4.py` uses only Python's standard library.
- `setup.ps1` creates a virtual environment and installs `requirements.txt`.
- A private/offline pip cache can be created with `setup.ps1 -CacheDependencies`; Garmin SDK package files are intentionally excluded from Git/public redistribution.

See [DEPENDENCIES.md](DEPENDENCIES.md) for installation commands, official references, licensing notes, and offline-cache instructions.

---

# 1. Export your Samsung Health data

In Samsung Health, use the app's **Download personal data** function and copy/extract the complete export onto your computer.

Keep the directory structure intact. Recorded workouts may reference JSON files under a structure similar to:

```text
Samsung Health export/
├── com.samsung.shealth.exercise.20260813124705.csv
├── com.samsung.shealth.exercise.extension.20260813124705.csv
├── com.samsung.shealth.exercise.route.20260813124705.csv
├── ...
└── jsons/
    └── com.samsung.shealth.exercise/
        ├── 0/
        ├── 1/
        ├── a/
        └── ...
```

**Do not move only the CSV files.** GPS and live sensor information can be stored in the JSON folders.

Also: Samsung Health exports contain sensitive health and location data. Do not commit your export to GitHub. This repository's `.gitignore` intentionally excludes common Samsung export files and generated outputs.

---

# 2. Windows / PowerShell setup

Copy `samsung_health_to_fit.py` and `activity_fixed_v4.py` into the root of the extracted Samsung Health export, or clone this repository and run the FIT script with `--source`.

Create a virtual environment:

```powershell
py -m venv .venv
```

Install the project dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Or simply run:

```powershell
.\setup.ps1
```

The FIT converter requires `garmin-fit-sdk >= 21.200.0,<22`, because Garmin added the Python FIT `Encoder` in release 21.200.0. `activity_fixed_v4.py` itself uses only the Python standard library. See [DEPENDENCIES.md](DEPENDENCIES.md) for full details.

### Keeping a private local dependency backup

You can cache the Python packages locally for your own/offline use:

```powershell
.\setup.ps1 -CacheDependencies
```

That places downloaded packages under `vendor/`, which is deliberately ignored by Git. To install from the cache later:

```powershell
.\setup.ps1 -Offline
```

**Do not commit or mirror Garmin's FIT SDK package in this repository.** Garmin's FIT Protocol License permits use of the SDK but restricts redistributing/providing the SDK and source files to others. For that reason this project keeps only the dependency declaration and official download references, not a copy of Garmin's files. See [DEPENDENCIES.md](DEPENDENCIES.md).

---

# 3. Recorded workouts → FIT

## Show the built-in activity mappings

```powershell
.\.venv\Scripts\python.exe .\samsung_health_to_fit.py --list-types
```

Current mappings:

| Samsung ID | Samsung activity | Garmin FIT |
|---:|---|---|
| 1001 | Walking | `walking / generic` |
| 1002 | Running | `running / generic` |
| 10006 | Sit-ups | `training / strength_training` |
| 10007 | Circuit training, moderate effort | `training / cardio_training` |
| 11007 | Cycling | `cycling / generic` |
| 13001 | Hiking | `hiking / generic` |
| 14001 | Swimming, general (not lap swimming) | `swimming / generic` |
| 15002 | Weight machine | `training / strength_training` |
| 15003 | Exercise bike | `cycling / indoor_cycling` |
| 15005 | Treadmill, jogging/walking | `running / treadmill` |

You can edit `SAMSUNG_TO_FIT` near the top of the script if your export contains additional Samsung exercise IDs.

> **Unknown exercise IDs:** If an export contains a Samsung exercise ID that is not enabled in `SAMSUNG_TO_FIT`, the converter currently preserves the activity by exporting it as `generic / generic` and prints a warning. This is intentional rather than silently discarding the activity. Review the warning, check the mapping reference below, and test the resulting activity in Garmin Connect before bulk importing unknown types.

### Other documented Samsung numeric IDs — reference only

Samsung's legacy numeric `EXERCISE_TYPE` reference documents the IDs below in addition to the ten mappings enabled above. They are **not enabled by default** because this project has not personally tested their Garmin Connect classification.

The suggested Garmin values were matched against Garmin FIT's published `sport` and `sub_sport` enums. `exact` means a direct FIT equivalent exists; `close` means a very similar category; `approximate` means FIT has no direct equivalent and a semantic fallback was chosen.

The same suggestions are included as **commented-out, copy/paste-ready dictionary entries** directly below `SAMSUNG_TO_FIT` in `samsung_health_to_fit.py`.

Sources:

- Samsung numeric exercise types: https://developer.samsung.com/health/android/data/api-reference/EXERCISE_TYPE.html
- Garmin FIT sport/sub-sport profile: https://github.com/garmin/fit-python-sdk/blob/main/garmin_fit_sdk/profile.py

> **Important:** These are mapping suggestions, not Garmin Connect UI guarantees. Test one or two activities before bulk importing. Samsung custom type `0` cannot be mapped reliably without inspecting its custom title/type.

<details>
<summary>Show the other documented Samsung IDs and suggested Garmin FIT mappings</summary>

| Samsung ID | Samsung activity | Suggested Garmin FIT | Confidence |
|---:|---|---|---|
| 0 | Custom type | `generic / generic` | custom |
| 2001 | Baseball, general | `baseball / generic` | exact |
| 2002 | Softball, general | `baseball / generic` | close |
| 2003 | Cricket | `cricket / generic` | exact |
| 3001 | Golf, general | `golf / generic` | exact |
| 3002 | Billiards | `generic / generic` | approximate |
| 3003 | Bowling, alley | `generic / generic` | approximate |
| 4001 | Hockey | `hockey / generic` | close |
| 4002 | Rugby, touch, non-competitive | `rugby / generic` | exact |
| 4003 | Basketball, general | `basketball / generic` | exact |
| 4004 | Football, general (Soccer) | `soccer / generic` | exact |
| 4005 | Handball, general | `team_sport / generic` | approximate |
| 4006 | American football, general, touch | `american_football / generic` | exact |
| 5001 | Volleyball, general, 6~9 member team, non-competitive | `volleyball / generic` | exact |
| 5002 | Beach volleyball | `volleyball / generic` | close |
| 6001 | Squash, general | `racket / squash` | exact |
| 6002 | Tennis, general | `tennis / generic` | exact |
| 6003 | Badminton, competitive | `racket / badminton` | exact |
| 6004 | Table tennis | `racket / table_tennis` | exact |
| 6005 | Racquetball, general | `racket / racquetball` | exact |
| 7001 | T'ai chi, general (deprecated; Samsung says use 7003) | `training / flexibility_training` | approximate |
| 7002 | Boxing, in ring | `boxing / generic` | exact |
| 7003 | Martial arts, moderate pace (Judo, Jujitsu, Karate, Taekwondo) | `mixed_martial_arts / generic` | close |
| 8001 | Ballet, general, rehearsal or class | `dance / generic` | close |
| 8002 | Dancing, general (Folk, Irish step, Polka) | `dance / generic` | exact |
| 8003 | Ballroom dancing, fast | `dance / generic` | close |
| 9001 | Pilates | `fitness_equipment / pilates` | exact |
| 9002 | Yoga | `training / yoga` | exact |
| 10001 | Stretching | `training / flexibility_training` | exact |
| 10002 | Jump rope, moderate pace | `jump_rope / generic` | exact |
| 10003 | Hula-hooping | `training / cardio_training` | approximate |
| 10004 | Push-ups (Press-ups) | `training / strength_training` | close |
| 10005 | Pull-ups (Chin-up) | `training / strength_training` | close |
| 10008 | Mountain climbers | `training / cardio_training` | approximate |
| 10009 | Jumping Jacks | `training / cardio_training` | approximate |
| 10010 | Burpee | `hiit / generic` | close |
| 10011 | Bench press | `training / strength_training` | close |
| 10012 | Squats | `training / strength_training` | close |
| 10013 | Lunges | `training / strength_training` | close |
| 10014 | Leg presses | `training / strength_training` | close |
| 10015 | Leg extensions | `training / strength_training` | close |
| 10016 | Leg curls | `training / strength_training` | close |
| 10017 | Back extensions | `training / strength_training` | close |
| 10018 | Lat pull-downs | `training / strength_training` | close |
| 10019 | Deadlifts | `training / strength_training` | close |
| 10020 | Shoulder presses | `training / strength_training` | close |
| 10021 | Front raises | `training / strength_training` | close |
| 10022 | Lateral raises | `training / strength_training` | close |
| 10023 | Crunches | `training / strength_training` | close |
| 10024 | Leg raises | `training / strength_training` | close |
| 10025 | Plank | `training / strength_training` | close |
| 10026 | Arm curls | `training / strength_training` | close |
| 10027 | Arm extensions | `training / strength_training` | close |
| 11001 | Inline skating, moderate pace | `inline_skating / generic` | exact |
| 11002 | Hang gliding | `hang_gliding / generic` | exact |
| 11003 | Pistol shooting | `shooting / generic` | close |
| 11004 | Archery, non-hunting | `archery / generic` | exact |
| 11005 | Horseback riding, general | `horseback_riding / generic` | exact |
| 11008 | Flying disc, general, playing | `generic / generic` | approximate |
| 11009 | Roller skating | `inline_skating / generic` | approximate |
| 12001 | Aerobics, general | `training / cardio_training` | close |
| 13002 | Rock climbing, low to moderate difficulty | `rock_climbing / generic` | exact |
| 13003 | Backpacking | `hiking / rucking` | close |
| 13004 | Mountain biking, general | `cycling / mountain` | exact |
| 13005 | Orienteering | `running / navigate` | approximate |
| 14002 | Aquarobics | `training / cardio_training` | approximate |
| 14003 | Canoeing, general, for pleasure | `canoeing / generic` | exact |
| 14004 | Sailing, leisure, ocean sailing | `sailing / generic` | exact |
| 14005 | Scuba diving, general | `diving / generic` | close |
| 14006 | Snorkeling | `snorkeling / generic` | exact |
| 14007 | Kayaking, moderate effort | `kayaking / generic` | exact |
| 14008 | Kitesurfing | `kitesurfing / generic` | exact |
| 14009 | Rafting | `rafting / generic` | exact |
| 14010 | Rowing machine, general, for pleasure | `rowing / indoor_rowing` | close |
| 14011 | Windsurfing, general | `windsurfing / generic` | exact |
| 14012 | Yachting, leisure | `sailing / generic` | close |
| 14013 | Water skiing | `water_skiing / generic` | exact |
| 15001 | Step machine | `fitness_equipment / stair_climbing` | exact |
| 15004 | Rowing machine | `rowing / indoor_rowing` | exact |
| 15006 | Elliptical trainer, moderate effort | `fitness_equipment / elliptical` | exact |
| 16001 | Cross-country skiing, general, moderate speed | `cross_country_skiing / generic` | exact |
| 16002 | Skiing, general, downhill, moderate effort | `alpine_skiing / generic` | close |
| 16003 | Ice dancing | `ice_skating / generic` | close |
| 16004 | Ice skating, general | `ice_skating / generic` | exact |
| 16006 | Ice hockey, general | `hockey / ice` | exact |
| 16007 | Snowboarding, general, moderate effort | `snowboarding / generic` | exact |
| 16008 | Alpine skiing, general, moderate effort | `alpine_skiing / generic` | exact |
| 16009 | Snowshoeing, moderate effort | `snowshoeing / generic` | exact |

</details>

The reference above covers the **legacy numeric Samsung Health exercise-type schema** used by the export format handled by this converter.

### Samsung Health Data SDK named enums — future reference

> **This converter currently supports Samsung Health exports using Samsung's legacy numeric `EXERCISE_TYPE` values.**  
> Current Samsung Health exports may still contain these numeric identifiers even though Samsung's newer Health Data SDK uses named `PredefinedExerciseType` enum values such as `WALKING`, `RUNNING`, and `HIKING`.  
> The new Health Data SDK enum list is provided separately as a reference for future development and should not be confused with the numeric IDs found in the exports currently handled by this converter.

The distinction is an **API/schema distinction**, not simply “old workouts versus new workouts.” Samsung's legacy Android Health SDK stores the exercise type as an integer `EXERCISE_TYPE`; Samsung's migration example shows `1002` for running. The newer Samsung Health Data SDK uses `PredefinedExerciseType.RUNNING` instead. Samsung also allows an `ExerciseType` record to contain one or more `ExerciseSession` objects, which matters for multisport records such as triathlon.

Official references:

- Legacy numeric `EXERCISE_TYPE` table: https://developer.samsung.com/health/android/data/api-reference/EXERCISE_TYPE.html
- Samsung migration example (numeric `1002` → `PredefinedExerciseType.RUNNING`): https://developer.samsung.com/health/data/migration-guide/exercise-app-example.html
- New `PredefinedExerciseType` enum reference: https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/-exercise-type/-predefined-exercise-type/index.html
- New `ExerciseType` / multi-session model: https://developer.samsung.com/health/data/api-reference/-shd/com.samsung.android.sdk.health.data.request/-data-type/-exercise-type/index.html
- Garmin FIT sport/sub-sport profile used for the suggestions: https://github.com/garmin/fit-python-sdk/blob/main/garmin_fit_sdk/profile.py

The table below is **reference-only**. The current CSV parser does not read these named enum strings, so adding a row here does not enable support by itself. The “closest legacy numeric ID” column is a project cross-reference where an obvious legacy equivalent exists; `—` means there is no direct equivalent in Samsung's older numeric table or the semantics differ materially.

<details>
<summary>Show Samsung Health Data SDK named enums and suggested Garmin FIT mappings</summary>

| Health Data SDK enum | Closest legacy numeric ID | Suggested Garmin FIT | Confidence |
|---|---:|---|---|
| `UNDEFINED` | — | `generic / generic` | approximate |
| `OTHER` | — | `generic / generic` | custom |
| `WALKING` | 1001 | `walking / generic` | exact |
| `RUNNING` | 1002 | `running / generic` | exact |
| `STAIR_CLIMBING` | — | `floor_climbing / generic` | exact |
| `TRACK_RUNNING` | — | `running / track` | exact |
| `BASEBALL` | 2001 | `baseball / generic` | exact |
| `SOFTBALL` | 2002 | `baseball / generic` | close |
| `CRICKET` | 2003 | `cricket / generic` | exact |
| `GOLF` | 3001 | `golf / generic` | exact |
| `BOWLING` | 3003 | `generic / generic` | approximate |
| `HOCKEY` | 4001 | `hockey / generic` | close |
| `RUGBY` | 4002 | `rugby / generic` | exact |
| `BASKETBALL` | 4003 | `basketball / generic` | exact |
| `SOCCER` | 4004 | `soccer / generic` | exact |
| `HANDBALL` | 4005 | `team_sport / generic` | approximate |
| `AMERICAN_FOOTBALL` | 4006 | `american_football / generic` | exact |
| `VOLLEYBALL` | 5001 | `volleyball / generic` | exact |
| `BEACH_VOLLEYBALL` | 5002 | `volleyball / generic` | close |
| `SQUASH` | 6001 | `racket / squash` | exact |
| `TENNIS` | 6002 | `tennis / generic` | exact |
| `BADMINTON` | 6003 | `racket / badminton` | exact |
| `TABLE_TENNIS` | 6004 | `racket / table_tennis` | exact |
| `RACQUETBALL` | 6005 | `racket / racquetball` | exact |
| `BOXING` | 7002 | `boxing / generic` | exact |
| `MARTIAL_ARTS` | 7003 | `mixed_martial_arts / generic` | close |
| `BALLET` | 8001 | `dance / generic` | close |
| `DANCING` | 8002 | `dance / generic` | exact |
| `BALLROOM_DANCING` | 8003 | `dance / generic` | close |
| `PILATES` | 9001 | `fitness_equipment / pilates` | exact |
| `YOGA` | 9002 | `training / yoga` | exact |
| `STRETCHING` | 10001 | `training / flexibility_training` | exact |
| `JUMP_ROPE` | 10002 | `jump_rope / generic` | exact |
| `HULA_HOOPING` | 10003 | `training / cardio_training` | approximate |
| `PUSH_UPS` | 10004 | `training / strength_training` | close |
| `PULL_UPS` | 10005 | `training / strength_training` | close |
| `SIT_UPS` | 10006 | `training / strength_training` | close |
| `CIRCUIT_TRAINING` | 10007 | `training / cardio_training` | close |
| `MOUNTAIN_CLIMBERS` | 10008 | `training / cardio_training` | approximate |
| `JUMPING_JACKS` | 10009 | `training / cardio_training` | approximate |
| `BURPEES` | 10010 | `hiit / generic` | close |
| `BENCH_PRESS` | 10011 | `training / strength_training` | close |
| `SQUATS` | 10012 | `training / strength_training` | close |
| `LUNGES` | 10013 | `training / strength_training` | close |
| `LEG_PRESSES` | 10014 | `training / strength_training` | close |
| `LEG_EXTENSIONS` | 10015 | `training / strength_training` | close |
| `LEG_CURLS` | 10016 | `training / strength_training` | close |
| `BACK_EXTENSIONS` | 10017 | `training / strength_training` | close |
| `LAT_PULLDOWNS` | 10018 | `training / strength_training` | close |
| `DEADLIFTS` | 10019 | `training / strength_training` | close |
| `SHOULDER_PRESSES` | 10020 | `training / strength_training` | close |
| `FRONT_RAISES` | 10021 | `training / strength_training` | close |
| `LATERAL_RAISES` | 10022 | `training / strength_training` | close |
| `CRUNCH` | 10023 | `training / strength_training` | close |
| `LEG_RAISES` | 10024 | `training / strength_training` | close |
| `PLANK` | 10025 | `training / strength_training` | close |
| `ARM_CURLS` | 10026 | `training / strength_training` | close |
| `ARM_EXTENSIONS` | 10027 | `training / strength_training` | close |
| `SKATERS` | — | `training / cardio_training` | approximate |
| `HIGH_KNEES` | — | `training / cardio_training` | approximate |
| `INLINE_SKATING` | 11001 | `inline_skating / generic` | exact |
| `HANG_GLIDING` | 11002 | `hang_gliding / generic` | exact |
| `ARCHERY` | 11004 | `archery / generic` | exact |
| `HORSEBACK_RIDING` | 11005 | `horseback_riding / generic` | exact |
| `BIKING` | 11007 | `cycling / generic` | exact |
| `FLYING_DISC` | 11008 | `generic / generic` | approximate |
| `ROLLER_SKATING` | 11009 | `inline_skating / generic` | approximate |
| `AEROBICS` | 12001 | `training / cardio_training` | close |
| `HIKING` | 13001 | `hiking / generic` | exact |
| `ROCK_CLIMBING` | 13002 | `rock_climbing / generic` | exact |
| `BACKPACKING` | 13003 | `hiking / rucking` | close |
| `MOUNTAIN_BIKING` | 13004 | `cycling / mountain` | exact |
| `ORIENTEERING` | 13005 | `running / navigate` | approximate |
| `POOL_SWIMMING` | — | `swimming / lap_swimming` | close |
| `AQUA_AEROBICS` | 14002 | `training / cardio_training` | approximate |
| `CANOEING` | 14003 | `canoeing / generic` | exact |
| `SAILING` | 14004 | `sailing / generic` | exact |
| `SCUBA_DIVING` | 14005 | `diving / generic` | close |
| `SNORKELING` | 14006 | `snorkeling / generic` | exact |
| `KAYAKING` | 14007 | `kayaking / generic` | exact |
| `KITESURFING` | 14008 | `kitesurfing / generic` | exact |
| `RAFTING` | 14009 | `rafting / generic` | exact |
| `ROWING` | — | `rowing / generic` | exact |
| `WINDSURFING` | 14011 | `windsurfing / generic` | exact |
| `YACHTING` | 14012 | `sailing / generic` | close |
| `WATER_SKIING` | 14013 | `water_skiing / generic` | exact |
| `STEP_MACHINE` | 15001 | `fitness_equipment / stair_climbing` | exact |
| `WEIGHT_MACHINE` | 15002 | `training / strength_training` | close |
| `STATIONARY_BIKING` | 15003 | `cycling / indoor_cycling` | exact |
| `ROWING_MACHINE` | 15004 | `rowing / indoor_rowing` | exact |
| `TREADMILL` | 15005 | `running / treadmill` | close |
| `ELLIPTICAL` | 15006 | `fitness_equipment / elliptical` | exact |
| `STAIR_CLIMBING_MACHINE` | — | `fitness_equipment / stair_climbing` | exact |
| `CROSS_COUNTRY_SKIING` | 16001 | `cross_country_skiing / generic` | exact |
| `SKIING` | 16002 | `alpine_skiing / generic` | close |
| `ICE_DANCING` | 16003 | `ice_skating / generic` | close |
| `ICE_SKATING` | 16004 | `ice_skating / generic` | exact |
| `ICE_HOCKEY` | 16006 | `hockey / ice` | exact |
| `SNOWBOARDING` | 16007 | `snowboarding / generic` | exact |
| `ALPINE_SKIING` | 16008 | `alpine_skiing / generic` | exact |
| `SNOWSHOEING` | 16009 | `snowshoeing / generic` | exact |
| `TRIATHLON` | — | `multisport / triathlon` | exact |
| `DUATHLON` | — | `multisport / duathlon` | exact |
| `AQUATHLON` | — | `multisport / swim_run` | close |
| `AQUABIKE` | — | `multisport / generic` | approximate |
| `CROSS_TRIATHLON` | — | `multisport / triathlon` | close |
| `CROSS_DUATHLON` | — | `multisport / duathlon` | close |
| `BREAK` | — | `generic / generic` | approximate |
| `COOL_DOWN` | — | `training / generic` | approximate |
| `WARM_UP` | — | `training / generic` | approximate |
| `TRANSITION` | — | `transition / generic` | exact |
| `ZUMBA` | — | `dance / generic` | close |
| `OPEN_WATER_SWIMMING` | — | `swimming / open_water` | exact |

</details>

A copy of this reference is also kept in [SAMSUNG_EXERCISE_TYPES.md](SAMSUNG_EXERCISE_TYPES.md), and a compact commented list is included in `samsung_health_to_fit.py` for future development.

## Test first

For example, export up to three hikes:

```powershell
.\.venv\Scripts\python.exe .\samsung_health_to_fit.py --types 13001 --limit 3
```

The script should automatically find the main file such as:

```text
com.samsung.shealth.exercise.20260813124705.csv
```

and ignore similarly named supplementary files such as:

```text
com.samsung.shealth.exercise.extension.20260813124705.csv
com.samsung.shealth.exercise.route.20260813124705.csv
com.samsung.shealth.exercise.weather.20260813124705.csv
```

If auto-detection is ever ambiguous, you can still specify it manually:

```powershell
.\.venv\Scripts\python.exe .\samsung_health_to_fit.py `
  --exercise-csv ".\com.samsung.shealth.exercise.20260813124705.csv" `
  --types 13001 `
  --limit 3
```

Generated files go into:

```text
fit_exports\
```

Each FIT file is decoded again after creation and checked for FIT integrity/CRC, a Session, Lap, Activity, Record messages, and the expected sport/sub-sport.

A successful line looks similar to:

```text
[1/3] 2026-08-12 13001 Hiking -> hiking/generic  OK (CRC/decode OK; 5811 records; hiking/generic)
```

## Export all workouts

```powershell
.\.venv\Scripts\python.exe .\samsung_health_to_fit.py
```

Existing output files are skipped by default. To regenerate them:

```powershell
.\.venv\Scripts\python.exe .\samsung_health_to_fit.py --overwrite
```

If the converter encounters a Samsung exercise ID that is not in `SAMSUNG_TO_FIT`, it warns at the end and currently exports that activity as `generic / generic`. Before bulk importing it, check the commented reference block below `SAMSUNG_TO_FIT`; if the ID is documented there, review and enable the suggested mapping. If it is not there, treat it as a genuinely new/unknown Samsung export value and investigate it before importing.

## Import FIT files into Garmin Connect

Use Garmin Connect Web's **Import Data / Upload or Import Activity** workflow and upload the generated `.fit` files. Testing a few activities first is strongly recommended.

Check at least:

- activity type;
- date/time;
- duration;
- distance;
- calories;
- GPS map;
- heart rate;
- elevation/cadence where available.

---

# 4. Daily steps/calories/floors → CSV

> **Compatibility note:** Garmin officially documents CSV third-party import for files exported directly from Fitbit. The CSV files produced by this project reproduce the Fitbit-style daily activity format and have worked in real-world testing, but this is an unofficial compatibility workaround. Garmin may change its importer at any time.

`activity_fixed_v4.py` reads Samsung's daily activity, calorie and floor datasets and creates the full Fitbit-style column layout expected by Garmin's CSV importer.

Run it **from the Samsung Health export root**.

## Missing-data modes

The script has three explicit modes:

### `skip` — recommended/default

```powershell
py .\activity_fixed_v4.py --missing-data skip
```

Behavior:

- if **Calories Burned** is missing for a day, the entire day is skipped;
- other missing numeric fields are written as `0` (in practice this is commonly missing Floors);
- output files are named `activities-export-1.csv`, `activities-export-2.csv`, etc.

This is the safest practical default because importing a missing daily calorie total as `0` can cause Garmin to derive strange/negative resting-calorie values when active calories are present.

### `zero` — accept zeros for every missing field

```powershell
py .\activity_fixed_v4.py --missing-data zero
```

Behavior:

- every missing numeric field is written as `0`, including **Calories Burned**;
- output files are named `activities-zero-export-*.csv`;
- the script prints a warning before conversion.

Use this only if you explicitly accept that missing values and real zeroes are not the same thing.

### `strict` — only fully complete days

```powershell
py .\activity_fixed_v4.py --missing-data strict
```

Behavior:

- any day missing **any** expected numeric field is skipped;
- output files are named `activities-strict-export-*.csv`.

This may skip many otherwise useful days because Samsung floor data is often sparse.

## Output summary

At the end, the script reports:

- rows written;
- days skipped for missing total calories;
- days skipped as incomplete;
- how many rows had zero-filled values;
- missing-value counts by field;
- example skipped dates.

## Garmin CSV import settings

When Garmin identifies the file as Fitbit data, use settings matching the generated CSV:

- **Language:** English
- **Length:** centimeters / meters / kilometers
- **Weight:** kilograms
- **Date format:** `YYYY-MM-DD` (the Garmin UI may show an example such as `2026-12-31`)
- **Number format:** `1,234.56`

The number format does **not** require every integer to contain a thousands comma. A value such as `10490` is still compatible with that convention; the important part for decimals is the period (`15.01`).

---

# 5. Known limitations and cautions

- Garmin Connect's CSV import is strict. The full expected Fitbit-style column layout is required, and blank numeric cells may be rejected.
- Missing data and zero are not equivalent. This is why the daily-history script exposes three modes rather than silently guessing.
- Garmin and Samsung count activity/intensity minutes differently, so historical minute totals may not match exactly.
- Older Samsung data can be sparse. A workout may contain only a few sensor records even when its summary data is valid.
- Samsung Health export formats can change. If a future export changes column names or file layout, open an issue with a **sanitized** sample/header—never upload private health/location data publicly.
- Garmin Connect can be difficult to clean up after a large bad import. Test first.

---

# 6. Attribution

This project would not exist without **FromSamToGarm** by Philipp Imhof:

https://github.com/PhilippImhof/FromSamToGarm

`activity_fixed_v4.py` is adapted from FromSamToGarm's `activity.py`, and `samsung_health_to_fit.py` reuses/adapts the Samsung exercise-reading and GPS/live-data merging approach from FromSamToGarm's `exercises.py` while changing the output format from TCX to FIT.

FromSamToGarm is published under the GNU GPL v3. This repository is therefore also distributed under the GNU GPL v3. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md).

The Garmin FIT Python SDK is a separate dependency and is **not bundled or mirrored** in this repository. Users install it from Garmin's official package distribution through `pip`. This is deliberate: Garmin's FIT Protocol License contains restrictions on redistributing/providing the SDK and source files to other people or entities. See [DEPENDENCIES.md](DEPENDENCIES.md) for installation, private local caching, and official references.

---

# 7. Contributing

Issues and pull requests are welcome. Useful contributions include:

- additional verified Samsung exercise-type mappings;
- support for Samsung export-format changes;
- better preservation of sensor fields;
- sanitized regression tests for different Samsung export generations.

Please do not attach raw Samsung Health exports to public issues.

---

# 8. Self-tests

Install dependencies first, then run the complete suite:

```powershell
.\run_tests.ps1
```

Or directly:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite checks:

- all three daily-history missing-data modes;
- Samsung main exercise-CSV auto-detection when auxiliary exercise CSV files are present;
- a real Garmin FIT SDK smoke test that encodes a small FIT Activity, decodes it again, and validates its CRC/core structure.

The FIT smoke test **does not silently skip** when the Garmin dependency is missing. Run `setup.ps1` / install `requirements.txt` first. GitHub Actions does the same dependency installation automatically before running the full suite.
