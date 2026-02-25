"""Enforce assimilated nun encoding for prefixed N-stem verb analyses.

Conventions:
- Prefixed N-stem forms must encode assimilated nun as `](n]` after the
  preformative marker (e.g. `!t!](n]ṯbr[`).
"""

from __future__ import annotations

import re

from pipeline.steps.base import RefinementStep, TabletRow

_VB_POS_HEAD_RE = re.compile(r"^\s*vb\.?\b", flags=re.IGNORECASE)
_VERBAL_NOUN_POS_RE = re.compile(r"\bvb\.\s*n\.", flags=re.IGNORECASE)
_POS_STEM_RE = re.compile(r"\b(Gpass|Dpass|Lpass|Špass|Gt|Dt|Lt|Nt|tD|tL|Št|G|D|L|N|R|Š)\b")
_PREFORMATIVE_RE = re.compile(r"^![ytan](?:=+)?!", flags=re.IGNORECASE)


def _pos_requires_n_assimilation(pos_text: str) -> bool:
    pos = (pos_text or "").strip()
    if not pos:
        return False
    if not _VB_POS_HEAD_RE.search(pos):
        return False
    if _VERBAL_NOUN_POS_RE.search(pos):
        return False
    stems = set(_POS_STEM_RE.findall(pos))
    return "N" in stems


def _insert_assimilated_n_marker(analysis: str) -> str:
    match = _PREFORMATIVE_RE.match(analysis)
    if match is None:
        return analysis

    prefix_end = match.end()
    tail = analysis[prefix_end:]
    if not tail:
        return analysis

    if tail.startswith("](n]") or tail.startswith("(n") or tail.startswith("n"):
        return analysis

    return f"{analysis[:prefix_end]}](n]{tail}"


class VerbNStemAssimilationFixer(RefinementStep):
    """Insert missing `](n]` marker in prefixed N-stem analyses."""

    @property
    def name(self) -> str:
        return "verb-n-stem-assimilation"

    def refine_row(self, row: TabletRow) -> TabletRow:
        analysis = (row.analysis or "").strip()
        if not analysis or "[/" in analysis or "[" not in analysis:
            return row
        if not _pos_requires_n_assimilation(row.pos or ""):
            return row

        updated = _insert_assimilated_n_marker(analysis)
        if updated == analysis:
            return row

        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis=updated,
            dulat=row.dulat,
            pos=row.pos,
            gloss=row.gloss,
            comment=row.comment,
        )
