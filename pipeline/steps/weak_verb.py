"""Fix weak-initial verb forms missing !...! preformative markers.

When a verb root starts with /y-.../ and the surface has a prefix preformative
(t, y, a, n, i), the analysis must wrap that prefix in !...! markers.
"""

import re

from pipeline.steps.base import RefinementStep, TabletRow

# Preformative consonants for prefix conjugation
_PREFORMATIVES = {"t", "y", "a", "n", "i"}

# Root pattern like /y-d-y/ or /ʔ-b-d/
_ROOT_RE = re.compile(r"^/([A-Za-zˤʔḫṣṯẓġḏḥṭš])-")


class WeakVerbFixer(RefinementStep):
    """Add !...! preformative markers for weak-initial verb prefix forms."""

    @property
    def name(self) -> str:
        return "weak-verb"

    def refine_row(self, row: TabletRow) -> TabletRow:
        surface = row.surface.strip()
        analysis = row.analysis.strip()
        dulat = row.dulat.strip()
        pos = row.pos.strip()

        if not surface or not analysis or not dulat or not pos:
            return row

        # Only verbs
        if "vb" not in pos:
            return row

        # Already has !...! markers
        if "!" in analysis:
            return row

        # Must be a verb form (has '[' ending)
        if "[" not in analysis:
            return row

        # Check DULAT for root pattern /C-C-C/
        roots = [v.strip() for v in dulat.split(";")]
        pos_variants = [v.strip() for v in pos.split(";")]

        variants = analysis.split(";")
        changed = False
        out = []

        for idx, var in enumerate(variants):
            var = var.strip()
            d_var = roots[idx].strip() if idx < len(roots) else ""
            p_var = pos_variants[idx].strip() if idx < len(pos_variants) else ""

            new_var = self._fix_variant(var, d_var, p_var, surface)
            if new_var != var:
                changed = True
            out.append(new_var)

        if not changed:
            return row

        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis=";".join(out),
            dulat=row.dulat,
            pos=row.pos,
            gloss=row.gloss,
            comment=row.comment,
        )

    def _fix_variant(self, var: str, dulat_var: str, pos_var: str, surface: str) -> str:
        """Fix one analysis variant if it's a weak-initial verb missing preformative."""
        if "vb" not in pos_var:
            return var
        if "[" not in var:
            return var
        if "!" in var:
            return var

        # Check if DULAT variant is a root
        m = _ROOT_RE.match(dulat_var)
        if not m:
            return var

        # Surface must start with a preformative
        if not surface or surface[0] not in _PREFORMATIVES:
            return var

        prefix = surface[0]

        # Check analysis starts with the same preformative letter
        if not var.startswith(prefix):
            return var

        # Wrap the prefix letter in !...!
        return "!" + prefix + "!" + var[1:]
