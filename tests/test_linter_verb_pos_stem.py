"""Regression tests for verb POS stem labels in column 5."""

import tempfile
import unittest
from pathlib import Path

from linter.lint import DulatEntry, lint_file, normalize_surface, normalize_udb


class LinterVerbPosStemTest(unittest.TestCase):
    WARNING = "Verb POS should include stem label(s):"
    POS_ERROR = "POS token '"

    def _lint_messages(self, pos_value: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            out_dir = root / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / "KTU 1.test.tsv"
            path.write_text(
                (
                    "id\tsurface form\tmorphological parsing\tDULAT\tPOS\tgloss\tcomments\n"
                    f"1\tytn\t!y!ytn[\t/y-t-n/\t{pos_value}\tto give\t\n"
                ),
                encoding="utf-8",
            )

            ytn_entry = DulatEntry(
                entry_id=1,
                lemma="/y-t-n/",
                homonym="",
                pos="vb",
                gloss="to give",
                morph="G, prefc.",
                form_text="ytn",
            )

            dulat_forms = {normalize_surface("ytn"): [ytn_entry]}
            entry_meta = {1: ("/y-t-n/", "", "vb", "to give")}
            lemma_map = {normalize_surface("/y-t-n/"): [ytn_entry]}
            entry_stems = {1: {"G"}}
            entry_gender = {}
            udb_words = {normalize_udb("ytn")}

            issues = lint_file(
                path=path,
                dulat_forms=dulat_forms,
                entry_meta=entry_meta,
                lemma_map=lemma_map,
                entry_stems=entry_stems,
                entry_gender=entry_gender,
                udb_words=udb_words,
                baseline=None,
                input_format="auto",
                db_checks=True,
            )
            return [issue.message for issue in issues]

    def test_warns_when_verb_pos_has_no_stem(self) -> None:
        messages = self._lint_messages("vb")
        self.assertTrue(any(message.startswith(self.WARNING) for message in messages))

    def test_no_warning_when_verb_pos_has_stem(self) -> None:
        messages = self._lint_messages("vb G")
        self.assertFalse(any(message.startswith(self.WARNING) for message in messages))

    def test_vb_stem_pos_is_accepted_by_dulat_pos_validation(self) -> None:
        messages = self._lint_messages("vb G")
        self.assertFalse(any(message.startswith(self.POS_ERROR) for message in messages))

    def test_vb_stem_alternation_is_accepted_by_dulat_pos_validation(self) -> None:
        messages = self._lint_messages("vb G/D")
        self.assertFalse(any(message.startswith(self.POS_ERROR) for message in messages))


if __name__ == "__main__":
    unittest.main()
