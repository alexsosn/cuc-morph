"""Fix plural nouns missing explicit split endings (/m, /t=)."""

import re
from typing import Optional

from pipeline.steps.base import RefinementStep, TabletRow
from pipeline.steps.dulat_gate import DulatMorphGate

# Match a noun ending with the plural -m or -t directly before the '/' closure.
# e.g. nhrm/ → nhr/m or nhrt/ → nhr/t=
_PLURAL_M_RE = re.compile(r"^([A-Za-zˤʔḫṣṯẓġḏḥṭš()\[\]!&~:]+?)m(\([IVX]+\))?/$")
_PLURAL_T_RE = re.compile(r"^([A-Za-zˤʔḫṣṯẓġḏḥṭš()\[\]!&~:]+?)t(\([IVX]+\))?/$")


class PluralSplitFixer(RefinementStep):
    """Rewrite plural noun analyses to use explicit split endings: X/m or X/t=."""

    def __init__(self, gate: Optional[DulatMorphGate] = None) -> None:
        self._gate = gate

    @property
    def name(self) -> str:
        return "plural-split"

    def refine_row(self, row: TabletRow) -> TabletRow:
        pos = row.pos.strip()
        if not pos:
            return row

        analysis = row.analysis
        if not analysis:
            return row

        variants = analysis.split(";")
        pos_variants = [v.strip() for v in pos.split(";")]
        dulat_variants = [v.strip() for v in row.dulat.split(";")]
        changed = False
        out_variants = []

        for idx, var in enumerate(variants):
            var = var.strip()
            pos_v = pos_variants[idx].strip() if idx < len(pos_variants) else ""
            dulat_tok = dulat_variants[idx].strip() if idx < len(dulat_variants) else ""
            new_var = self._fix_variant(var, pos_v, dulat_tok, row.surface)
            if new_var != var:
                changed = True
            out_variants.append(new_var)

        if not changed:
            return row

        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis=";".join(out_variants),
            dulat=row.dulat,
            pos=row.pos,
            gloss=row.gloss,
            comment=row.comment,
        )

    def _fix_variant(self, var: str, pos_v: str, dulat_tok: str, surface: str) -> str:
        """Fix a single analysis variant if it needs plural split."""
        # Only fix noun-like slots
        first_slot = pos_v.split(",")[0].strip() if pos_v else ""
        if not first_slot.startswith("n."):
            return var

        # Require DULAT evidence that the token has plural morphology.
        if not self._is_plural_dulat_token(dulat_tok, surface):
            return var

        # Already has explicit split (contains /m or /t=)?
        if re.search(r"/[mt]", var):
            return var

        # Try masculine plural: Xm/ → X/m
        m = _PLURAL_M_RE.match(var)
        if m:
            base = m.group(1)
            hom = m.group(2) or ""
            return f"{base}{hom}/m"

        # Try feminine plural: Xt/ → X/t=
        m = _PLURAL_T_RE.match(var)
        if m:
            base = m.group(1)
            hom = m.group(2) or ""
            return f"{base}{hom}/t="

        return var

    def _is_plural_dulat_token(self, token: str, surface: str) -> bool:
        if not token or token == "?":
            return False
        if self._gate is None:
            return False
        return self._gate.is_plural_token(token, surface=surface)
