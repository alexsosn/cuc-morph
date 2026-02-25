# Reconstructable Variant Pruner

## Purpose

Reduce high-noise variant rows when a token already has a reconstructable
lexical analysis.

This targets frequent bundles where one row reconstructs surface correctly but
additional rows are clitic-only or structurally non-reconstructable.

## Pipeline Step

Implemented as `ReconstructableVariantPruner` in:

- `pipeline/steps/reconstructable_variant_pruner.py`

Registered in `TabletParsingPipeline` after duplicate pruning and before
context disambiguators.

## Rule

For each contiguous `(id, surface)` token-group:

1. Find reconstructable rows (analysis reconstructs to surface).
2. Continue only if at least one reconstructable **non-clitic** row exists.
3. Prune rows that are:
   - clitic-only analyses (`+...`, `~...`, `[...]` marker payloads), or
   - non-reconstructable and non-`?` analyses.
4. Keep unresolved `?` rows for manual review.

All-clitic groups are intentionally left unchanged.

## Why High Confidence

- Only activates when a reconstructable lexical row already exists.
- Does not alter single-row tokens.
- Does not delete unresolved placeholder rows.
- Preserves conservative behavior for all-clitic groups.

