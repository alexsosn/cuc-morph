# Changelog

## 2026-02-18

- Moved morphology lint report generation from GitHub Actions to a local pre-commit workflow.
- Added `scripts/generate_lint_reports.py` and `lint_reports/` modules to run linter with local DULAT/UDB databases and materialize committed reports under `reports/`.
- Added tracked hook `.githooks/pre-commit` and installer `scripts/install_git_hooks.sh` to enforce report refresh before commit.
- Added report parser `scripts/parse_lint_reports.py` and simplified `.github/workflows/morphology-lint.yml` to parse committed reports only.
- Added unit tests for lint output parsing and SVG trend chart rendering.
- Updated pre-commit hook to run Ruff on staged Python files (`ruff format` + `ruff check --fix` + `ruff check`) before report generation.
