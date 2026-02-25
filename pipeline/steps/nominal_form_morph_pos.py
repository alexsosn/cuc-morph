"""Refine nominal/adjectival POS from exact DULAT form morphology."""

from __future__ import annotations

import re
from typing import Optional

from pipeline.steps.base import RefinementStep, TabletRow
from pipeline.steps.dulat_gate import DulatMorphGate

_MASC_RE = re.compile(r"m\.", flags=re.IGNORECASE)


def _split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";")]


def _split_comma(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",")]


class NominalFormMorphPosFixer(RefinementStep):
    """Set POS gender/number markers from exact DULAT form morphology."""

    def __init__(self, gate: Optional[DulatMorphGate] = None) -> None:
        self._gate = gate

    @property
    def name(self) -> str:
        return "nominal-form-morph-pos"

    def refine_row(self, row: TabletRow) -> TabletRow:
        if self._gate is None:
            return row

        pos_variants = _split_semicolon(row.pos)
        if not pos_variants:
            return row

        dulat_variants = _split_semicolon(row.dulat)
        out_pos: list[str] = []
        changed = False

        for idx, pos_variant in enumerate(pos_variants):
            dulat_variant = dulat_variants[idx] if idx < len(dulat_variants) else ""
            dulat_head = _split_comma(dulat_variant)[0] if dulat_variant else ""
            rewritten = self._rewrite_pos(
                pos_variant=pos_variant,
                dulat_head=dulat_head,
                surface=row.surface,
            )
            out_pos.append(rewritten)
            if rewritten != pos_variant:
                changed = True

        if not changed:
            return row

        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis=row.analysis,
            dulat=row.dulat,
            pos="; ".join(out_pos),
            gloss=row.gloss,
            comment=row.comment,
        )

    def _rewrite_pos(self, pos_variant: str, dulat_head: str, surface: str) -> str:
        value = (pos_variant or "").strip()
        if not value:
            return value

        parts = _split_comma(value)
        if not parts:
            return value
        head = parts[0].strip()
        head_lower = head.lower()
        if not (head_lower.startswith("n.") or head_lower.startswith("adj.")):
            return value

        morphologies = self._gate.surface_morphologies(dulat_head, surface=surface)
        if not morphologies:
            return value

        has_fem = any("f." in (morph or "").lower() for morph in morphologies)
        has_dual = any(
            ("du." in (morph or "").lower()) or ("dual" in (morph or "").lower())
            for morph in morphologies
        )
        if not has_fem and not has_dual:
            return value

        rewritten_head = head
        if has_fem and "f." not in rewritten_head.lower():
            if _MASC_RE.search(rewritten_head):
                rewritten_head = _MASC_RE.sub("f.", rewritten_head)
            else:
                rewritten_head = f"{rewritten_head} f."

        if has_dual and "du." not in rewritten_head.lower():
            rewritten_head = f"{rewritten_head} du."

        if rewritten_head == head:
            return value
        if len(parts) == 1:
            return rewritten_head
        return ", ".join([rewritten_head, *parts[1:]])
