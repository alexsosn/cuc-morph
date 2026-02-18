# cuc-morph

## Local Lint Reports

This repository now generates morphology lint reports locally and commits them under `reports/`.

### One-time setup

1. Create virtual environment: `python3 -m venv .venv`
2. Configure tracked Git hooks: `./scripts/install_git_hooks.sh`

### Pre-commit behavior

When staged changes touch lint-relevant files (`out/*.tsv`, `linter/**`, report tooling), the pre-commit hook:

1. Runs `scripts/generate_lint_reports.py` with local DB access (`sources/dulat_cache.sqlite`, `sources/udb_cache.sqlite`)
2. Regenerates `reports/*`
3. Stages updated `reports/*` automatically

Generated files include:

- `reports/lint_report.txt`
- `reports/lint_summary.md`
- `reports/lint_stats.json`
- `reports/lint_history.json`
- `reports/lint_severity_trend.svg`
- `reports/lint_issue_types_trend.svg`
- `reports/lint_trends.md`

## GitHub Actions

GitHub Actions no longer runs the linter itself. It parses committed files under `reports/` and publishes the summary in the workflow UI.
