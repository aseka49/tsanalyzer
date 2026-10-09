import unittest

import numpy as np
import pandas as pd

from tests.helpers import make_series
from tsanalyzer.stats import autocorrelation, describe
from tsanalyzer.trend import linear_trend, mann_kendall, moving_average


class DescribeTests(unittest.TestCase):
    def test_known_values(self):
        d = describe(pd.Series([1.0, 2.0, 3.0, 4.0, np.nan]))
        self.assertEqual(d["count"], 4)
        self.assertEqual(d["missing"], 1)
        self.assertAlmostEqual(d["mean"], 2.5)
        self.assertAlmostEqual(d["median"], 2.5)
        self.assertAlmostEqual(d["std"], np.std([1, 2, 3, 4], ddof=1))
        self.assertIn("skewness", d)

    def test_empty_series(self):
        self.assertEqual(describe(pd.Series([], dtype=float))["count"], 0)

    def test_single_value(self):
        d = describe(pd.Series([7.0]))
        self.assertEqual(d["std"], 0.0)
        self.assertNotIn("skewness", d)


class AutocorrelationTests(unittest.TestCase):
    def test_trend_has_high_lag1_autocorrelation(self):
        self.assertGreater(autocorrelation(make_series(noise=0.1)), 0.9)

    def test_invalid_lag(self):
        with self.assertRaises(ValueError):
            autocorrelation(make_series(), lag=0)
        with self.assertRaises(ValueError):
            autocorrelation(make_series(n=3), lag=5)


class LinearTrendTests(unittest.TestCase):
    def test_recovers_known_slope(self):
        res = linear_trend(make_series(slope_per_day=0.02))
        self.assertAlmostEqual(res.slope, 0.02, delta=0.002)
        self.assertAlmostEqual(res.slope_per_year, res.slope * 365.25)
        self.assertTrue(res.significant)
        self.assertGreater(res.r_squared, 0.8)

    def test_flat_series_is_not_significant(self):
        res = linear_trend(make_series(slope_per_day=0.0, seed=1))
        self.assertFalse(res.significant)

    def test_integer_index(self):
        s = pd.Series([1.0, 3.0, 5.0, 7.0])
        self.assertAlmostEqual(linear_trend(s).slope, 2.0)

    def test_to_dict(self):
        d = linear_trend(make_series()).to_dict()
        expected = {"slope", "slope_per_year", "intercept", "r_squared", "p_value", "significant"}
        self.assertEqual(set(d), expected)

    def test_too_short(self):
        with self.assertRaises(ValueError):
            linear_trend(pd.Series([1.0, 2.0]))


class MovingAverageTests(unittest.TestCase):
    def test_no_nans_at_edges(self):
        ma = moving_average(make_series(n=30), window=7)
        self.assertFalse(ma.isna().any())

    def test_constant_series(self):
        ma = moving_average(pd.Series([5.0] * 10), window=3)
        self.assertTrue(np.allclose(ma, 5.0))

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            moving_average(make_series(), window=0)


class MannKendallTests(unittest.TestCase):
    def test_increasing(self):
        self.assertEqual(mann_kendall(make_series(slope_per_day=0.02))["trend"], "increasing")

    def test_decreasing(self):
        self.assertEqual(mann_kendall(make_series(slope_per_day=-0.02))["trend"], "decreasing")

    def test_constant_series_has_no_trend(self):
        self.assertEqual(mann_kendall(pd.Series([1.0] * 10))["trend"], "no trend")

    def test_too_short(self):
        with self.assertRaises(ValueError):
            mann_kendall(pd.Series([1.0, 2.0, 3.0]))


if __name__ == "__main__":
    unittest.main()
