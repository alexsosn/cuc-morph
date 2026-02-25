"""Split mixed verb form POS options by analysis encoding conventions.

Conventions:
- finite forms (prefc./suffc./impv.) -> `[...]`
- non-finite forms (inf./ptcpl.) -> `[/...]`
"""

from __future__ import annotations

import re

from pipeline.steps.base import RefinementStep, TabletRow

_VB_POS_HEAD_RE = re.compile(r"^\s*vb\.?\b", flags=re.IGNORECASE)
_VERBAL_NOUN_POS_RE = re.compile(r"\bvb\.\s*n\.", flags=re.IGNORECASE)
_FORM_INFINITE_RE = re.compile(r"\binf\.", flags=re.IGNORECASE)
_FORM_PTCP_RE = re.compile(
    r"(?:\bact\.\s*ptcpl\.|\bpass\.\s*ptcpl\.|\bptcpl\.)",
    flags=re.IGNORECASE,
)
_FORM_FINITE_RE = re.compile(r"(?:\bprefc\.|\bsuffc\.|\bimpv\.)", flags=re.IGNORECASE)


def _split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";")]


def _split_slash_options(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*/\s*", (value or "").strip()) if part.strip()]


def _is_target_pos(value: str) -> bool:
    text = (value or "").strip()
    if not _VB_POS_HEAD_RE.search(text):
        return False
    if _VERBAL_NOUN_POS_RE.search(text):
        return False
    return True


def _requires_nonfinite_encoding(pos_option: str) -> bool:
    text = (pos_option or "").strip()
    return bool(_FORM_INFINITE_RE.search(text) or _FORM_PTCP_RE.search(text))


def _requires_finite_encoding(pos_option: str) -> bool:
    text = (pos_option or "").strip()
    return bool(_FORM_FINITE_RE.search(text))


def _to_nonfinite_encoding(analysis: str) -> str:
    text = (analysis or "").strip()
    if "[/" in text:
        return text
    if "[" not in text:
        return text
    return text.replace("[", "[/", 1)


def _to_finite_encoding(analysis: str) -> str:
    text = (analysis or "").strip()
    if "[/" not in text:
        return text
    return text.replace("[/", "[", 1)


def _join_options(options: list[str]) -> str:
    return " / ".join(options)


class VerbFormEncodingSplitFixer(RefinementStep):
    """Ensure POS form options align with `[` vs `[/` verbal analysis encoding."""

    @property
    def name(self) -> str:
        return "verb-form-encoding-split"

    def refine_row(self, row: TabletRow) -> TabletRow:
        analysis_variants = _split_semicolon(row.analysis)
        dulat_variants = _split_semicolon(row.dulat)
        pos_variants = _split_semicolon(row.pos)
        gloss_variants = _split_semicolon(row.gloss)

        if not analysis_variants or not pos_variants:
            return row

        changed = False
        out_analysis: list[str] = []
        out_dulat: list[str] = []
        out_pos: list[str] = []
        out_gloss: list[str] = []

        for idx, analysis in enumerate(analysis_variants):
            dulat = (
                dulat_variants[idx]
                if idx < len(dulat_variants)
                else (dulat_variants[0] if dulat_variants else "")
            )
            pos = (
                pos_variants[idx]
                if idx < len(pos_variants)
                else (pos_variants[0] if pos_variants else "")
            )
            gloss = (
                gloss_variants[idx]
                if idx < len(gloss_variants)
                else (gloss_variants[0] if gloss_variants else "")
            )

            if not _is_target_pos(pos):
                out_analysis.append(analysis)
                out_dulat.append(dulat)
                out_pos.append(pos)
                out_gloss.append(gloss)
                continue

            options = _split_slash_options(pos)
            if len(options) <= 1:
                normalized_analysis = analysis
                if options and _requires_nonfinite_encoding(options[0]):
                    converted = _to_nonfinite_encoding(analysis)
                    if converted != analysis:
                        changed = True
                    normalized_analysis = converted
                elif options and _requires_finite_encoding(options[0]):
                    converted = _to_finite_encoding(analysis)
                    if converted != analysis:
                        changed = True
                    normalized_analysis = converted

                out_analysis.append(normalized_analysis)
                out_dulat.append(dulat)
                out_pos.append(pos)
                out_gloss.append(gloss)
                continue

            finite_options: list[str] = []
            nonfinite_options: list[str] = []
            neutral_options: list[str] = []
            for option in options:
                finite = _requires_finite_encoding(option)
                nonfinite = _requires_nonfinite_encoding(option)
                if finite and not nonfinite:
                    finite_options.append(option)
                elif nonfinite and not finite:
                    nonfinite_options.append(option)
                elif finite and nonfinite:
                    neutral_options.append(option)
                else:
                    neutral_options.append(option)

            # No mixed form classes -> keep row-level variant and normalize encoding if needed.
            if not finite_options or not nonfinite_options:
                normalized_analysis = analysis
                if nonfinite_options:
                    converted = _to_nonfinite_encoding(analysis)
                    if converted != analysis:
                        changed = True
                    normalized_analysis = converted
                elif finite_options:
                    converted = _to_finite_encoding(analysis)
                    if converted != analysis:
                        changed = True
                    normalized_analysis = converted

                out_analysis.append(normalized_analysis)
                out_dulat.append(dulat)
                out_pos.append(pos)
                out_gloss.append(gloss)
                continue

            # Mixed finite/non-finite options -> split into two aligned variants.
            finite_pos = _join_options(finite_options + neutral_options)
            nonfinite_pos = _join_options(nonfinite_options + neutral_options)
            finite_analysis = _to_finite_encoding(analysis)
            nonfinite_analysis = _to_nonfinite_encoding(analysis)

            out_analysis.append(finite_analysis)
            out_dulat.append(dulat)
            out_pos.append(finite_pos)
            out_gloss.append(gloss)

            out_analysis.append(nonfinite_analysis)
            out_dulat.append(dulat)
            out_pos.append(nonfinite_pos)
            out_gloss.append(gloss)
            changed = True

        deduped: list[tuple[str, str, str, str]] = []
        for item in zip(out_analysis, out_dulat, out_pos, out_gloss):
            if item in deduped:
                changed = True
                continue
            deduped.append(item)

        final_analysis = "; ".join(item[0] for item in deduped)
        final_dulat = "; ".join(item[1] for item in deduped)
        final_pos = "; ".join(item[2] for item in deduped)
        final_gloss = "; ".join(item[3] for item in deduped)

        if (
            not changed
            and final_analysis == row.analysis
            and final_dulat == row.dulat
            and final_pos == row.pos
            and final_gloss == row.gloss
        ):
            return row

        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis=final_analysis,
            dulat=final_dulat,
            pos=final_pos,
            gloss=final_gloss,
            comment=row.comment,
        )
