#!/usr/bin/env python3
"""Convert Samsung Health daily summaries to Garmin/Fitbit-style CSV files.

This script is adapted from the activity.py script in FromSamToGarm:
https://github.com/PhilippImhof/FromSamToGarm

It adds support for newer Samsung Health date formats and three explicit
missing-data modes for Garmin Connect's strict Fitbit-style CSV importer.

License: GPL-3.0-only (see LICENSE in this repository).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import glob
from pathlib import Path
from typing import Dict, Iterable


COLUMNS = [
    "Date",
    "Calories Burned",
    "Steps",
    "Distance",
    "Floors",
    "Minutes Sedentary",
    "Minutes Lightly Active",
    "Minutes Fairly Active",
    "Minutes Very Active",
    "Activity Calories",
]


class ActivityConversionError(RuntimeError):
    """Raised when Samsung Health source files cannot be read safely."""


def parse_samsung_date(value: str) -> str:
    """Convert Samsung Health day_time values to YYYY-MM-DD.

    Older exports may store day_time as Unix epoch milliseconds. Newer exports
    may store it as text such as ``2018-03-19 00:00:00.000``. Both are accepted.
    """
    value = (value or "").strip()
    if not value:
        raise ValueError("Empty Samsung Health date/time value")

    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return value[:10]

    try:
        timestamp = float(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported Samsung Health date/time value: {value!r}") from exc

    if abs(timestamp) > 10_000_000_000:
        timestamp /= 1000

    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


def _find_one(pattern: str, label: str) -> str:
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise ActivityConversionError(f"No {label} data found (pattern: {pattern}).")
    if len(matches) > 1:
        names = "\n  ".join(matches)
        raise ActivityConversionError(
            f"More than one {label} CSV was found. Keep only the intended export in "
            f"this folder or run the script from the correct Samsung Health export root:\n  {names}"
        )
    return matches[0]

def _open_dict_reader(path: str):
    """Open a Samsung CSV and tolerate its optional first metadata/version line."""
    f = open(path, "r", encoding="utf-8-sig", newline="")
    first_line = f.readline()
    # Most Samsung exports have a metadata/version line first. If the first line
    # already looks like a normal CSV header, rewind instead of skipping it.
    if "," in first_line and any(
        token in first_line
        for token in ("day_time", "start_time", "step_count", "rest_calorie", "floor")
    ):
        f.seek(0)
    return f, csv.DictReader(f)


def fetch_floor_data() -> Dict[str, int]:
    """Fetch and consolidate floors climbed by date."""
    filename = _find_one("com.samsung.health.floors_climbed.*.csv", "floors")
    f, reader = _open_dict_reader(filename)
    try:
        result: Dict[str, int] = {}
        for row in reader:
            raw_date = (row.get("start_time") or "").strip()
            if not raw_date:
                continue
            date = parse_samsung_date(raw_date)
            raw_floor = (row.get("floor") or "").strip()
            if not raw_floor:
                continue
            floors = int(float(raw_floor))
            result[date] = result.get(date, 0) + floors
        return result
    finally:
        f.close()


def fetch_calorie_data() -> Dict[str, int]:
    """Fetch total daily calories (resting + active) by date."""
    filename = _find_one(
        "com.samsung.shealth.calories_burned.details.*.csv", "calorie"
    )
    f, reader = _open_dict_reader(filename)
    try:
        result: Dict[str, int] = {}
        prefix = "com.samsung.shealth.calories_burned."
        day_key = prefix + "day_time"
        rest_key = prefix + "rest_calorie"
        active_key = prefix + "active_calorie"

        for row in reader:
            raw_day = (row.get(day_key) or "").strip()
            raw_rest = (row.get(rest_key) or "").strip()
            raw_active = (row.get(active_key) or "").strip()
            if not raw_day or not raw_rest or not raw_active:
                continue
            date = parse_samsung_date(raw_day)
            rest_calorie = float(raw_rest)
            active_calorie = float(raw_active)
            result[date] = int(round(rest_calorie + active_calorie, 0))
        return result
    finally:
        f.close()


def fetch_activity_data() -> Dict[str, dict]:
    """Fetch Samsung Health daily activity summaries."""
    filename = _find_one(
        "com.samsung.shealth.activity.day_summary.*.csv", "daily activity"
    )
    f, reader = _open_dict_reader(filename)
    try:
        result: Dict[str, dict] = {}
        for row in reader:
            raw_day = (row.get("day_time") or "").strip()
            if not raw_day:
                continue
            date = parse_samsung_date(raw_day)

            raw_steps = (row.get("step_count") or "").strip()
            if not raw_steps:
                # Missing step_count is unknown data, not a genuine zero-step day.
                # Skip only rows where Samsung did not provide a step total at all.
                continue

            # Keep genuine zero-step days.
            step_count = int(float(raw_steps))

            distance = round(float(row.get("distance") or 0) / 1000, 2)
            calorie = float(row.get("calorie") or 0)
            run_time = int(float(row.get("run_time") or 0) / 60000)
            walk_time = int(float(row.get("walk_time") or 0) / 60000)

            result[date] = {
                "Steps": step_count,
                "Distance": distance,
                "Minutes Sedentary": 0,
                "Minutes Lightly Active": walk_time,
                "Minutes Fairly Active": 0,
                "Minutes Very Active": run_time,
                "Activity Calories": int(calorie),
            }
        return result
    finally:
        f.close()


def merge_data(
    floors: Dict[str, int], calories: Dict[str, int], activities: Dict[str, dict]
) -> Dict[str, dict]:
    """Merge only dates that have a Samsung daily activity summary.

    This avoids creating calorie-only or floor-only rows with invented step data.
    """
    merged: Dict[str, dict] = {}
    for date, activity in activities.items():
        row = dict(activity)
        if date in calories:
            row["Calories Burned"] = calories[date]
        if date in floors:
            row["Floors"] = floors[date]
        merged[date] = row
    return dict(sorted(merged.items()))


def _missing_fields(row: dict) -> list[str]:
    return [
        column
        for column in COLUMNS
        if column != "Date" and (column not in row or row[column] in ("", None))
    ]


def _output_prefix(mode: str) -> str:
    return {
        "skip": "activities-export",
        "zero": "activities-zero-export",
        "strict": "activities-strict-export",
    }[mode]


def write_to_files(
    data: Dict[str, dict],
    mode: str = "skip",
    lines_per_file: int = 100,
    output_dir: Path | None = None,
) -> dict:
    """Write Garmin/Fitbit-style activity CSV files.

    Modes:
      skip   (recommended/default): skip days missing ``Calories Burned``;
             zero-fill other missing fields (normally only Floors).
      zero:  zero-fill every missing numeric field, including total calories.
             This can create misleading Garmin calorie metrics and is provided
             only for users who explicitly accept that trade-off.
      strict: skip any day missing any expected numeric field.
    """
    if mode not in {"skip", "zero", "strict"}:
        raise ValueError("mode must be one of: skip, zero, strict")
    if lines_per_file < 1:
        raise ValueError("lines_per_file must be >= 1")

    output_dir = (output_dir or Path.cwd()).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = _output_prefix(mode)
    lines_written = 0
    skipped_missing_calories = 0
    skipped_incomplete = 0
    zero_filled_rows = 0
    zero_filled_by_field = {column: 0 for column in COLUMNS if column != "Date"}
    missing_by_field = {column: 0 for column in COLUMNS if column != "Date"}
    skipped_examples: list[tuple[str, list[str]]] = []
    output_files: list[str] = []

    dest = None
    writer = None

    try:
        for date in sorted(data):
            row = dict(data[date])
            row["Date"] = date
            missing = _missing_fields(row)

            for field in missing:
                missing_by_field[field] += 1

            if mode == "strict" and missing:
                skipped_incomplete += 1
                if len(skipped_examples) < 10:
                    skipped_examples.append((date, missing))
                continue

            if mode == "skip" and "Calories Burned" in missing:
                skipped_missing_calories += 1
                if len(skipped_examples) < 10:
                    skipped_examples.append((date, missing))
                continue

            if missing:
                zero_filled_rows += 1
                for field in missing:
                    row[field] = 0
                    zero_filled_by_field[field] += 1

            if lines_written % lines_per_file == 0:
                if dest is not None:
                    dest.close()
                filename = output_dir / f"{prefix}-{lines_written // lines_per_file + 1}.csv"
                output_files.append(str(filename))
                dest = filename.open("w", encoding="utf-8", newline="")
                dest.write("Activities\n")
                writer = csv.DictWriter(
                    dest,
                    fieldnames=COLUMNS,
                    lineterminator="\n",
                    quoting=csv.QUOTE_ALL,
                )
                writer.writeheader()

            assert writer is not None
            writer.writerow(row)
            lines_written += 1
    finally:
        if dest is not None:
            dest.close()

    return {
        "mode": mode,
        "rows_written": lines_written,
        "skipped_missing_calories": skipped_missing_calories,
        "skipped_incomplete": skipped_incomplete,
        "zero_filled_rows": zero_filled_rows,
        "zero_filled_by_field": zero_filled_by_field,
        "missing_by_field": missing_by_field,
        "skipped_examples": skipped_examples,
        "output_files": output_files,
    }


def print_summary(stats: dict) -> None:
    print()
    print("Summary")
    print(f"  Missing-data mode: {stats['mode']}")
    print(f"  Rows written: {stats['rows_written']}")
    print(f"  Rows skipped for missing total calories: {stats['skipped_missing_calories']}")
    print(f"  Rows skipped as incomplete: {stats['skipped_incomplete']}")
    print(f"  Rows containing one or more zero-filled fields: {stats['zero_filled_rows']}")

    missing_counts = stats["missing_by_field"]
    if any(missing_counts.values()):
        print("  Missing source values encountered:")
        for field, count in missing_counts.items():
            if count:
                print(f"    {field}: {count} day(s)")

    zero_counts = stats["zero_filled_by_field"]
    if any(zero_counts.values()):
        print("  Values replaced with 0:")
        for field, count in zero_counts.items():
            if count:
                print(f"    {field}: {count} day(s)")

    if stats["skipped_examples"]:
        print("  Example skipped days:")
        for date, missing in stats["skipped_examples"]:
            print(f"    {date}: missing {', '.join(missing)}")

    if not stats["output_files"]:
        print("  No CSV files were created.")
    else:
        print(f"  Files created: {len(stats['output_files'])}")
        print(f"  Output pattern: {Path(stats['output_files'][0]).name.rsplit('-', 1)[0]}-*.csv")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert Samsung Health daily activity summaries to Garmin/Fitbit-style CSV files."
        )
    )
    parser.add_argument(
        "--missing-data",
        choices=("skip", "zero", "strict"),
        default="skip",
        help=(
            "How to handle missing values: 'skip' (default) skips days missing total "
            "Calories Burned and zero-fills other missing fields; 'zero' writes 0 for all "
            "missing numeric fields; 'strict' skips any day missing any expected field."
        ),
    )
    parser.add_argument(
        "--lines-per-file",
        type=int,
        default=100,
        help="Maximum data rows per output CSV (default: 100).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Folder for generated CSV files (default: current directory).",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    if args.missing_data == "zero":
        print(
            "WARNING: --missing-data zero writes 0 for missing total daily calories.\n"
            "Garmin may interpret that as a real total of zero and derive negative resting\n"
            "calories when active calories exist. Use this mode only if you accept that risk.\n"
        )

    try:
        data = merge_data(fetch_floor_data(), fetch_calorie_data(), fetch_activity_data())
        stats = write_to_files(
            data,
            mode=args.missing_data,
            lines_per_file=args.lines_per_file,
            output_dir=args.output_dir,
        )
    except (ActivityConversionError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print_summary(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
