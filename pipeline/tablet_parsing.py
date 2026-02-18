"""Reusable pipeline for parsing KTU tablets into structured out/*.tsv files."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import scripts.bootstrap_tablet_labeling as bootstrap
import scripts.refine_results_mentions as refine
from lint_reports.generator import LintReportGenerator


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for tablet parsing pipeline."""

    source_dir: Path
    out_dir: Path
    dulat_db: Path
    udb_db: Path
    include_existing: bool = False
    source_glob: str = "KTU 1.*.tsv"


class TabletParsingPipeline:
    """Runs bootstrap, refinement, and report regeneration for tablets."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    def discover_source_files(self) -> List[Path]:
        return sorted(self.config.source_dir.glob(self.config.source_glob))

    def discover_out_files(self) -> List[Path]:
        return sorted(self.config.out_dir.glob(self.config.source_glob))

    def select_targets(
        self, explicit_names: Optional[Sequence[str]] = None
    ) -> List[Path]:
        source_files = self.discover_source_files()
        source_by_name = {item.name: item for item in source_files}

        if explicit_names:
            names = sorted(
                set(name.strip() for name in explicit_names if name and name.strip())
            )
            return [source_by_name[name] for name in names if name in source_by_name]

        if self.config.include_existing:
            return source_files

        out_names = {item.name for item in self.discover_out_files()}
        return [item for item in source_files if item.name not in out_names]

    def bootstrap_targets(self, targets: Sequence[Path]) -> Dict[str, int]:
        forms_map = bootstrap.load_dulat_forms(self.config.dulat_db)
        written = 0
        for src in targets:
            dst = self.config.out_dir / src.name
            bootstrap.process_file(src, dst, forms_map)
            written += 1
        return {"bootstrap_written": written}

    def refine_targets(self, targets: Sequence[Path]) -> Dict[str, int]:
        _entries_by_id, forms_map, _lemma_map, suffix_map, forms_morph = (
            refine.load_entries(self.config.dulat_db)
        )
        reverse_mentions, entry_ref_count, entry_tablets, entry_family_count = (
            refine.load_reverse_mentions(
                self.config.dulat_db,
                self.config.udb_db,
            )
        )

        rows_total = 0
        changed_total = 0
        for src in targets:
            out_file = self.config.out_dir / src.name
            rows, changed = refine.refine_file(
                out_file,
                out_file,
                forms_map,
                suffix_map,
                forms_morph,
                reverse_mentions,
                entry_ref_count,
                entry_tablets,
                entry_family_count,
            )
            rows_total += rows
            changed_total += changed

        return {
            "refine_rows": rows_total,
            "refine_changed": changed_total,
        }

    def regenerate_reports(self) -> int:
        generator = LintReportGenerator(
            out_dir=self.config.out_dir,
            reports_dir=Path("reports"),
            dulat_db=self.config.dulat_db,
            udb_db=self.config.udb_db,
            linter_path=Path("linter") / "lint.py",
        )
        return generator.run()

    def run(
        self, explicit_names: Optional[Sequence[str]] = None, dry_run: bool = False
    ) -> Dict[str, object]:
        targets = self.select_targets(explicit_names=explicit_names)
        summary: Dict[str, object] = {
            "targets": [path.name for path in targets],
            "target_count": len(targets),
            "dry_run": dry_run,
        }

        if dry_run or not targets:
            return summary

        self.config.out_dir.mkdir(parents=True, exist_ok=True)

        summary.update(self.bootstrap_targets(targets))
        summary.update(self.refine_targets(targets))
        summary["report_exit_code"] = self.regenerate_reports()

        return summary
