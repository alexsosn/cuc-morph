"""Instruction-driven high-confidence refinement for parsed tablet TSV files."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple


DISALLOWED_NORMALIZE = str.maketrans(
    {
        "ʿ": "ˤ",
        "ʕ": "ˤ",
        "ả": "a",
        "ỉ": "i",
        "ủ": "u",
    }
)

POS_LABEL_NORMALIZATION = {
    "det. / rel. functor": "det. or rel. functor",
    "subordinating / completive functor": "Subordinating or completive functor",
    "emph./det. encl. morph.": "emph. or det. encl. morph.",
    "adv./emph. functor": "adv. or emph. functor",
    "adv./prep.": "adv. or prep.",
    "adj./n.": "adj. or n.",
    "adj. /n.": "adj. or n.",
    "n./adj. (?)": "n. or adj. (?)",
    "pn/dn": "PN or DN",
    "pn/gn": "PN or GN",
    "pn/tn (?)": "PN or TN (?)",
    "dn/tn": "DN or TN",
    "gn/tn": "GN or TN",
    "tn/toponymic element": "TN or toponymic element",
}


@dataclass(frozen=True)
class RefinementResult:
    """Refinement summary for one file batch."""

    files: int
    rows: int
    changed: int


class InstructionRefiner:
    """Applies conservative, instruction-backed formatting refinements."""

    def refine_files(self, paths: Sequence[Path]) -> RefinementResult:
        file_count = 0
        row_count = 0
        changed_count = 0
        for path in paths:
            rows, changed = self.refine_file(path)
            file_count += 1
            row_count += rows
            changed_count += changed
        return RefinementResult(files=file_count, rows=row_count, changed=changed_count)

    def refine_file(self, path: Path) -> Tuple[int, int]:
        rows = 0
        changed = 0
        out_lines: List[str] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.startswith("#"):
                out_lines.append(raw)
                continue

            parts = raw.split("\t")
            if len(parts) < 2:
                out_lines.append(raw)
                continue

            rows += 1
            line_id = parts[0].strip()
            surface = self._normalize_col23(parts[1] if len(parts) > 1 else "")
            analysis = self._normalize_col23(parts[2] if len(parts) > 2 else "")
            dulat = (parts[3] if len(parts) > 3 else "").strip()
            pos = self._normalize_pos_field(parts[4] if len(parts) > 4 else "")
            gloss = (parts[5] if len(parts) > 5 else "").strip()
            note = "\t".join(parts[6:]).strip() if len(parts) > 6 else ""

            if self._is_unresolved_row(
                analysis=analysis, dulat=dulat, pos=pos, gloss=gloss, note=note
            ):
                analysis = "?"
                dulat = "?"
                pos = "?"
                gloss = "?"

            new_parts = [line_id, surface, analysis, dulat, pos, gloss]
            if note:
                new_parts.append(note)
            new_line = "\t".join(new_parts)
            if new_line != raw:
                changed += 1
            out_lines.append(new_line)

        path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        return rows, changed

    def _normalize_col23(self, value: str) -> str:
        return (value or "").translate(DISALLOWED_NORMALIZE).strip()

    def _normalize_pos_field(self, field: str) -> str:
        variants = [item.strip() for item in (field or "").split(";")]
        normalized_variants: List[str] = []
        for variant in variants:
            if not variant:
                continue
            slots = [slot.strip() for slot in variant.split(",")]
            normalized_slots: List[str] = []
            for slot in slots:
                if not slot:
                    continue
                compact = " ".join(slot.split())
                normalized_slots.append(
                    POS_LABEL_NORMALIZATION.get(compact.lower(), compact)
                )
            normalized_variants.append(",".join(normalized_slots))
        return ";".join(normalized_variants)

    def _is_unresolved_row(
        self, analysis: str, dulat: str, pos: str, gloss: str, note: str
    ) -> bool:
        note_upper = (note or "").upper()
        if "DULAT: NOT FOUND" in note_upper:
            return True
        if (analysis or "").strip() == "?":
            return True
        if not dulat and not pos and not gloss:
            return True
        return False
