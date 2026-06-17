---
name: silpo-auto-restock-cart
description: Use when the user wants to auto-build a Silpo cart of everything they're about to run out of — "fill my cart with what I need to rebuy". Combines the restock forecast with current promos (promo items first) and adds it to the cart for review.
---

# silpo-auto-restock-cart

## Prereq
`data/raw/` (run **silpo-collect**). For promo-first ordering, also have
`data/snapshots/promotions.json` (run **silpo-promos** / collect).

## Steps
`P = ${CLAUDE_PLUGIN_ROOT}`

1. Build the spec:
   `python3 "$P/analytics/report.py" restock-cart --out="$P/data/restock-cart.json" [--limit=15]`
   Prints overdue+soon staples (PROMO-tagged) with typical qty.
2. Show the plan. On confirmation, follow **silpo-cart → "Add from a spec file"**
   with `$P/data/restock-cart.json` (resolve names → ids, audit, add).
