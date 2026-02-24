"""Tests for III-aleph noun/adjective case-vowel normalization."""

import unittest

from pipeline.steps.base import TabletRow
from pipeline.steps.iii_aleph_case_fixer import IIIAlephCaseFixer


class IIIAlephCaseFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = IIIAlephCaseFixer()

    def test_rewrites_rpi_from_rpu_headword(self) -> None:
        row = TabletRow("1", "rpi", "rpu/", "rpủ", "n. m.", "healer", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "rp(u/&i")

    def test_rewrites_homonym_variant_with_surface_a(self) -> None:
        row = TabletRow("2", "ṣba", "ṣbu(II)/", "ṣbủ (II)", "n. m.", "setting", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "ṣb(u(II)/&a")

    def test_rewrites_nni_and_preserves_homonym(self) -> None:
        row = TabletRow("3", "nni", "nnu(I)/", "nnủ (I)", "n. m.", "Ammi", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "nn(u(I)/&i")

    def test_skips_when_analysis_already_reconstructs_surface(self) -> None:
        row = TabletRow("4", "rpu", "rpu/", "rpủ", "n. m.", "healer", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "rpu/")

    def test_skips_non_nominal_pos(self) -> None:
        row = TabletRow("5", "yṣa", "yṣu[", "/y-ṣ-ʔ/", "vb", "to go out", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "yṣu[")

    def test_rewrites_only_aligned_target_variant(self) -> None:
        row = TabletRow(
            "6",
            "rpi",
            "rpu/; !y!qrʔ[",
            "rpủ; /q-r-ʔ/",
            "n. m.; vb",
            "healer; to call",
            "",
        )
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "rp(u/&i; !y!qrʔ[")


if __name__ == "__main__":
    unittest.main()
