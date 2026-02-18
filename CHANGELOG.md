# Changelog

## 2026-02-18

- Moved morphology lint report generation from GitHub Actions to a local pre-commit workflow.
- Added `scripts/generate_lint_reports.py` and `lint_reports/` modules to run linter with local DULAT/UDB databases and materialize committed reports under `reports/`.
- Added tracked hook `.githooks/pre-commit` and installer `scripts/install_git_hooks.sh` to enforce report refresh before commit.
- Added report parser `scripts/parse_lint_reports.py` and simplified `.github/workflows/morphology-lint.yml` to parse committed reports only.
- Added unit tests for lint output parsing and SVG trend chart rendering.
- Updated pre-commit hook to run Ruff on staged Python files (`ruff format` + `ruff check --fix` + `ruff check`) before report generation.
- Bootstrapped first-pass structured morphology outputs for all remaining `cuc_tablets_tsv/KTU 1.*.tsv` files into `out/` (coverage now matches all `KTU 1.*` sources).
- Added reusable tablet parsing pipeline (`pipeline/tablet_parsing.py` + `scripts/run_tablet_parsing_pipeline.py`) to automate missing/new tablet processing: bootstrap, mention-based refinement, and report regeneration.
- Added unit tests for pipeline target selection and dry-run behavior.
- Added instruction-driven refinement (`pipeline/instruction_refiner.py`) to normalize disallowed col2/col3 characters and force unresolved `?` rows when DULAT is explicitly missing.
- Applied instruction-driven cleanup to newly parsed `out/KTU 1.*.tsv` tablets (excluding curated `KTU 1.1-1.6`) and refreshed reports.
- Extended instruction-driven refinement to inject DULAT-backed POS gender markers for `n.`/`adj.` slots when gender is uniquely known (including pipeline wiring and unit tests).
- Re-ran refinement across non-curated `out/KTU 1.*.tsv` outputs and regenerated reports, removing 8,350 warning-level issues in this pass.
- Strengthened `.githooks/pre-commit` to use `uv` + `.venv` for repo-wide Ruff checks and full test-suite execution before commit; kept report regeneration for lint-relevant staged changes.
- Cleared pre-existing Ruff blockers in helper scripts (`scripts/generate_lint_reports.py`, `scripts/refine_results_mentions.py`, `scripts/notarius_refinement_pass.py`) and modules (`lint_reports/charts.py`, `linter/lint.py`) so the stricter gate passes.
