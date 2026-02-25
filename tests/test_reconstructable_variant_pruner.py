"""Tests for conservative pruning of non-reconstructable/clitic-only variants."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline.steps.reconstructable_variant_pruner import ReconstructableVariantPruner


class ReconstructableVariantPrunerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.step = ReconstructableVariantPruner()

    def test_prunes_non_reconstructable_and_clitic_rows_when_lexical_match_exists(self) -> None:
        content = (
            "id\tsurface form\tmorphological parsing\tDULAT\tPOS\tgloss\tcomments\n"
            "1\tkm\tk(III)\tk (III)\tSubordinating or completive functor\twhen\t\n"
            "1\tkm\tkm\tkm\tprep./conj./adv.\t\t\n"
            "1\tkm\t+km, +km=\t-km\t\t\t\n"
            "2\tmlk\tmlk(II)/\tmlk (II)\tn. m.\tking\t\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "KTU 1.test.tsv"
            path.write_text(content, encoding="utf-8")

            result = self.step.refine_file(path)

            self.assertEqual(result.rows_processed, 4)
            self.assertEqual(result.rows_changed, 2)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertIn("1\tkm\tkm\tkm\tprep./conj./adv.\t\t", lines)
            self.assertNotIn(
                "1\tkm\tk(III)\tk (III)\tSubordinating or completive functor\twhen\t",
                lines,
            )
            self.assertNotIn("1\tkm\t+km, +km=\t-km\t\t\t", lines)

    def test_keeps_all_clitic_rows_when_no_lexical_variant_exists(self) -> None:
        content = (
            "id\tsurface form\tmorphological parsing\tDULAT\tPOS\tgloss\tcomments\n"
            "1\tn\t~n\t-n (I)\tencl. morph.\t\t\n"
            "1\tn\t+n, +n=\t-n (III)\tsuff. pn. morph. 1.p.pl.\tour/us\t\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "KTU 1.test.tsv"
            path.write_text(content, encoding="utf-8")

            result = self.step.refine_file(path)

            self.assertEqual(result.rows_processed, 2)
            self.assertEqual(result.rows_changed, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_prunes_clitic_options_for_surface_y_when_lexical_variant_present(self) -> None:
        content = (
            "id\tsurface form\tmorphological parsing\tDULAT\tPOS\tgloss\tcomments\n"
            "1\ty\t+y, [y\t-y (I)\tprep. functor\tmy\t\n"
            "1\ty\t~y\t-y (II)\tprep. functor\tindeed\t\n"
            "1\ty\ty\ty\tprep. functor\toh!\t\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "KTU 1.test.tsv"
            path.write_text(content, encoding="utf-8")

            result = self.step.refine_file(path)

            self.assertEqual(result.rows_processed, 3)
            self.assertEqual(result.rows_changed, 2)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertIn("1\ty\ty\ty\tprep. functor\toh!\t", lines)
            self.assertNotIn("1\ty\t+y, [y\t-y (I)\tprep. functor\tmy\t", lines)
            self.assertNotIn("1\ty\t~y\t-y (II)\tprep. functor\tindeed\t", lines)

    def test_keeps_unresolved_row_for_manual_review(self) -> None:
        content = (
            "id\tsurface form\tmorphological parsing\tDULAT\tPOS\tgloss\tcomments\n"
            "1\tmlk\tmlk/\tmlk\tn. m.\tking\t\n"
            "1\tmlk\t?\t?\t?\t?\tDULAT: NOT FOUND\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "KTU 1.test.tsv"
            path.write_text(content, encoding="utf-8")

            result = self.step.refine_file(path)

            self.assertEqual(result.rows_processed, 2)
            self.assertEqual(result.rows_changed, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
