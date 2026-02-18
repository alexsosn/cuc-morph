"""Fix suffix/clitic forms missing the '+' separator in analysis column.

When DULAT morphology indicates a pronominal suffix and the surface form ends
with a known suffix segment (h, k, km, kn, n, ny, hm, hn, y), inject '+' before
the suffix in the analysis.
"""

import re
from typing import Optional

from pipeline.steps.base import RefinementStep, TabletRow
from pipeline.steps.dulat_gate import DulatMorphGate

# Ordered from longest to shortest so greedy match captures full suffix
_SUFFIX_SEGMENTS = ("hm", "hn", "km", "kn", "ny", "nm", "nn", "h", "k", "n", "y")

# POS patterns that commonly carry suffixes
_SUFFIXABLE_POS_PREFIXES = {"n.", "adj.", "prep.", "adv."}


class SuffixCliticFixer(RefinementStep):
    """Inject '+' separator before pronominal suffix segments in analysis."""

    def __init__(self, gate: Optional[DulatMorphGate] = None) -> None:
        self._gate = gate

    @property
    def name(self) -> str:
        return "suffix-clitic"

    def refine_row(self, row: TabletRow) -> TabletRow:
        surface = row.surface.strip()
        analysis = row.analysis.strip()
        pos = row.pos.strip()
        if not surface or not analysis or not pos:
            return row

        # Check if surface ends with a known suffix segment
        matched_suffix = None
        for seg in _SUFFIX_SEGMENTS:
            if surface.endswith(seg) and len(surface) > len(seg):
                matched_suffix = seg
                break

        if not matched_suffix:
            return row

        variants = analysis.split(";")
        pos_variants = [v.strip() for v in pos.split(";")]
        dulat_variants = [v.strip() for v in row.dulat.split(";")]
        changed = False
        out = []

        for idx, var in enumerate(variants):
            variant = var.strip()
            pos_v = pos_variants[idx].strip() if idx < len(pos_variants) else ""
            dulat_tok = dulat_variants[idx].strip() if idx < len(dulat_variants) else ""

            new_variant = self._fix_variant(
                analysis_variant=variant,
                pos_variant=pos_v,
                dulat_token=dulat_tok,
                suffix=matched_suffix,
                surface=surface,
            )
            if new_variant != variant:
                changed = True
            out.append(new_variant)

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

    def _fix_variant(
        self,
        analysis_variant: str,
        pos_variant: str,
        dulat_token: str,
        suffix: str,
        surface: str,
    ) -> str:
        # Already has '+' — suffix already marked
        if "+" in analysis_variant:
            return analysis_variant

        # Must have noun-like/adjectival POS for suffix injection
        first_pos = pos_variant.split(",")[0].strip() if pos_variant else ""
        if not any(first_pos.startswith(p) for p in _SUFFIXABLE_POS_PREFIXES):
            return analysis_variant

        # Require DULAT evidence that this token supports pronominal suffixes.
        if not self._is_suffix_dulat_token(dulat_token, surface):
            return analysis_variant

        return self._inject_suffix(analysis_variant, suffix)

    def _inject_suffix(self, analysis_variant: str, suffix: str) -> str:
        """Try to inject '+' before the suffix in a single analysis variant."""
        # Analysis ends with suffix letters followed by optional closure
        # e.g., "npšh/" → "npš/+h"
        # e.g., "bth(II)/" → "bt(II)/+h"
        # Strip trailing closure markers
        core = analysis_variant.rstrip("/")

        if core.endswith(suffix):
            base = core[: -len(suffix)]
            # Re-add the '/' if the original had it
            if analysis_variant.endswith("/"):
                return base + "/+" + suffix
            else:
                return base + "+" + suffix

        # Check if it ends with suffix + homonym tag + /
        m = re.match(r"^(.+?)" + re.escape(suffix) + r"(\([IVX]+\))?/$", analysis_variant)
        if m:
            base = m.group(1)
            hom = m.group(2) or ""
            return base + hom + "/+" + suffix

        return analysis_variant

    def _is_suffix_dulat_token(self, token: str, surface: str) -> bool:
        if not token or token == "?":
            return False
        if self._gate is None:
            return False
        return self._gate.has_suffix_token(token, surface=surface)
