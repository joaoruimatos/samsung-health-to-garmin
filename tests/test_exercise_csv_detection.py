import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExerciseCsvDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "samsung_health_to_fit", ROOT / "samsung_health_to_fit.py"
        )
        cls.mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.mod)

    def test_prefers_plain_exercise_csv_over_auxiliary_files(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            main = td / "com.samsung.shealth.exercise.20260813124705.csv"
            main.write_text(
                "metadata\n"
                "com.samsung.health.exercise.datauuid,"
                "com.samsung.health.exercise.start_time,"
                "com.samsung.health.exercise.exercise_type\n"
                "abc,2026-01-01 00:00:00.000,1001\n",
                encoding="utf-8",
            )

            for name in (
                "com.samsung.shealth.exercise.extension.20260813124705.csv",
                "com.samsung.shealth.exercise.route.20260813124705.csv",
                "com.samsung.shealth.exercise.weather.20260813124705.csv",
                "com.samsung.shealth.exercise.periodization_training_program.20260813124705.csv",
            ):
                (td / name).write_text("metadata\nfoo,bar\n1,2\n", encoding="utf-8")

            found = self.mod.find_exercise_csv(td, None)
            self.assertEqual(found, main)


if __name__ == "__main__":
    unittest.main()
