"""Refine nominal/adjectival POS from exact DULAT form morphology."""

from __future__ import annotations

import re
from typing import Optional

from pipeline.steps.base import RefinementStep, TabletRow
from pipeline.steps.dulat_gate import DulatMorphGate

_MASC_RE = re.compile(r"m\.", flags=re.IGNORECASE)
_FEM_RE = re.compile(r"f\.", flags=re.IGNORECASE)
_DUAL_POS_RE = re.compile(r"du\.", flags=re.IGNORECASE)


def _split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";")]


def _split_comma(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",")]


def _has_feminine_marker(morphologies: set[str]) -> bool:
    for morph in morphologies:
        parts = _split_comma((morph or "").lower())
        if any(part == "f." for part in parts):
            return True
    return False


def _has_dual_marker(morphologies: set[str]) -> bool:
    for morph in morphologies:
        parts = _split_comma((morph or "").lower())
        if any(part in {"du.", "dual"} for part in parts):
            return True
    return False


def _has_singular_marker(morphologies: set[str]) -> bool:
    for morph in morphologies:
        parts = _split_comma((morph or "").lower())
        if any(part in {"sg.", "sing", "singular"} for part in parts):
            return True
    return False


def _has_plural_marker(morphologies: set[str]) -> bool:
    for morph in morphologies:
        parts = _split_comma((morph or "").lower())
        if any(part in {"pl.", "plur", "plural"} for part in parts):
            return True
    return False


def _pos_gender(head: str) -> str:
    lower = (head or "").lower()
    if "f." in lower:
        return "f."
    if "m." in lower:
        return "m."
    return ""


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

        token_genders = set()
        token_gender_getter = getattr(self._gate, "token_genders", None)
        if callable(token_gender_getter):
            token_genders = set(token_gender_getter(dulat_head))

        has_fem = _has_feminine_marker(morphologies)
        has_dual = _has_dual_marker(morphologies)
        has_singular = _has_singular_marker(morphologies)
        has_plural = _has_plural_marker(morphologies)
        dual_unambiguous = has_dual and not has_singular and not has_plural
        if not has_fem and not has_dual and not token_genders:
            return value

        rewritten_head = head
        if has_fem and "f." not in rewritten_head.lower():
            if _MASC_RE.search(rewritten_head):
                rewritten_head = _MASC_RE.sub("f.", rewritten_head)
            else:
                rewritten_head = f"{rewritten_head} f."
        elif not has_fem:
            # Prevent false fem reassignments from suffixal forms like "suff.".
            # If DULAT token gender is unambiguous masculine, normalize `n. f.` -> `n. m.`.
            if token_genders == {"m."} and _pos_gender(rewritten_head) == "f.":
                rewritten_head = _FEM_RE.sub("m.", rewritten_head)

        # Add dual marker only when dual is not competing with explicit sg/pl
        # for the same exact surface form.
        if dual_unambiguous and "du." not in rewritten_head.lower():
            rewritten_head = f"{rewritten_head} du."
        elif not dual_unambiguous and "du." in rewritten_head.lower():
            rewritten_head = _DUAL_POS_RE.sub("", rewritten_head)
            rewritten_head = re.sub(r"\s{2,}", " ", rewritten_head).strip()

        if rewritten_head == head:
            return value
        if len(parts) == 1:
            return rewritten_head
        return ", ".join([rewritten_head, *parts[1:]])
