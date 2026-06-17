---
name: silpo-budget-cart
description: Use when the user wants a Silpo cart built to a spending limit — "make me a ₴1500 weekly cart from my usuals", budget-capped basket from their staple products.
---

# silpo-budget-cart

## Prereq
`data/raw/` (run **silpo-collect** first).

## Steps
`P = ${CLAUDE_PLUGIN_ROOT}`

1. Build the spec:
   `python3 "$P/analytics/report.py" budget-cart --budget=1500 --out="$P/data/budget-cart.json"`
   Greedy by purchase frequency, priced from last paid price; prints items + est total.
2. Show the plan. On confirmation, follow **silpo-cart → "Add from a spec file"**
   with `$P/data/budget-cart.json`.

Estimate uses last paid price, so the live cart total can differ.
