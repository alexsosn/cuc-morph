"""Repair recurring analysis/surface reconstructability mismatches."""

from __future__ import annotations

from pipeline.steps.analysis_utils import normalize_surface
from pipeline.steps.base import RefinementStep, TabletRow


def _split_semicolon(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";")]


def _split_comma(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",")]


class SurfaceReconstructabilityFixer(RefinementStep):
    """Normalize known recurrent form/analysis mismatch classes."""

    @property
    def name(self) -> str:
        return "surface-reconstructability"

    def refine_row(self, row: TabletRow) -> TabletRow:
        if self._is_thmt_singular_row(row):
            return self._rewrite_thmt_singular(row)

        analysis_variants = _split_semicolon(row.analysis)
        if not analysis_variants:
            return row
        dulat_variants = _split_semicolon(row.dulat)

        changed = False
        out_analysis: list[str] = []
        for idx, analysis_variant in enumerate(analysis_variants):
            dulat_variant = dulat_variants[idx] if idx < len(dulat_variants) else ""
            dulat_head = _split_comma(dulat_variant)[0] if dulat_variant else ""
            rewritten = self._rewrite_variant(
                surface=row.surface,
                analysis_variant=analysis_variant,
                dulat_head=dulat_head,
            )
            if rewritten != analysis_variant:
                changed = True
            out_analysis.append(rewritten)

        out_pos = row.pos
        if (
            normalize_surface(row.surface).lower() == "thmtm"
            and row.dulat.strip() == "thmt"
            and "du." in (row.pos or "").lower()
        ):
            out_pos = "n. f."
            changed = True

        if not changed:
            return row

        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis="; ".join(out_analysis),
            dulat=row.dulat,
            pos=out_pos,
            gloss=row.gloss,
            comment=row.comment,
        )

    def _is_thmt_singular_row(self, row: TabletRow) -> bool:
        return (
            normalize_surface(row.surface).lower() == "thmt"
            and row.dulat.strip() == "thmt"
            and row.pos.strip().startswith("n. f.")
        )

    def _rewrite_thmt_singular(self, row: TabletRow) -> TabletRow:
        analysis = "thm(t/t; thm/t"
        dulat = "thmt; thm"
        pos = "n. f.; n. m."
        gloss_primary = row.gloss.strip() or "Primordial Ocean"
        gloss = f"{gloss_primary}; ocean/deep"
        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis=analysis,
            dulat=dulat,
            pos=pos,
            gloss=gloss,
            comment=row.comment,
        )

    def _rewrite_variant(
        self,
        surface: str,
        analysis_variant: str,
        dulat_head: str,
    ) -> str:
        surface_norm = normalize_surface(surface).lower()
        dulat = (dulat_head or "").strip()

        if dulat == "thmt" and surface_norm == "thmtm":
            return "thm(t/tm"

        if dulat == "bnt (II)":
            if surface_norm == "bnwt":
                return "bn&w(t(II)/t="
            if surface_norm == "bnwth":
                return "bn&w(t(II)/t=+h"

        if surface_norm == "mtm":
            if dulat == "mt (II)":
                return "mt(II)/~m"
            if dulat == "mt (I)":
                return "mt(I)/m"
            if dulat == "mt (III)":
                return "mt(III)/m"
            if dulat == "/m-t/":
                return "mt[~m"

        if dulat == "ym (I)":
            if surface_norm == "ymm":
                return "ym(I)/m"
            if surface_norm == "ymt":
                return "ym(I)/t="
            if surface_norm == "ymy":
                return "ym(I)&y/"

        return analysis_variant
