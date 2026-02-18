# cuc-morph

## Local Lint Reports

This repository now generates morphology lint reports locally and commits them under `reports/`.

### One-time setup

1. Create Python 3.13 virtual environment: `UV_CACHE_DIR=.uv-cache uv venv --python 3.13 .venv`
2. Configure tracked Git hooks: `./scripts/install_git_hooks.sh`

### Pre-commit behavior

On every commit attempt, the pre-commit hook:

1. Runs `ruff format` and `ruff check --fix` on staged Python files
2. Runs `ruff check` on staged Python files and fails commit on any warning/error
3. Runs the full test suite (`python -m unittest discover -s tests -v`) and fails commit if tests fail
4. For lint-relevant staged changes (`out/*.tsv`, `linter/**`, report tooling), runs `scripts/generate_lint_reports.py` with local DB access (`sources/dulat_cache.sqlite`, `sources/udb_cache.sqlite`)
5. Regenerates `reports/*` and stages updated Python/report files automatically

Generated files include:

- `reports/lint_report.txt`
- `reports/lint_summary.md`
- `reports/lint_stats.json`
- `reports/lint_history.json`
- `reports/lint_severity_trend.svg`
- `reports/lint_issue_types_trend.svg`
- `reports/lint_trends.md`

## Tablet Parsing Pipeline

Use the reusable pipeline to process new tablets from `cuc_tablets_tsv` into `out` and regenerate reports:

- Dry-run target discovery: `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python python scripts/run_tablet_parsing_pipeline.py --dry-run`
- Parse only missing tablets (default): `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python python scripts/run_tablet_parsing_pipeline.py`
- Parse specific tablets: `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python python scripts/run_tablet_parsing_pipeline.py --files 'KTU 1.181.tsv' 'KTU 1.182.tsv'`
- Reprocess existing outputs too: `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python python scripts/run_tablet_parsing_pipeline.py --include-existing`
- Tighten/relax step safety threshold: `python scripts/run_tablet_parsing_pipeline.py --max-step-change-ratio 0.20` or `python scripts/run_tablet_parsing_pipeline.py --allow-large-step-changes`

Pipeline stages are:

1. Bootstrap from DULAT form matches
2. Mention-aware refinement (`scripts/refine_results_mentions.py` logic)
3. Instruction-driven cleanup for high-confidence cases (normalize disallowed col2/col3 characters, enforce unresolved `?` rows where DULAT is missing, and enrich `n.`/`adj.` POS slots with DULAT gender where uniquely known)
4. Step chain with DULAT-gated fixes (`noun-pos-closure`, `plural-split`, `suffix-clitic`, `weak-verb`) and per-step safety threshold checks
5. Report regeneration under `reports/`

## GitHub Actions

GitHub Actions no longer runs the linter itself. It parses committed files under `reports/` and publishes the summary in the workflow UI.
