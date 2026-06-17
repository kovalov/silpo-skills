---
name: silpo-restock
description: Use when the user wants to know what groceries they're about to run out of, repurchase cycles, or "what should I rebuy" — predicts per-product restock timing from Silpo purchase history.
---

# silpo-restock

## Prereq
Needs `data/raw/` (run **silpo-collect** first).

## Run
`python3 "${CLAUDE_PLUGIN_ROOT}/analytics/report.py" restock`

Mean inter-purchase interval per staple (≥3 orders) → predicted next-buy,
OVERDUE/SOON/ok, soonest first. Override today with `--ref=YYYY-MM-DD`.

Relay OVERDUE + SOON — the actionable list. Offer **silpo-promos** (on sale?) or
**silpo-auto-restock-cart** (build the basket).
