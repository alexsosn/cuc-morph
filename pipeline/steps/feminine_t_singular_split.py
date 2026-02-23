"""Fix unsplit feminine singular noun endings: Xt/ -> X/t or X(t(hom)/t."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Sequence

from pipeline.steps.base import RefinementStep, TabletRow
from pipeline.steps.dulat_gate import DulatMorphGate
from pipeline.steps.onomastic_overrides import OnomasticOverrideStore

_ONOMASTIC_POS_TAGS: Sequence[str] = ("DN", "PN", "TN", "GN", "MN")
_UNSPLIT_FEM_T_RE = re.compile(r"^(?P<stem>.+?)t(?P<hom>\([IVX]+\))?/$")


def _split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";")]


def _split_comma(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",")]


class FeminineTSingularSplitFixer(RefinementStep):
    """Apply feminine singular /t split to noun-like analyses."""

    def __init__(
        self,
        overrides_path: Path | None = None,
        feminine_onomastic_tokens: set[str] | None = None,
        gate: Optional[DulatMorphGate] = None,
    ) -> None:
        self._overrides_path = overrides_path or Path("data/onomastic_gloss_overrides.tsv")
        self._gate = gate
        if feminine_onomastic_tokens is None:
            store = OnomasticOverrideStore.from_tsv(self._overrides_path)
            self._feminine_onomastic_tokens = store.feminine_tokens()
        else:
            self._feminine_onomastic_tokens = {
                OnomasticOverrideStore.normalize_key(token)
                for token in feminine_onomastic_tokens
                if (token or "").strip()
            }

    @property
    def name(self) -> str:
        return "feminine-t-singular-split"

    def refine_row(self, row: TabletRow) -> TabletRow:
        analysis_variants = _split_semicolon(row.analysis)
        if not analysis_variants:
            return row

        pos_variants = _split_semicolon(row.pos)
        dulat_variants = _split_semicolon(row.dulat)

        changed = False
        out_variants: list[str] = []
        for idx, analysis_variant in enumerate(analysis_variants):
            pos_variant = pos_variants[idx] if idx < len(pos_variants) else ""
            dulat_variant = dulat_variants[idx] if idx < len(dulat_variants) else ""
            pos_head = _split_comma(pos_variant)[0].strip() if pos_variant else ""
            dulat_head = _split_comma(dulat_variant)[0].strip() if dulat_variant else ""
            transformed = self._fix_variant(
                variant=analysis_variant,
                pos_slot=pos_head,
                dulat_slot=dulat_head,
                surface=row.surface,
            )
            out_variants.append(transformed)
            if transformed != analysis_variant:
                changed = True

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

    def _fix_variant(self, variant: str, pos_slot: str, dulat_slot: str, surface: str) -> str:
        value = (variant or "").strip()
        if not value or value == "?":
            return value
        if "+" in value or "~" in value:
            return value
        if "[" in value:
            return value
        if value.endswith(("/m", "/m=", "/t", "/t=")):
            return value

        match = _UNSPLIT_FEM_T_RE.match(value)
        if not match:
            return value
        if not self._is_feminine_context(pos_slot=pos_slot, dulat_slot=dulat_slot):
            return value
        if self._is_plural_dulat_token(dulat_slot, surface=surface):
            return value

        stem = match.group("stem")
        homonym = match.group("hom") or ""
        if homonym:
            return f"{stem}(t{homonym}/t"
        return f"{stem}/t"

    def _is_plural_dulat_token(self, token: str, surface: str = "") -> bool:
        if self._gate is None:
            return False
        token = (token or "").strip()
        if not token or token == "?":
            return False
        return self._gate.is_plural_token(token, surface=surface)

    def _is_feminine_context(self, pos_slot: str, dulat_slot: str) -> bool:
        pos_text = (pos_slot or "").strip()
        if not pos_text:
            return False

        upper = pos_text.upper()
        if "PL. TANT" in upper:
            return False
        if "N. F." in upper or "ADJ. F." in upper:
            return True

        if any(tag in upper for tag in _ONOMASTIC_POS_TAGS):
            if " F." in upper or upper.startswith("F."):
                return True
            return self._is_feminine_onomastic_token(dulat_slot)

        return False

    def _is_feminine_onomastic_token(self, token: str) -> bool:
        normalized = OnomasticOverrideStore.normalize_key(token)
        if not normalized:
            return False
        return normalized in self._feminine_onomastic_tokens
