"""Unit tests for pipeline refinement steps (unittest-discover compatible)."""

import tempfile
import textwrap
import unittest
from pathlib import Path

from pipeline.dulat_attestation_index import DulatAttestationIndex
from pipeline.steps.aleph_prefix import AlephPrefixFixer
from pipeline.steps.attestation_sort import AttestationSortFixer
from pipeline.steps.baal_labourer_ktu1 import BaalLabourerKtu1Fixer
from pipeline.steps.baal_plural import BaalPluralGodListFixer
from pipeline.steps.base import (
    TabletRow,
    is_separator_line,
    is_unresolved,
    normalize_separator_row,
    parse_tsv_line,
)
from pipeline.steps.noun_closure import NounPosClosureFixer
from pipeline.steps.offering_l_prep import OfferingListLPrepFixer
from pipeline.steps.plural_split import PluralSplitFixer
from pipeline.steps.schema_formatter import TsvSchemaFormatter
from pipeline.steps.suffix_fixer import SuffixCliticFixer
from pipeline.steps.weak_final_sc import WeakFinalSuffixConjugationFixer
from pipeline.steps.weak_verb import WeakVerbFixer


class StaticGate:
    """Small test double for DULAT feature-gating behavior."""

    def __init__(self, plural_tokens=None, suffix_tokens=None) -> None:
        self._plural = set(plural_tokens or [])
        self._suffix = set(suffix_tokens or [])

    def is_plural_token(self, token: str, surface: str = "") -> bool:
        return token in self._plural

    def has_suffix_token(self, token: str, surface: str = "") -> bool:
        return token in self._suffix


class ParseTsvLineTest(unittest.TestCase):
    def test_data_row(self) -> None:
        row = parse_tsv_line("12345\tum\tum/\tủm\tn. f.\tmother")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.line_id, "12345")
        self.assertEqual(row.surface, "um")
        self.assertEqual(row.analysis, "um/")
        self.assertEqual(row.dulat, "ủm")
        self.assertEqual(row.pos, "n. f.")
        self.assertEqual(row.gloss, "mother")
        self.assertEqual(row.comment, "")

    def test_data_row_with_comment(self) -> None:
        row = parse_tsv_line("12345\tum\t?\t?\t?\t?\tDULAT: NOT FOUND")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.comment, "DULAT: NOT FOUND")

    def test_separator_returns_none(self) -> None:
        self.assertIsNone(parse_tsv_line("#---- KTU 1.100 1"))

    def test_empty_line_returns_none(self) -> None:
        self.assertIsNone(parse_tsv_line(""))


class BaseHelpersTest(unittest.TestCase):
    def test_is_separator_line(self) -> None:
        self.assertTrue(is_separator_line("#---- KTU 1.100 1"))
        self.assertFalse(is_separator_line("12345\tum\tum/"))

    def test_is_unresolved(self) -> None:
        unresolved = TabletRow("1", "x", "?", "?", "?", "?", "DULAT: NOT FOUND")
        resolved = TabletRow("1", "um", "um/", "ủm", "n. f.", "mother", "")
        self.assertTrue(is_unresolved(unresolved))
        self.assertFalse(is_unresolved(resolved))

    def test_tablet_row_to_tsv(self) -> None:
        row = TabletRow("1", "um", "um/", "ủm", "n. f.", "mother", "")
        self.assertEqual(row.to_tsv(), "1\tum\tum/\tủm\tn. f.\tmother\t")
        row_with_comment = TabletRow("1", "x", "?", "?", "?", "?", "DULAT: NOT FOUND")
        self.assertEqual(
            row_with_comment.to_tsv(),
            "1\tx\t?\t?\t?\t?\tDULAT: NOT FOUND",
        )

    def test_normalize_separator_row_preserves_tab_shape(self) -> None:
        self.assertEqual(
            normalize_separator_row("#---------------------------- KTU 1.5 I:4\t\t\t\t\t\t"),
            "# KTU 1.5 I:4\t\t\t\t\t\t",
        )
        self.assertEqual(
            normalize_separator_row("#---------------------------- KTU 1.5 I:4"),
            "# KTU 1.5 I:4",
        )


class AlephPrefixFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = AlephPrefixFixer()

    def test_bare_aleph_gets_prefix(self) -> None:
        row = TabletRow("1", "ảb", "ʔb/", "ʔb", "n. m.", "father", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "(ʔb/")

    def test_already_prefixed_unchanged(self) -> None:
        row = TabletRow("1", "ảb", "(ʔb/", "ʔb", "n. m.", "father", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "(ʔb/")

    def test_root_notation_skipped(self) -> None:
        row = TabletRow("1", "abd", "/ʔ-b-d/", "/ʔ-b-d/", "vb", "be missing", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "/ʔ-b-d/")


class NounPosClosureFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = NounPosClosureFixer()

    def test_noun_without_slash_gets_slash(self) -> None:
        row = TabletRow("1", "bn", "bn", "bn (I)", "n. m.", "son", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "bn/")

    def test_verb_unchanged(self) -> None:
        row = TabletRow("1", "yṯb", "yṯb[", "/y-ṯ-b/", "vb", "to sit", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "yṯb[")

    def test_multi_variant_partial_fix(self) -> None:
        row = TabletRow(
            "1",
            "mlk",
            "mlk;mlk(II)/",
            "/m-l-k/;mlk (II)",
            "vb;n. m.",
            "to reign;kingdom",
            "",
        )
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "mlk;mlk(II)/")


class PluralSplitFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = PluralSplitFixer(gate=StaticGate(plural_tokens={"nhr (I)"}))

    def test_masc_plural_m_split(self) -> None:
        row = TabletRow("1", "nhrm", "nhrm/", "nhr (I)", "n. m.", "river", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "nhr/m")

    def test_masc_plural_with_homonym(self) -> None:
        row = TabletRow("1", "nhrm", "nhrm(I)/", "nhr (I)", "n. m.", "river", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "nhr(I)/m")

    def test_non_noun_unchanged(self) -> None:
        row = TabletRow("1", "yṯbm", "yṯbm[", "/y-ṯ-b/", "vb", "to sit", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "yṯbm[")

    def test_singular_lexeme_ending_with_m_is_unchanged(self) -> None:
        row = TabletRow("1", "um", "um/", "ủm", "n. f.", "mother", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "um/")

    def test_lemma_style_plural_surface_m_gets_split(self) -> None:
        fixer = PluralSplitFixer(gate=StaticGate(plural_tokens={"ỉl (I)"}))
        row = TabletRow("1", "ilm", "il(I)/", "ỉl (I)", "n. m.", "god", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "il(I)/m")

    def test_lemma_style_plural_surface_t_gets_split(self) -> None:
        fixer = PluralSplitFixer(gate=StaticGate(plural_tokens={"kṯr (I)"}))
        row = TabletRow("1", "kṯrt", "kṯr(I)/", "kṯr (I)", "n. f.", "Kothar", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "kṯr(I)/t=")

    def test_singular_t_form_not_forced_to_plural(self) -> None:
        fixer = PluralSplitFixer(gate=StaticGate(plural_tokens={"dqt (I)"}))
        row = TabletRow("1", "dqt", "dqt(I)/", "dqt (I)", "n. f.", "small", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "dqt(I)/")


class SuffixCliticFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"npš"}))

    def test_suffix_h_injected(self) -> None:
        row = TabletRow("1", "npšh", "npšh/", "npš", "n. f.", "throat", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "npš/+h")

    def test_already_has_plus_unchanged(self) -> None:
        row = TabletRow("1", "npšh", "npš/+h", "npš", "n. f.", "throat", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "npš/+h")

    def test_verb_not_changed(self) -> None:
        row = TabletRow("1", "yblh", "yblh[", "/y-b-l/", "vb", "to carry", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "yblh[")

    def test_false_suffix_candidate_without_dulat_support_unchanged(self) -> None:
        row = TabletRow("1", "abn", "abn/", "ảbn", "n. f.", "stone", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "abn/")

    def test_adds_suffix_to_lemma_style_prep(self) -> None:
        fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"l (I)"}))
        row = TabletRow("1", "lnh", "l(I)", "l (I)", "prep.", "to", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "l(I)+h")

    def test_adds_suffix_to_homonym_noun_with_slash(self) -> None:
        fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"šmm (I)"}))
        row = TabletRow("1", "šmmh", "šmm(I)/", "šmm (I)", "n. m.", "heavens", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "šmm(I)/+h")

    def test_adds_suffix_when_reconstruction_matches_surface_base(self) -> None:
        fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"l (I)"}))
        row = TabletRow("1", "ln", "l(I)", "l (I)", "prep.", "to", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "l(I)+n")

    def test_no_suffix_injection_when_reconstruction_does_not_match(self) -> None:
        fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"l (I)"}))
        row = TabletRow("1", "lhn", "hmlk/", "l (I)", "prep.", "to", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "hmlk/")

    def test_reverts_enclitic_plus_pattern(self) -> None:
        fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"bʕd"}))
        row = TabletRow("1", "bˤdn", "bˤd~+n", "bʕd", "adv., prep.", "behind", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "bˤd~n")

    def test_reverts_lexeme_final_n_split(self) -> None:
        fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"mṯn"}))
        row = TabletRow("1", "mṯn", "mṯ/+n", "mṯn", "n. m.", "repetition", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "mṯn/")

    def test_reverts_lexeme_final_n_split_for_lshan(self) -> None:
        fixer = SuffixCliticFixer(gate=StaticGate(suffix_tokens={"lšn"}))
        row = TabletRow("1", "lšn", "lš/+n", "lšn", "n. f.", "tongue", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.analysis, "lšn/")


class WeakVerbFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = WeakVerbFixer()

    def test_prefix_y_wrapped_and_hidden_y_reconstructed(self) -> None:
        row = TabletRow("1", "yṯb", "yṯb[", "/y-ṯ-b/", "vb", "to sit down", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "!y!(yṯb[")

    def test_existing_preformative_adds_hidden_initial_y(self) -> None:
        row = TabletRow("1", "yṯb", "!y!ṯb[", "/y-ṯ-b/", "vb", "to sit down", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "!y!(yṯb[")

    def test_existing_surface_y_after_preformative_becomes_hidden_y(self) -> None:
        row = TabletRow("1", "ybl", "!y!ybl[", "/y-b-l/", "vb", "to carry", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "!y!(ybl[")

    def test_t_preformative_variant_gets_hidden_initial_y(self) -> None:
        row = TabletRow("1", "ttn", "!t!tn[", "/y-t-n/", "vb", "to give", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "!t!(ytn[")

    def test_non_weak_initial_verb_unchanged(self) -> None:
        row = TabletRow("1", "tqru", "tqrʔ[", "/q-r-ʔ/", "vb", "to call", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "tqrʔ[")

    def test_non_verb_unchanged(self) -> None:
        row = TabletRow("1", "yd", "yd/", "yd (I)", "n. f.", "hand", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "yd/")


class WeakFinalSuffixConjugationFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = WeakFinalSuffixConjugationFixer()

    def test_weak_final_y_gets_sc_t_marker(self) -> None:
        row = TabletRow("1", "dit", "dʔy[", "/d-ʔ-y/", "vb", "to fly", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "dʔy[t")

    def test_weak_final_w_gets_sc_t_marker(self) -> None:
        row = TabletRow("1", "šnwt", "šnw[", "/š-n-w/", "vb", "to change", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "šnw[t")

    def test_prefixed_form_unchanged(self) -> None:
        row = TabletRow("1", "tkly", "!t!kly[", "/k-l-y/", "vb", "to finish", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "!t!kly[")

    def test_middle_radical_t_unchanged(self) -> None:
        row = TabletRow("1", "ytt", "ytn[", "/y-t-n/", "vb", "to give", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "ytn[")

    def test_already_marked_unchanged(self) -> None:
        row = TabletRow("1", "dit", "dʔy[t", "/d-ʔ-y/", "vb", "to fly", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "dʔy[t")

    def test_non_verb_variant_unchanged(self) -> None:
        row = TabletRow("1", "klt", "kl(I)/t=", "klt (I)", "n. f.", "bride", "")
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "kl(I)/t=")


class BaalPluralGodListFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = BaalPluralGodListFixer()

    def test_collapses_mixed_baal_ambiguity(self) -> None:
        row = TabletRow(
            "149082",
            "bˤlm",
            "bˤl(II)/;bˤl(I)/m",
            "bʕl (II);bʕl (I)",
            "n. m./DN;n. m.",
            "Baʿlu;labourer",
            "",
        )
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "bˤl(II)/m")
        self.assertEqual(result.dulat, "bʕl (II)")
        self.assertEqual(result.pos, "n. m.")
        self.assertEqual(result.gloss, "lord")

    def test_unrelated_baal_entry_unchanged(self) -> None:
        row = TabletRow(
            "1",
            "bˤl",
            "bˤl(II)/",
            "bʕl (II)",
            "n. m./DN",
            "Baʿlu",
            "",
        )
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "bˤl(II)/")


class BaalLabourerKtu1FixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = BaalLabourerKtu1Fixer()

    def test_removes_labourer_variant_in_ktu1(self) -> None:
        content = (
            "#---- KTU 1.105 25\n"
            "152715\tbˤl\tbˤl(II)/;bˤl(I)/;bˤl[\t"
            "bʕl (II);bʕl (I);/b-ʕ-l/\tn. m./DN;n. m.;vb\t"
            "Baʿlu;labourer;to make\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "KTU 1.105.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 1)
            line = f.read_text(encoding="utf-8").splitlines()[1]
            self.assertEqual(
                line,
                "152715\tbˤl\tbˤl(II)/;bˤl[\tbʕl (II);/b-ʕ-l/\tn. m./DN;vb\tBaʿlu;to make\t",
            )

    def test_keeps_variant_outside_ktu1(self) -> None:
        content = (
            "#---- KTU 4.1 1\n"
            "900001\tbˤl\tbˤl(II)/;bˤl(I)/;bˤl[\t"
            "bʕl (II);bʕl (I);/b-ʕ-l/\tn. m./DN;n. m.;vb\t"
            "Baʿlu;labourer;to make\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "KTU 4.1.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 1)
            line = f.read_text(encoding="utf-8").splitlines()[1]
            self.assertEqual(
                line,
                "900001\tbˤl\tbˤl(II)/;bˤl(I)/;bˤl[\t"
                "bʕl (II);bʕl (I);/b-ʕ-l/\tn. m./DN;n. m.;vb\t"
                "Baʿlu;labourer;to make\t",
            )


class OfferingListLPrepFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = OfferingListLPrepFixer()

    def test_collapses_ambiguous_l_in_offering_sequence(self) -> None:
        content = textwrap.dedent(
            """\
            #---- KTU 1.119 1
            154176\tgdlt\tgdl(I)/t=\tgdlt (I)\tn. f.\thead of cattle
            154177\tl\tl(I);l(II);l(III)\tl (I);l (II);l (III)\tprep.;adv.;functor\tto;no;certainly
            154178\tbˤlm\tbˤl(II)/m\tbʕl (II)\tn. m.\tlord
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 3)
            lines = f.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[2], "154177\tl\tl(I)\tl (I)\tprep.\tto\t")

    def test_non_offering_context_unchanged(self) -> None:
        content = textwrap.dedent(
            """\
            #---- KTU 1.1 1
            135588\tḥẓr\tḥẓr/\tḥẓr\tn. m.\tmansion
            135589\tl\tl(I);l(II);l(III)\tl (I);l (II);l (III)\tprep.;adv.;functor\tto;no;certainly
            135590\tpˤn\tpˤn/\tpʕn\tn. f.\tfoot
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 3)


class AttestationSortFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = DulatAttestationIndex(
            counts_by_key={
                ("bʕl", "II"): 200,
                ("ʕbd", ""): 20,
                ("il", "I"): 600,
                ("mlk", ""): 120,
            },
            max_count_by_lemma={
                "bʕl": 200,
                "ʕbd": 20,
                "il": 600,
                "mlk": 120,
            },
        )
        self.fixer = AttestationSortFixer(index=self.index)

    def test_reorders_aligned_variants_by_attestation_count(self) -> None:
        row = TabletRow(
            line_id="1",
            surface="x",
            analysis="a1;a2;a3",
            dulat="ʕbd;bʕl (II);ỉl (I)",
            pos="p1;p2;p3",
            gloss="g1;g2;g3",
            comment="free comment",
        )
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "a3;a2;a1")
        self.assertEqual(result.dulat, "ỉl (I);bʕl (II);ʕbd")
        self.assertEqual(result.pos, "p3;p2;p1")
        self.assertEqual(result.gloss, "g3;g2;g1")
        self.assertEqual(result.comment, "free comment")

    def test_uses_first_dulat_entry_before_comma_for_ranking(self) -> None:
        row = TabletRow(
            line_id="2",
            surface="x",
            analysis="a1;a2",
            dulat="mlk, -m (I);ʕbd, -k (I)",
            pos="p1;p2",
            gloss="g1;g2",
            comment="c1;c2",
        )
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "a1;a2")
        self.assertEqual(result.comment, "c1;c2")

    def test_reorders_comment_when_comment_variants_are_aligned(self) -> None:
        row = TabletRow(
            line_id="3",
            surface="x",
            analysis="a1;a2",
            dulat="ʕbd;bʕl (II)",
            pos="p1;p2",
            gloss="g1;g2",
            comment="c1;c2",
        )
        result = self.fixer.refine_row(row)
        self.assertEqual(result.analysis, "a2;a1")
        self.assertEqual(result.comment, "c2;c1")


class TsvSchemaFormatterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixer = TsvSchemaFormatter()
        self.header = "id\tsurface form\tmorphological parsing\tDULAT\tPOS\tgloss\tcomments"
        self.separator = "# KTU 1.5 I:4\t\t\t\t\t\t"

    def test_normalizes_separator_and_expands_to_7_columns(self) -> None:
        content = textwrap.dedent(
            """\
            #---------------------------- KTU 1.5 I:4
            100\tabc\tabc/\tabc\tn. m.\tthing
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 3)
            lines = f.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], self.header)
            self.assertEqual(lines[1], self.separator)
            self.assertEqual(lines[2], "100\tabc\tabc/\tabc\tn. m.\tthing\t")

    def test_merges_extra_columns_into_comment(self) -> None:
        content = textwrap.dedent(
            """\
            # KTU 1.5 I:4
            101\tabc\tabc/\tabc\tn. m.\tthing\tc1\tc2
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 3)
            lines = f.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], self.header)
            self.assertEqual(lines[1], self.separator)
            self.assertEqual(lines[2], "101\tabc\tabc/\tabc\tn. m.\tthing\tc1 c2")

    def test_escapes_quotes_in_data_columns(self) -> None:
        content = textwrap.dedent(
            """\
            # KTU 1.5 I:4
            102\tabc\tabc/\tabc\tn. m.\tthing\tUNP: "quoted"
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 3)
            lines = f.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[1], self.separator)
            self.assertEqual(lines[2], '102\tabc\tabc/\tabc\tn. m.\tthing\t"UNP: ""quoted"""')

    def test_preserves_existing_header_without_change(self) -> None:
        content = textwrap.dedent(
            """\
            id\tsurface form\tmorphological parsing\tDULAT\tPOS\tgloss\tcomments
            # KTU 1.5 I:4\t\t\t\t\t\t
            103\tabc\tabc/\tabc\tn. m.\tthing\t
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")
            result = self.fixer.refine_file(f)
            self.assertEqual(result.rows_changed, 0)
            lines = f.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], self.header)
            self.assertEqual(lines[1], self.separator)


class RefineFileIntegrationTest(unittest.TestCase):
    def test_refine_file_preserves_structure(self) -> None:
        content = textwrap.dedent(
            """\
            #---- KTU 1.100 1
            12345\tum\tum/\tủm\tn. f.\tmother
            12346\tx\t?\t?\t?\t?\tDULAT: NOT FOUND
            #---- KTU 1.100 2
            12347\tbn\tbn\tbn (I)\tn. m.\tson
        """
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")

            fixer = NounPosClosureFixer()
            result = fixer.refine_file(f)

            self.assertEqual(result.rows_processed, 3)
            self.assertEqual(result.rows_changed, 2)

            lines = f.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "# KTU 1.100 1")
            self.assertTrue(lines[2].startswith("12346\tx\t?"))
            self.assertIn("bn/", lines[4])

    def test_refine_file_idempotent(self) -> None:
        content = textwrap.dedent(
            """\
            #---- KTU 1.100 1
            12345\tum\tum/\tủm\tn. f.\tmother
        """
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "test.tsv"
            f.write_text(content, encoding="utf-8")

            fixer = NounPosClosureFixer()
            r1 = fixer.refine_file(f)
            r2 = fixer.refine_file(f)

            self.assertEqual(r1.rows_changed, 1)
            self.assertEqual(r2.rows_changed, 0)


if __name__ == "__main__":
    unittest.main()
