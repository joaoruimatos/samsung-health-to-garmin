# Changelog

## v1.3

- Added `DEPENDENCIES.md` with explicit runtime requirements, official dependency references, Garmin FIT SDK licensing notes, and private/offline cache instructions.
- Added `setup.ps1` to create the virtual environment, install dependencies, cache dependencies privately, or install from an offline cache.
- Added `run_tests.ps1` and a GitHub Actions workflow that installs requirements and runs the full test suite.
- Refactored `samsung_health_to_fit.py` to load Garmin's FIT SDK lazily, so mapping/reference commands and CSV-detection tests do not require the SDK import.
- Removed the silent skip from the exercise-CSV test.
- Added a Garmin FIT SDK smoke test that encodes and decodes a FIT Activity and validates it.
- Added `vendor/README.md` and Git ignore rules so users can maintain a private dependency cache without publishing Garmin SDK files.
- Clarified that Garmin SDK files are not bundled/mirrored because Garmin's FIT Protocol License restricts redistribution.

## 1.1.0 - 2026-08-14

- Added a complete reference for Samsung's documented legacy numeric exercise IDs.
- Added copy/paste-ready **commented** Garmin FIT mapping suggestions for every documented Samsung numeric ID not enabled by default.
- Added mapping confidence labels (`exact`, `close`, `approximate`, `custom`) so untested fallbacks are clearly distinguished from direct FIT equivalents.
- Expanded the README with the ten enabled/tested mappings plus a collapsible table of the remaining documented IDs.
- Improved the unknown-ID warning to point users to the mapping reference before bulk import.

## 1.0.0 - 2026-08-14

- Added Samsung Health recorded-workout conversion to Garmin FIT using Garmin's Python FIT SDK.
- Added Walking, Running, Hiking, Cycling, Swimming, Treadmill, indoor cycling and training mappings for the Samsung exercise IDs verified during migration testing.
- Added post-write FIT integrity/CRC and sport/sub-sport verification.
- Added automatic selection of the main Samsung exercise CSV while ignoring supplementary exercise files such as extension, route and weather tables.
- Added modern Samsung `day_time` text-date support to the daily activity converter.
- Added three daily-history missing-data modes: `skip`, `zero`, and `strict`.
- Added documentation, attribution, GPL-3.0 license, privacy-oriented `.gitignore`, and regression tests.
