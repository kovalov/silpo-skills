---
name: silpo-promos
description: Use when the user wants to save money on their Silpo shopping — match current promotions and coupons against the things they actually rebuy, "what that I buy is on sale right now". Joins live promos with their restock-due list.
---

# silpo-promos

Matches current promotions against your restock-due staples.

## Steps
`P = ${CLAUDE_PLUGIN_ROOT}`

1. Refresh promos (small payloads — fine to call from main, or via subagent):
   call `mcp__silpo__silpo_get_promotions` and write its JSON to
   `P/data/snapshots/promotions.json`. (silpo-collect already does this.)
2. Match: `python3 "$P/analytics/report.py" promo-match`

Requires `data/raw/` (run **silpo-collect** first). Prints staples that are
due/soon AND on promo — the highest-value buys-now. If nothing overlaps, say so
and report the loyalty/coupon balance from `data/snapshots/`.
