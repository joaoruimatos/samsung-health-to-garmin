# Attribution

## FromSamToGarm

This project is based in part on **FromSamToGarm** by Philipp Imhof:

- Project: https://github.com/PhilippImhof/FromSamToGarm
- Upstream license: GNU General Public License v3.0

Specific relationship:

- `activity_fixed_v4.py` is adapted from FromSamToGarm's `activity.py` and preserves the general Garmin/Fitbit-style CSV conversion approach while adding newer Samsung date handling and explicit missing-data modes.
- `samsung_health_to_fit.py` uses/adapts the Samsung exercise CSV/JSON reading and GPS/live-data merging approach from FromSamToGarm's `exercises.py`, but replaces TCX output with Garmin FIT Activity encoding and verification.

Because this repository contains derivative/adapted GPL-3.0 code, it is distributed under the GNU GPL v3.0 as well. See `LICENSE`.

## Garmin FIT Python SDK

`samsung_health_to_fit.py` depends on Garmin's official FIT Python SDK (`garmin-fit-sdk`). The SDK is **not copied, mirrored, or bundled** in this repository. Users install it separately from Garmin's official PyPI/GitHub distribution.

- Project: https://github.com/garmin/fit-python-sdk
- PyPI: https://pypi.org/project/garmin-fit-sdk/
- Documentation: https://developer.garmin.com/fit/
- FIT Protocol License: https://thisisant.developer.garmin.com/pages/developer/ant/licensing/flexible-and-interoperable-data-transfer-fit-protocol-license/

The non-bundling decision is intentional. Garmin's FIT Protocol License permits use of the FIT SDK but includes restrictions on redistributing or providing the SDK/source files to other people or entities. `DEPENDENCIES.md` explains how users can create a private local pip cache without committing Garmin's package files to the public repository.

## Samsung Health and Garmin Connect

Samsung Health, Samsung, Garmin, Garmin Connect and FIT are trademarks or products of their respective owners. This repository is an independent community project and is not affiliated with or endorsed by Samsung or Garmin.
