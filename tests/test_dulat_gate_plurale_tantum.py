"""Tests for DULAT plurale-tantum gate classification."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pipeline.steps.dulat_gate import DulatMorphGate


class DulatGatePluraleTantumTest(unittest.TestCase):
    def _build_gate(self) -> DulatMorphGate:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "dulat.sqlite"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE entries (
                    entry_id INTEGER PRIMARY KEY,
                    lemma TEXT,
                    homonym TEXT,
                    pos TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE forms (
                    entry_id INTEGER,
                    text TEXT,
                    morphology TEXT
                )
                """
            )

            cur.executemany(
                "INSERT INTO entries(entry_id, lemma, homonym, pos) VALUES (?, ?, ?, ?)",
                [
                    (1, "pnm", "", "n."),
                    (2, "šlm", "II", "n."),
                    (3, "qm", "", "n."),
                ],
            )
            cur.executemany(
                "INSERT INTO forms(entry_id, text, morphology) VALUES (?, ?, ?)",
                [
                    (1, "pn", "pl., cstr."),
                    (1, "pnm", "pl."),
                    (1, "pnh", "suff."),
                    (2, "šlmm", "pl."),
                    (2, "šlmm", "sg., suff."),
                    (2, "-m", "sg., suff."),
                    (3, "qm", "pl., cstr."),
                ],
            )
            conn.commit()
            conn.close()

            gate = DulatMorphGate(db_path)
        return gate

    def test_ignores_explicit_singular_suffix_evidence_for_plurale_tantum(self) -> None:
        gate = self._build_gate()
        self.assertTrue(gate.is_plurale_tantum_noun_token("pnm"))
        self.assertFalse(gate.is_plurale_tantum_noun_token("šlm (II)"))
        self.assertFalse(gate.is_plurale_tantum_noun_token("qm"))


if __name__ == "__main__":
    unittest.main()
