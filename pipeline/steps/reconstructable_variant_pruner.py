"""Prune noisy token variants when a reconstructable lexical variant is available."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pipeline.config.l_negation_exception_refs import extract_separator_ref
from pipeline.steps.analysis_utils import normalize_surface, reconstruct_surface_from_analysis
from pipeline.steps.base import RefinementStep, StepResult, TabletRow, parse_tsv_line

_CLITIC_SEGMENT_RE = re.compile(r"^[+~\[][A-Za-zˤʔḫṣṯẓġḏḥṭšʕʿảỉủ]+(?:\([IVX]+\))?=*$")
_UNRESOLVED_RE = re.compile(r"^\?+$")


def _analysis_is_unresolved(analysis: str) -> bool:
    return bool(_UNRESOLVED_RE.fullmatch((analysis or "").strip()))


def _analysis_is_clitic_only(analysis: str) -> bool:
    text = (analysis or "").strip()
    if not text or _analysis_is_unresolved(text) or ";" in text:
        return False
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return False
    return all(_CLITIC_SEGMENT_RE.fullmatch(part) is not None for part in parts)


def _row_reconstructs_surface(row: TabletRow) -> bool:
    analysis = (row.analysis or "").strip()
    surface = (row.surface or "").strip()
    if not analysis or _analysis_is_unresolved(analysis) or not surface:
        return False
    reconstructed = reconstruct_surface_from_analysis(analysis)
    return normalize_surface(reconstructed) == normalize_surface(surface)


def _row_is_empty_clitic_payload(row: TabletRow) -> bool:
    analysis = (row.analysis or "").strip()
    dulat = (row.dulat or "").strip()
    return not analysis and dulat.startswith("-")


@dataclass(frozen=True)
class _TokenGroup:
    key: tuple[str, str]
    indexes: list[int]
    rows: list[TabletRow]


class ReconstructableVariantPruner(RefinementStep):
    """Keep reconstructable lexical rows and prune clearly noisy alternatives."""

    @property
    def name(self) -> str:
        return "reconstructable-variant-pruner"

    def refine_row(self, row: TabletRow) -> TabletRow:  # pragma: no cover - file-level step
        return row

    def refine_file(self, path: Path) -> StepResult:
        lines = path.read_text(encoding="utf-8").splitlines()
        parsed_rows: dict[int, TabletRow] = {}
        data_indexes: list[int] = []

        for index, raw in enumerate(lines):
            if extract_separator_ref(raw) is not None:
                continue
            row = parse_tsv_line(raw)
            if row is None:
                continue
            parsed_rows[index] = row
            data_indexes.append(index)

        groups = self._group_rows(data_indexes=data_indexes, parsed_rows=parsed_rows)
        remove_indexes: set[int] = set()

        for group in groups:
            if len(group.rows) < 2:
                continue

            reconstructable_indexes = {
                row_index
                for row_index, row in zip(group.indexes, group.rows)
                if _row_reconstructs_surface(row)
            }
            if not reconstructable_indexes:
                continue

            lexical_reconstructable_present = any(
                row_index in reconstructable_indexes and not _analysis_is_clitic_only(row.analysis)
                for row_index, row in zip(group.indexes, group.rows)
            )
            if not lexical_reconstructable_present:
                continue

            for row_index, row in zip(group.indexes, group.rows):
                if row_index in reconstructable_indexes:
                    if _analysis_is_clitic_only(row.analysis) or _row_is_empty_clitic_payload(row):
                        remove_indexes.add(row_index)
                    continue

                analysis = (row.analysis or "").strip()
                if analysis and not _analysis_is_unresolved(analysis):
                    remove_indexes.add(row_index)

        if not remove_indexes:
            return StepResult(file=path.name, rows_processed=len(data_indexes), rows_changed=0)

        out_lines: list[str] = []
        for index, raw in enumerate(lines):
            if index in remove_indexes:
                continue
            out_lines.append(raw)

        path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        return StepResult(
            file=path.name,
            rows_processed=len(data_indexes),
            rows_changed=len(remove_indexes),
        )

    def _group_rows(
        self,
        data_indexes: list[int],
        parsed_rows: dict[int, TabletRow],
    ) -> list[_TokenGroup]:
        groups: list[_TokenGroup] = []
        current_key: tuple[str, str] | None = None
        current_indexes: list[int] = []
        current_rows: list[TabletRow] = []

        for index in data_indexes:
            row = parsed_rows[index]
            key = (row.line_id.strip(), row.surface.strip())
            if current_key is None or key == current_key:
                current_key = key
                current_indexes.append(index)
                current_rows.append(row)
                continue

            groups.append(_TokenGroup(key=current_key, indexes=current_indexes, rows=current_rows))
            current_key = key
            current_indexes = [index]
            current_rows = [row]

        if current_key is not None:
            groups.append(_TokenGroup(key=current_key, indexes=current_indexes, rows=current_rows))
        return groups
