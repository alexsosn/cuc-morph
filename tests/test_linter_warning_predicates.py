"""Unit tests for linter warning predicate helpers."""

import unittest

from linter.lint import (
    analysis_has_missing_plural_split,
    analysis_has_missing_suffix_plus,
)


class LinterWarningPredicateTest(unittest.TestCase):
    def test_plural_missing_split_detected_for_lemma_style(self) -> None:
        self.assertTrue(analysis_has_missing_plural_split("il(I)/", "ilm"))

    def test_plural_not_flagged_for_singular_t_lemma(self) -> None:
        self.assertFalse(analysis_has_missing_plural_split("dqt(I)/", "dqt"))

    def test_suffix_missing_plus_detected_for_reconstructed_base(self) -> None:
        self.assertTrue(analysis_has_missing_suffix_plus("l(I)", "ln"))

    def test_suffix_missing_plus_detected_for_explicit_suffix_letters(self) -> None:
        self.assertTrue(analysis_has_missing_suffix_plus("npšh/", "npšh"))

    def test_suffix_not_flagged_without_suffix_shape(self) -> None:
        self.assertFalse(analysis_has_missing_suffix_plus("ˤl(I)", "ˤl"))


if __name__ == "__main__":
    unittest.main()
