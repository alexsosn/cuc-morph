"""Unit tests for linter warning predicate helpers."""

import unittest

from linter.lint import (
    analysis_has_invalid_enclitic_plus,
    analysis_has_missing_plural_split,
    analysis_has_missing_suffix_plus,
    variant_has_baad_plus_n,
    variant_has_lexeme_terminal_single_suffix_split,
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

    def test_enclitic_plus_is_invalid(self) -> None:
        self.assertTrue(analysis_has_invalid_enclitic_plus("bˤd~+n"))
        self.assertFalse(analysis_has_invalid_enclitic_plus("bˤd~n"))

    def test_lexeme_final_n_split_detected(self) -> None:
        self.assertTrue(variant_has_lexeme_terminal_single_suffix_split("mṯ/+n", "mṯn"))
        self.assertTrue(variant_has_lexeme_terminal_single_suffix_split("lš/+n", "lšn"))
        self.assertFalse(variant_has_lexeme_terminal_single_suffix_split("bn(I)/+ny", "bn (I)"))

    def test_explicit_suffix_token_not_flagged(self) -> None:
        self.assertFalse(
            variant_has_lexeme_terminal_single_suffix_split("ḥr(I)/+n(I)", "ḥr (I),-n (I)")
        )

    def test_baad_enclitic_plus_detected(self) -> None:
        self.assertTrue(variant_has_baad_plus_n("bˤd+n", "bʕd"))
        self.assertFalse(variant_has_baad_plus_n("ˤl(I)+n", "ʕl (I)"))


if __name__ == "__main__":
    unittest.main()
