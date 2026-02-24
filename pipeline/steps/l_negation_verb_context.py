"""Prune `l(II)` negation readings when not followed by a verbal token."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pipeline.steps.base import RefinementStep, StepResult, TabletRow, parse_tsv_line


def _is_l_negation_row(row: TabletRow) -> bool:
    return (
        row.surface.strip() == "l"
        and row.analysis.strip() == "l(II)"
        and row.dulat.strip() == "l (II)"
        and row.pos.strip() == "adv."
        and row.gloss.strip() in {"no", "not"}
    )


@dataclass(frozen=True)
class _TokenGroup:
    key: tuple[str, str]
    indexes: list[int]
    rows: list[TabletRow]


class LNegationVerbContextPruner(RefinementStep):
    """Drop ambiguous `l(II)` rows unless the following token is verbal."""

    @property
    def name(self) -> str:
        return "l-negation-verb-context"

    def refine_row(self, row: TabletRow) -> TabletRow:
        return row

    def refine_file(self, path: Path) -> StepResult:
        lines = path.read_text(encoding="utf-8").splitlines()
        parsed_rows: dict[int, TabletRow] = {}
        data_indexes: list[int] = []
        for index, raw in enumerate(lines):
            row = parse_tsv_line(raw)
            if row is None:
                continue
            parsed_rows[index] = row
            data_indexes.append(index)

        groups = self._group_rows(data_indexes=data_indexes, parsed_rows=parsed_rows)
        remove_indexes: set[int] = set()

        for idx, group in enumerate(groups):
            if group.key[1] != "l":
                continue
            next_group = groups[idx + 1] if idx + 1 < len(groups) else None
            next_has_verb = bool(
                next_group and any("vb" in (row.pos or "") for row in next_group.rows)
            )
            if next_has_verb:
                continue

            l2_indexes = [
                row_index
                for row_index, row in zip(group.indexes, group.rows)
                if _is_l_negation_row(row)
            ]
            if not l2_indexes:
                continue
            # Do not delete the entire token if only one analysis exists.
            if len(l2_indexes) == len(group.indexes):
                continue
            remove_indexes.update(l2_indexes)

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
        self, data_indexes: list[int], parsed_rows: dict[int, TabletRow]
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
