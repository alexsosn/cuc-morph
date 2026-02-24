"""Tests for plurale-tantum -m noun normalization refinement."""

import unittest

from pipeline.steps.base import TabletRow
from pipeline.steps.plurale_tantum_m import PluraleTantumMFixer


class _PluraleTantumGate:
    def __init__(self, plural_tokens=None, plurale_tantum_tokens=None) -> None:
        self._plural = set(plural_tokens or [])
        self._pl_tant = set(plurale_tantum_tokens or [])

    def is_plural_token(self, token: str, surface: str = "") -> bool:
        return token in self._plural

    def is_plurale_tantum_noun_token(self, token: str) -> bool:
        return token in self._pl_tant


class PluraleTantumMFixerTest(unittest.TestCase):
    def test_rewrites_missing_lexeme_m_before_plural_split(self) -> None:
        fixer = PluraleTantumMFixer(
            gate=_PluraleTantumGate(
                plural_tokens={"šmm (I)"},
                plurale_tantum_tokens={"šmm (I)"},
            )
        )
        row = TabletRow("1", "šmm", "šm(I)/m", "šmm (I)", "n. m.", "heavens", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "šm(m(I)/m")
        self.assertEqual(result.pos, "n. m. pl. tant.")

    def test_rewrites_unsplit_variant_for_terminal_m_lemma(self) -> None:
        fixer = PluraleTantumMFixer(
            gate=_PluraleTantumGate(
                plural_tokens={"šmm (I)"},
                plurale_tantum_tokens={"šmm (I)"},
            )
        )
        row = TabletRow("2", "šmm", "šmm(I)/", "šmm (I)", "n. m.", "heavens", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "šm(m(I)/m")
        self.assertEqual(result.pos, "n. m. pl. tant.")

    def test_injects_allograph_y_for_shmym(self) -> None:
        fixer = PluraleTantumMFixer(
            gate=_PluraleTantumGate(
                plural_tokens={"šmm (I)"},
                plurale_tantum_tokens={"šmm (I)"},
            )
        )
        row = TabletRow("3", "šmym", "šm(I)/m", "šmm (I)", "n. m.", "heavens", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "šm&y(m(I)/m")
        self.assertEqual(result.pos, "n. m. pl. tant.")

    def test_rewrites_suffix_form_with_terminal_m_base(self) -> None:
        fixer = PluraleTantumMFixer(
            gate=_PluraleTantumGate(
                plural_tokens={"šmm (I)"},
                plurale_tantum_tokens={"šmm (I)"},
            )
        )
        row = TabletRow("4", "šmmh", "šmm(I)/+h", "šmm (I)", "n. m.", "heavens", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "šm(m(I)/m+h")
        self.assertEqual(result.pos, "n. m. pl. tant.")

    def test_drops_spurious_nm_suffix_before_terminal_m_rewrite(self) -> None:
        fixer = PluraleTantumMFixer(
            gate=_PluraleTantumGate(
                plural_tokens={"pnm"},
                plurale_tantum_tokens={"pnm"},
            )
        )
        row = TabletRow("5", "pnm", "pn/m+nm", "pnm", "n. m.", "face", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "pn(m/m")
        self.assertEqual(result.pos, "n. m. pl. tant.")

    def test_marks_only_targeted_pos_variant_in_multi_variant_row(self) -> None:
        fixer = PluraleTantumMFixer(
            gate=_PluraleTantumGate(
                plural_tokens={"pnm"},
                plurale_tantum_tokens={"pnm"},
            )
        )
        row = TabletRow(
            "6",
            "pn",
            "pn/m; pn",
            "pnm; pn",
            "n. m.; functor",
            "face; lest",
            "",
        )
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "pn/m; pn")
        self.assertEqual(result.pos, "n. m. pl. tant.; functor")

    def test_keeps_non_target_lemma_unchanged(self) -> None:
        fixer = PluraleTantumMFixer(
            gate=_PluraleTantumGate(
                plural_tokens={"šlm (II)"},
                plurale_tantum_tokens=set(),
            )
        )
        row = TabletRow(
            "7",
            "šlmm",
            "šlm(II)/m",
            "šlm (II)",
            "n. m.",
            "communion victim / sacrifice",
            "",
        )
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "šlm(II)/m")
        self.assertEqual(result.pos, "n. m.")


if __name__ == "__main__":
    unittest.main()
