# Dependencies

This project deliberately keeps third-party dependencies small.

## Runtime requirements

### Python

- Python 3.9+ is recommended for this project.
- Garmin's FIT Python SDK itself supports Python 3.6+, but the project is developed and tested with modern Python 3 releases.

### Garmin FIT Python SDK

`samsung_health_to_fit.py` requires Garmin's official Python package:

```text
garmin-fit-sdk>=21.200.0,<22
```

The lower bound matters because Garmin added the Python `Encoder` class in FIT SDK 21.200.0. The converter uses that encoder to create binary `.fit` Activity files, and uses Garmin's decoder/integrity checks to verify files after writing.

Install all runtime dependencies with:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Or use the supplied setup helper:

```powershell
.\setup.ps1
```

## Offline/local dependency cache

If you want to keep a **personal local backup** of the Python dependency packages in case a package index is temporarily unavailable, run:

```powershell
.\setup.ps1 -CacheDependencies
```

This downloads the dependency wheel/source archive into `vendor/`.

Later, on the same computer or another computer where you are permitted to use your copy, you can install from that local cache with:

```powershell
.\setup.ps1 -Offline
```

### Do not commit the Garmin SDK package to this repository

The `vendor/` directory is configured so package archives/wheels are ignored by Git. This is intentional.

Garmin's FIT Protocol License permits use of the FIT SDK but contains restrictions on redistributing or providing the FIT SDK/source files to other people or entities. For that reason this project **does not bundle or mirror Garmin's SDK files**. Users install the dependency from Garmin's official PyPI/GitHub distribution themselves.

Official references:

- Garmin FIT Python SDK: https://github.com/garmin/fit-python-sdk
- Garmin FIT documentation: https://developer.garmin.com/fit/
- Garmin FIT Protocol License: https://thisisant.developer.garmin.com/pages/developer/ant/licensing/flexible-and-interoperable-data-transfer-fit-protocol-license/
- PyPI package: https://pypi.org/project/garmin-fit-sdk/

## Daily-activity converter

`activity_fixed_v4.py` uses only the Python standard library; it does not require the Garmin FIT SDK.

## Tests

The full test suite expects runtime dependencies to be installed. It does **not silently skip FIT dependency tests**.

Run:

```powershell
.\run_tests.ps1
```

or:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

GitHub Actions also installs `requirements.txt` before running the complete test suite.
