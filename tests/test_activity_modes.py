import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("activity_fixed_v4", ROOT / "activity_fixed_v4.py")
activity = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(activity)


class ActivityModeTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "2020-01-01": {
                "Calories Burned": 2000,
                "Steps": 10000,
                "Distance": 7.5,
                "Floors": 5,
                "Minutes Sedentary": 0,
                "Minutes Lightly Active": 80,
                "Minutes Fairly Active": 0,
                "Minutes Very Active": 20,
                "Activity Calories": 600,
            },
            # Missing total calories and floors.
            "2020-01-02": {
                "Steps": 8000,
                "Distance": 6.0,
                "Minutes Sedentary": 0,
                "Minutes Lightly Active": 60,
                "Minutes Fairly Active": 0,
                "Minutes Very Active": 10,
                "Activity Calories": 450,
            },
            # Has total calories, but no floors.
            "2020-01-03": {
                "Calories Burned": 2200,
                "Steps": 9000,
                "Distance": 6.8,
                "Minutes Sedentary": 0,
                "Minutes Lightly Active": 70,
                "Minutes Fairly Active": 0,
                "Minutes Very Active": 15,
                "Activity Calories": 500,
            },
        }

    def test_skip_mode(self):
        with tempfile.TemporaryDirectory() as td:
            stats = activity.write_to_files(self.data, "skip", output_dir=Path(td))
            self.assertEqual(stats["rows_written"], 2)
            self.assertEqual(stats["skipped_missing_calories"], 1)
            self.assertEqual(stats["zero_filled_by_field"]["Floors"], 1)

    def test_zero_mode(self):
        with tempfile.TemporaryDirectory() as td:
            stats = activity.write_to_files(self.data, "zero", output_dir=Path(td))
            self.assertEqual(stats["rows_written"], 3)
            self.assertEqual(stats["zero_filled_by_field"]["Calories Burned"], 1)

    def test_strict_mode(self):
        with tempfile.TemporaryDirectory() as td:
            stats = activity.write_to_files(self.data, "strict", output_dir=Path(td))
            self.assertEqual(stats["rows_written"], 1)
            self.assertEqual(stats["skipped_incomplete"], 2)

    def test_generated_csv_has_full_schema(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            stats = activity.write_to_files(self.data, "skip", output_dir=td)
            path = Path(stats["output_files"][0])
            with path.open("r", encoding="utf-8", newline="") as f:
                self.assertEqual(f.readline().strip(), "Activities")
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, activity.COLUMNS)
                rows = list(reader)
                self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
