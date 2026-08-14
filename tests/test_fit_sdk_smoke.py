import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "samsung_health_to_fit", ROOT / "samsung_health_to_fit.py"
)
fitmod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(fitmod)


class GarminFitSdkSmokeTests(unittest.TestCase):
    def test_official_sdk_can_encode_and_decode_fit(self):
        # This test intentionally does NOT skip when garmin-fit-sdk is missing.
        # A normal project setup/CI install must provide requirements.txt first.
        fitmod.load_fit_sdk()

        start = fitmod.datetime_to_fit(
            fitmod.dt.datetime(2026, 1, 1, tzinfo=fitmod.dt.timezone.utc)
        )
        messages = [
            {
                "mesg_num": fitmod.Profile["mesg_num"]["FILE_ID"],
                "type": "activity",
                "manufacturer": "development",
                "product": 0,
                "time_created": start,
                "serial_number": 1,
            },
            {
                "mesg_num": fitmod.Profile["mesg_num"]["EVENT"],
                "timestamp": start,
                "event": "timer",
                "event_type": "start",
            },
            {
                "mesg_num": fitmod.Profile["mesg_num"]["RECORD"],
                "timestamp": start,
            },
            {
                "mesg_num": fitmod.Profile["mesg_num"]["RECORD"],
                "timestamp": start + 60,
            },
            {
                "mesg_num": fitmod.Profile["mesg_num"]["EVENT"],
                "timestamp": start + 60,
                "event": "timer",
                "event_type": "stop",
            },
            {
                "mesg_num": fitmod.Profile["mesg_num"]["LAP"],
                "message_index": 0,
                "timestamp": start + 60,
                "start_time": start,
                "total_elapsed_time": 60.0,
                "total_timer_time": 60.0,
                "sport": "walking",
                "sub_sport": "generic",
            },
            {
                "mesg_num": fitmod.Profile["mesg_num"]["SESSION"],
                "message_index": 0,
                "timestamp": start + 60,
                "start_time": start,
                "total_elapsed_time": 60.0,
                "total_timer_time": 60.0,
                "sport": "walking",
                "sub_sport": "generic",
                "first_lap_index": 0,
                "num_laps": 1,
            },
            {
                "mesg_num": fitmod.Profile["mesg_num"]["ACTIVITY"],
                "timestamp": start + 60,
                "num_sessions": 1,
                "total_timer_time": 60.0,
            },
        ]

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "smoke.fit"
            fitmod.encode_fit(messages, path)
            ok, detail = fitmod.verify_fit(path, "walking", "generic")
            self.assertTrue(ok, detail)
            self.assertGreater(path.stat().st_size, 20)


if __name__ == "__main__":
    unittest.main()
