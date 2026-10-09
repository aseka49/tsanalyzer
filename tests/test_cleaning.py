import unittest

import numpy as np
import pandas as pd

from tests.helpers import make_series
from tsanalyzer.cleaning import deseasonalize, fill_missing, remove_outliers, resample


class FillMissingTests(unittest.TestCase):
    def setUp(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        self.s = pd.Series([1.0, np.nan, 3.0, np.nan, 5.0], index=idx)

    def test_linear_interpolation(self):
        self.assertEqual(list(fill_missing(self.s, "linear")), [1, 2, 3, 4, 5])

    def test_interpolation_respects_uneven_time_gaps(self):
        idx = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-05"])
        s = pd.Series([0.0, np.nan, 4.0], index=idx)
        self.assertAlmostEqual(fill_missing(s).iloc[1], 1.0)

    def test_forward_and_backward_fill(self):
        self.assertEqual(list(fill_missing(self.s, "ffill")), [1, 1, 3, 3, 5])
        self.assertEqual(list(fill_missing(self.s, "bfill")), [1, 3, 3, 5, 5])

    def test_drop(self):
        self.assertEqual(len(fill_missing(self.s, "drop")), 3)

    def test_non_datetime_index(self):
        s = pd.Series([1.0, np.nan, 3.0])
        self.assertEqual(list(fill_missing(s)), [1, 2, 3])

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            fill_missing(self.s, "magic")


class OutlierTests(unittest.TestCase):
    def setUp(self):
        self.s = make_series(n=200, slope_per_day=0.0)
        self.s.iloc[50] = 100.0
        self.s.iloc[120] = -80.0

    def test_iqr_detects_injected_outliers(self):
        clean, out = remove_outliers(self.s, "iqr")
        self.assertIn(self.s.index[50], out.index)
        self.assertIn(self.s.index[120], out.index)
        self.assertEqual(len(clean) + len(out), len(self.s))

    def test_zscore_detects_injected_outliers(self):
        _, out = remove_outliers(self.s, "zscore")
        self.assertEqual(set(out.index), {self.s.index[50], self.s.index[120]})

    def test_threshold_controls_sensitivity(self):
        _, strict = remove_outliers(self.s, "iqr", threshold=0.5)
        _, loose = remove_outliers(self.s, "iqr", threshold=3.0)
        self.assertGreater(len(strict), len(loose))

    def test_constant_series_has_no_outliers(self):
        s = pd.Series([2.0] * 10)
        _, out = remove_outliers(s, "zscore")
        self.assertTrue(out.empty)

    def test_empty_series(self):
        clean, out = remove_outliers(pd.Series([], dtype=float))
        self.assertTrue(clean.empty and out.empty)

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            remove_outliers(self.s, "dbscan")


class ResampleTests(unittest.TestCase):
    def test_weekly_mean(self):
        s = make_series(n=14, noise=0.0, slope_per_day=0.0)
        weekly = resample(s, "W")
        self.assertTrue(np.allclose(weekly.to_numpy(), 10.0))

    def test_requires_datetime_index(self):
        with self.assertRaises(TypeError):
            resample(pd.Series([1, 2, 3]))

    def test_bad_aggregation(self):
        with self.assertRaises(ValueError):
            resample(make_series(n=5), how="mode")


class DeseasonalizeTests(unittest.TestCase):
    def setUp(self):
        idx = pd.date_range("2020-01-01", "2023-12-31", freq="D")
        seasonal = 20 * np.sin(2 * np.pi * idx.dayofyear.to_numpy() / 365.25)
        self.s = pd.Series(seasonal, index=idx, name="temp")

    def test_removes_pure_seasonal_signal(self):
        anomalies = deseasonalize(self.s, "dayofyear")
        self.assertLess(anomalies.abs().max(), 1e-9)
        self.assertEqual(anomalies.name, "temp_anomaly")

    def test_monthly_climatology_has_zero_mean_per_month(self):
        anomalies = deseasonalize(self.s, "month")
        per_month = anomalies.groupby(anomalies.index.month).mean()
        self.assertTrue(np.allclose(per_month, 0.0))

    def test_requires_datetime_index(self):
        with self.assertRaises(TypeError):
            deseasonalize(pd.Series([1.0, 2.0]))

    def test_bad_period(self):
        with self.assertRaises(ValueError):
            deseasonalize(self.s, "week")


if __name__ == "__main__":
    unittest.main()
