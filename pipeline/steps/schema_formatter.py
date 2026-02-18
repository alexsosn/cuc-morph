"""Format TSV schema for labeled output files.

Responsibilities:
- enforce canonical header row for 7-column schema
- normalize separator lines to '# KTU ...'
- enforce exactly 7 tab-separated columns for data rows
- escape double quotes in data columns for GitHub TSV rendering
"""

import re
from pathlib import Path

from pipeline.steps.base import (
    RefinementStep,
    StepResult,
    is_separator_line,
    normalize_separator_line,
)

HEADER_COLUMNS = [
    "id",
    "surface form",
    "morphological parsing",
    "DULAT",
    "POS",
    "gloss",
    "comments",
]
HEADER_ROW = "\t".join(HEADER_COLUMNS)
HEADER_COLUMNS_LOWER = [value.lower() for value in HEADER_COLUMNS]


class TsvSchemaFormatter(RefinementStep):
    """Normalize labeled TSV structure without changing linguistic payload."""

    @property
    def name(self) -> str:
        return "tsv-schema"

    def refine_row(self, row):  # pragma: no cover - file-level formatter
        return row

    def refine_file(self, path: Path) -> StepResult:
        lines = path.read_text(encoding="utf-8").splitlines()
        out_lines: list[str] = []
        rows_processed = 0
        rows_changed = 0
        header_found = False

        for raw in lines:
            if self._is_header_row(raw):
                header_found = True
                if raw != HEADER_ROW:
                    rows_changed += 1
                continue

            if not raw.strip():
                out_lines.append(raw)
                continue

            if is_separator_line(raw):
                normalized_sep = normalize_separator_line(raw)
                if normalized_sep != raw:
                    rows_changed += 1
                out_lines.append(normalized_sep)
                continue

            parts = raw.split("\t")
            line_id = (parts[0] if parts else "").strip()
            if not line_id or not line_id[0].isdigit():
                out_lines.append(raw)
                continue

            rows_processed += 1
            normalized = self._normalize_columns(parts)
            if normalized != raw:
                rows_changed += 1
            out_lines.append(normalized)

        if not header_found:
            rows_changed += 1
        out_lines = [HEADER_ROW] + out_lines

        path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        return StepResult(file=path.name, rows_processed=rows_processed, rows_changed=rows_changed)

    def _is_header_row(self, raw: str) -> bool:
        parts = [part.strip().lower() for part in raw.split("\t")]
        return parts == HEADER_COLUMNS_LOWER

    def _normalize_columns(self, parts: list[str]) -> str:
        if len(parts) < 7:
            fixed = parts + [""] * (7 - len(parts))
        elif len(parts) > 7:
            merged_comment = " ".join(p.strip() for p in parts[6:] if p.strip())
            fixed = parts[:6] + [merged_comment]
        else:
            fixed = parts

        escaped = [re.sub(r'(?<!\\)"', r'\\"', part) for part in fixed]
        return "\t".join(escaped)
