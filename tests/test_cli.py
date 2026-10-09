import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import make_series
from tsanalyzer.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        s = make_series(n=120, slope_per_day=0.03)
        s.iloc[10] = None
        s.iloc[60] = 500.0
        self.csv = self.dir / "data.csv"
        s.rename("temp_c").to_frame().reset_index(names="date").to_csv(self.csv, index=False)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([str(self.csv), "--value-col", "temp_c", *extra])
        return code, out.getvalue(), err.getvalue()

    def test_full_pipeline_writes_report_and_plot(self):
        report_path = self.dir / "out" / "report.json"
        plot_path = self.dir / "out" / "plot.png"
        code, stdout, _ = self._run("--report", str(report_path), "--plot", str(plot_path))
        self.assertEqual(code, 0)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["filled_missing"], 1)
        self.assertGreaterEqual(report["outliers_removed"], 1)
        self.assertEqual(report["mann_kendall"]["trend"], "increasing")
        self.assertTrue(plot_path.exists() and plot_path.stat().st_size > 0)
        self.assertEqual(json.loads(stdout), report)

    def test_resample_and_no_outlier_removal(self):
        code, stdout, _ = self._run("--resample", "W", "--outliers", "none")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["outliers_removed"], 0)

    def test_deseasonalize_option(self):
        code, stdout, _ = self._run("--deseasonalize", "month", "--outliers", "zscore")
        self.assertEqual(code, 0)
        report = json.loads(stdout)
        self.assertEqual(report["deseasonalized"], "month")
        self.assertAlmostEqual(report["statistics"]["mean"], 0.0, places=6)

    def test_error_returns_nonzero_exit_code(self):
        code, _, err = self._run("--time-col", "missing")
        self.assertEqual(code, 1)
        self.assertIn("error:", err)


if __name__ == "__main__":
    unittest.main()
