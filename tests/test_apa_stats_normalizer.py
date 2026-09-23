"""
Unit tests for APAStatsNormalizer
"""

import unittest
from book_processor.parsers.math.apa_stats_normalizer import APAStatsNormalizer


class TestAPAStatsNormalizer(unittest.TestCase):

    def test_normalize_f_test(self):
        s = "ANOVA revealed a significant main effect, F(2, 82) = 19.2, p < .001, on scores."
        res = APAStatsNormalizer.normalize_text(s)
        self.assertIn("$F(2, 82) = 19.2, p < .001$", res)

    def test_normalize_t_test(self):
        s = "Post-hoc tests indicated t(84) = 2.45, p < .05, for the treatment."
        res = APAStatsNormalizer.normalize_text(s)
        self.assertIn("$t(84) = 2.45, p < .05$", res)

    def test_normalize_correlations(self):
        s = "Riskiness was correlated with sensation seeking (r = .45, p < .01)."
        res = APAStatsNormalizer.normalize_text(s)
        self.assertIn("$r = .45, p < .01$", res)

    def test_normalize_beta_and_delta_r2(self):
        s = "In Step 2, ΔR² = .08 and β = .32 were significant."
        res = APAStatsNormalizer.normalize_text(s)
        self.assertIn("$\\Delta R^2 = .08$", res)
        self.assertIn("$\\beta = .32$", res)

    def test_normalize_sample_size_and_ps(self):
        s = "In the present sample (N = 86), age effects were not significant (ps > .05)."
        res = APAStatsNormalizer.normalize_text(s)
        self.assertIn("$N = 86$", res)
        self.assertIn("$p\\text{s} > .05$", res)

    def test_normalize_m_and_sd(self):
        s = "Participants reported high scores (M = 12.4, SD = 3.2)."
        res = APAStatsNormalizer.normalize_text(s)
        self.assertIn("$M = 12.4, SD = 3.2$", res)


if __name__ == "__main__":
    unittest.main()
