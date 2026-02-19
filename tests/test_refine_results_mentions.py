"""Tests for slash-variant handling in refine_results_mentions helpers."""

import unittest

from scripts.refine_results_mentions import Entry, analysis_for_entry, entry_label


class RefineResultsMentionsTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
