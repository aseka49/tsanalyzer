import tempfile
import unittest
from pathlib import Path

from tsanalyzer.io import DataFormatError, load_csv


class LoadCsvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text: str) -> Path:
        path = self.dir / "data.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_loads_sorted_numeric_series(self):
        path = self._write("date,value\n2024-01-03,3\n2024-01-01,1\n2024-01-02,2\n")
        s = load_csv(path)
        self.assertEqual(list(s), [1.0, 2.0, 3.0])
        self.assertTrue(s.index.is_monotonic_increasing)

    def test_non_numeric_values_become_nan(self):
        s = load_csv(self._write("date,value\n2024-01-01,1\n2024-01-02,n/a\n"))
        self.assertEqual(int(s.isna().sum()), 1)

    def test_duplicate_timestamps_are_averaged(self):
        s = load_csv(self._write("date,value\n2024-01-01,1\n2024-01-01,3\n"))
        self.assertEqual(len(s), 1)
        self.assertAlmostEqual(s.iloc[0], 2.0)

    def test_custom_columns_and_separator(self):
        s = load_csv(self._write("t;temp\n2024-01-01;5\n"), time_col="t", value_col="temp", sep=";")
        self.assertEqual(s.name, "temp")

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_csv(self.dir / "nope.csv")

    def test_missing_column(self):
        with self.assertRaises(DataFormatError):
            load_csv(self._write("date,other\n2024-01-01,1\n"))

    def test_unparseable_timestamps(self):
        with self.assertRaises(DataFormatError):
            load_csv(self._write("date,value\nfoo,1\nbar,2\n"))


if __name__ == "__main__":
    unittest.main()
