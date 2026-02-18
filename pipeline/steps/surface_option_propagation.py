"""Propagate richer option sets to parallel rows with the same surface form."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from pipeline.steps.base import RefinementStep, TabletRow, parse_tsv_line

_SEMICOLON_FIELDS = ("analysis", "dulat", "pos", "gloss")


def _split_variants(value: str) -> List[str]:
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def _variant_count(value: str) -> int:
    variants = _split_variants(value)
    return len(variants) if variants else (1 if (value or "").strip() else 0)


@dataclass(frozen=True)
class SurfacePayload:
    """Canonical aligned col3-col6 payload for one surface token."""

    analysis: str
    dulat: str
    pos: str
    gloss: str
    variant_count: int


class SurfaceOptionPropagationFixer(RefinementStep):
    """Copy richer aligned options to rows that currently have fewer options.

    This is a conservative propagation step:
    - only surfaces with length >= `min_surface_len`,
    - only aligned multi-option payloads (same option count in col3-col6),
    - only when target row shares at least one DULAT token with canonical payload.
    """

    def __init__(
        self,
        corpus_dir: Path,
        file_glob: str = "KTU 1.*.tsv",
        min_surface_len: int = 3,
    ) -> None:
        self._min_surface_len = min_surface_len
        self._payload_by_surface = self._build_payload_index(
            corpus_dir=corpus_dir, file_glob=file_glob
        )

    @property
    def name(self) -> str:
        return "surface-option-propagation"

    def refine_row(self, row: TabletRow) -> TabletRow:
        surface = (row.surface or "").strip()
        if len(surface) < self._min_surface_len:
            return row

        payload = self._payload_by_surface.get(surface)
        if payload is None:
            return row

        current_count = _variant_count(row.analysis)
        if current_count >= payload.variant_count:
            return row

        row_dulat = set(_split_variants(row.dulat))
        payload_dulat = set(_split_variants(payload.dulat))
        if row_dulat and payload_dulat and not (row_dulat & payload_dulat):
            return row

        return TabletRow(
            line_id=row.line_id,
            surface=row.surface,
            analysis=payload.analysis,
            dulat=payload.dulat,
            pos=payload.pos,
            gloss=payload.gloss,
            comment=row.comment,
        )

    def _build_payload_index(self, corpus_dir: Path, file_glob: str) -> Dict[str, SurfacePayload]:
        by_surface: Dict[str, SurfacePayload] = {}
        for path in sorted(corpus_dir.glob(file_glob)):
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw or raw.lstrip().startswith("#"):
                    continue
                row = parse_tsv_line(raw)
                if row is None:
                    continue
                if row.analysis.strip() == "?":
                    continue

                surface = (row.surface or "").strip()
                if len(surface) < self._min_surface_len:
                    continue

                counts = [_variant_count(getattr(row, field)) for field in _SEMICOLON_FIELDS]
                if any(count == 0 for count in counts):
                    continue
                if len(set(counts)) != 1:
                    continue
                if counts[0] <= 1:
                    continue

                payload = SurfacePayload(
                    analysis=row.analysis,
                    dulat=row.dulat,
                    pos=row.pos,
                    gloss=row.gloss,
                    variant_count=counts[0],
                )
                current = by_surface.get(surface)
                if current is None or payload.variant_count > current.variant_count:
                    by_surface[surface] = payload
        return by_surface
