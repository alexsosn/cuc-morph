"""Tests for slash-variant handling in refine_results_mentions helpers."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.refine_results_mentions import (
    Entry,
    analysis_for_entry,
    build_variants,
    entry_label,
    load_entries,
    parse_separator_ref,
    refine_file,
)


class RefineResultsMentionsTest(unittest.TestCase):
    def _init_dulat_schema(self, db_path: Path) -> None:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE entries ("
            "entry_id INTEGER PRIMARY KEY, "
            "lemma TEXT, homonym TEXT, pos TEXT, wiki_transcription TEXT)"
        )
        cur.execute(
            "CREATE TABLE senses (id INTEGER PRIMARY KEY, entry_id INTEGER, definition TEXT)"
        )
        cur.execute("CREATE TABLE translations (entry_id INTEGER, text TEXT)")
        cur.execute("CREATE TABLE forms (text TEXT, entry_id INTEGER, morphology TEXT)")
        conn.commit()
        conn.close()

    def test_entry_label_preserves_short_prefix_slash_lemma(self) -> None:
        entry = Entry(
            entry_id=665,
            lemma="ỉ/ủšḫry",
            hom="",
            pos="DN",
            gloss="",
            wiki_tr="",
        )
        self.assertEqual(entry_label(entry), "ỉ/ủšḫry")

    def test_analysis_prefers_surface_for_short_prefix_slash_lemma(self) -> None:
        entry = Entry(
            entry_id=665,
            lemma="ỉ/ủšḫry",
            hom="",
            pos="DN",
            gloss="",
            wiki_tr="",
        )
        self.assertEqual(analysis_for_entry("ušḫry", entry), "ušḫry/")
        self.assertEqual(analysis_for_entry("išḫry", entry), "išḫry/")

    def test_analysis_keeps_trailing_prefixed_verb_tail(self) -> None:
        entry = Entry(
            entry_id=2520,
            lemma="/l-s-m/",
            hom="",
            pos="vb",
            gloss="",
            wiki_tr="",
        )
        self.assertEqual(analysis_for_entry("tlsmn", entry), "!t!lsm[n")

    def test_load_entries_falls_back_to_lemma_when_forms_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "dulat.sqlite"
            self._init_dulat_schema(db_path)
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO entries(entry_id, lemma, homonym, pos, wiki_transcription) "
                "VALUES (?, ?, ?, ?, ?)",
                (170, "ủgrt", "", "TN", ""),
            )
            cur.execute(
                "INSERT INTO senses(id, entry_id, definition) VALUES (?, ?, ?)",
                (1, 170, "Ugarit"),
            )
            conn.commit()
            conn.close()

            _entries_by_id, forms_map, _lemma_map, suffix_map, forms_morph = load_entries(db_path)
            self.assertIn("ugrt", forms_map)
            self.assertEqual([entry.entry_id for entry in forms_map["ugrt"]], [170])

            variants = build_variants(
                surface="ugrt",
                current_ref="CAT 1.119 I:1",
                forms_map=forms_map,
                suffix_map=suffix_map,
                forms_morph=forms_morph,
                mention_ids=set(),
                entry_ref_count={},
                entry_tablets={},
                entry_family_count={},
                max_variants=3,
            )
            self.assertTrue(variants)
            self.assertEqual(variants[0].entries[0].entry_id, 170)

    def test_parse_separator_ref_supports_no_column_format(self) -> None:
        self.assertEqual(
            parse_separator_ref("#---------------------------- KTU 1.101 5"),
            "CAT 1.101:5",
        )
        self.assertEqual(
            parse_separator_ref("#---------------------------- KTU 1.3 I:23"),
            "CAT 1.3 I:23",
        )

    def test_refine_file_uses_reverse_mentions_with_no_column_separator(self) -> None:
        dn_entry = Entry(
            entry_id=1,
            lemma="ṭly",
            hom="",
            pos="DN",
            gloss="Tallay",
            wiki_tr="",
        )
        noun_entry = Entry(
            entry_id=2,
            lemma="ṭl",
            hom="",
            pos="n. m.",
            gloss="dew",
            wiki_tr="",
        )
        forms_map = {"ṭly": [noun_entry, dn_entry]}
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "KTU 1.101.tsv"
            out_path.write_text(
                ("#---------------------------- KTU 1.101 5\n1\tṭly\t?\t?\t?\t?\t\n"),
                encoding="utf-8",
            )
            rows, changed = refine_file(
                path=out_path,
                out_path=out_path,
                forms_map=forms_map,
                suffix_map={},
                forms_morph={},
                reverse_mentions={"CAT 1.101:5": {1}},
                entry_ref_count={},
                entry_tablets={},
                entry_family_count={},
            )
            self.assertEqual(rows, 1)
            self.assertEqual(changed, 1)
            lines = out_path.read_text(encoding="utf-8").splitlines()
            self.assertIn("\tṭly/\tṭly\tDN\tTallay\t", lines[1])

    def test_load_entries_applies_form_text_alias_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "dulat.sqlite"
            self._init_dulat_schema(db_path)
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO entries(entry_id, lemma, homonym, pos, wiki_transcription) "
                "VALUES (?, ?, ?, ?, ?)",
                (2520, "/l-s-m/", "", "vb", ""),
            )
            cur.execute(
                "INSERT INTO forms(text, entry_id, morphology) VALUES (?, ?, ?)",
                ("tslmn", 2520, "G, prefc."),
            )
            conn.commit()
            conn.close()

            _entries, forms_map, _lemma_map, _suffix_map, forms_morph = load_entries(db_path)
            self.assertIn("tlsmn", forms_map)
            self.assertEqual([entry.entry_id for entry in forms_map["tlsmn"]], [2520])
            self.assertIn(("tlsmn", 2520), forms_morph)


if __name__ == "__main__":
    unittest.main()
