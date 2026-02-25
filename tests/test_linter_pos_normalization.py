"""Tests for POS normalization in DULAT validation."""

import unittest

from linter.lint import normalize_pos_option_for_validation


class LinterPosNormalizationTest(unittest.TestCase):
    def test_strips_nominal_number_markers_for_validation(self) -> None:
        self.assertEqual(normalize_pos_option_for_validation("n. m. du."), "n")
        self.assertEqual(normalize_pos_option_for_validation("n. f. pl."), "n")
        self.assertEqual(normalize_pos_option_for_validation("adj. f. sg."), "adj.")


if __name__ == "__main__":
    unittest.main()
