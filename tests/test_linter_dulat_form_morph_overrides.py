"""Tests for form-morph overrides applied during DULAT loading in linter."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from linter.lint import load_dulat, normalize_surface


class LinterDulatFormMorphOverridesTest(unittest.TestCase):
    def test_overrides_il_construct_morphology_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "dulat.sqlite"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE entries(
                    entry_id INTEGER PRIMARY KEY,
                    lemma TEXT,
                    homonym TEXT,
                    pos TEXT,
                    data TEXT
                )
                """
            )
            cur.execute("CREATE TABLE translations(entry_id INTEGER, text TEXT)")
            cur.execute("CREATE TABLE forms(text TEXT, morphology TEXT, entry_id INTEGER)")
            cur.execute(
                "INSERT INTO entries(entry_id, lemma, homonym, pos, data) "
                "VALUES (264, 'ỉl', 'I', 'n.', '{}')"
            )
            cur.execute("INSERT INTO translations(entry_id, text) VALUES (264, 'god')")
            cur.executemany(
                "INSERT INTO forms(text, morphology, entry_id) VALUES (?, ?, 264)",
                [
                    ("ỉl", "sg."),
                    ("ỉl", "du., cstr."),
                    ("ỉly", "du., cstr."),
                ],
            )
            conn.commit()
            conn.close()

            forms_map, _entry_meta, _lemma_map, _entry_stems, _entry_gender = load_dulat(db_path)
            il_rows = forms_map[normalize_surface("ỉl")]
            ily_rows = forms_map[normalize_surface("ỉly")]

            self.assertIn("sg., cstr.", {row.morph for row in il_rows})
            self.assertNotIn("du., cstr.", {row.morph for row in il_rows})
            self.assertEqual({row.morph for row in ily_rows}, {"pl., cstr."})


if __name__ == "__main__":
    unittest.main()
