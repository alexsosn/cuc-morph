"""Tests for form-aware nominal POS refinements (gender/dual)."""

import unittest

from pipeline.steps.base import TabletRow
from pipeline.steps.nominal_form_morph_pos import NominalFormMorphPosFixer


class _MorphGate:
    def __init__(self, mapping=None) -> None:
        self.mapping = dict(mapping or {})

    def surface_morphologies(self, token: str, surface: str) -> set[str]:
        return set(self.mapping.get((token, surface), set()))


class NominalFormMorphPosFixerTest(unittest.TestCase):
    def test_promotes_masculine_pos_to_feminine_for_feminine_surface_form(self) -> None:
        gate = _MorphGate({("pḥl", "pḥlt"): {"f."}})
        fixer = NominalFormMorphPosFixer(gate=gate)
        row = TabletRow("1", "pḥlt", "pḥl/t", "pḥl", "n. m.", "ass", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.pos, "n. f.")

    def test_appends_dual_marker_when_surface_form_is_dual(self) -> None:
        gate = _MorphGate({("š", "šm"): {"du."}})
        fixer = NominalFormMorphPosFixer(gate=gate)
        row = TabletRow("2", "šm", "š/m", "š", "n. m.", "ram", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.pos, "n. m. du.")

    def test_non_nominal_pos_unchanged(self) -> None:
        gate = _MorphGate({("hl", "hlm"): {"sg."}})
        fixer = NominalFormMorphPosFixer(gate=gate)
        row = TabletRow("3", "hlm", "hl~m", "hl", "deictic adv. functor", "behold", "")
        result = fixer.refine_row(row)
        self.assertEqual(result.pos, "deictic adv. functor")


if __name__ == "__main__":
    unittest.main()
