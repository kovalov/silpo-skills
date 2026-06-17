---
name: silpo-price-watch
description: Use when the user wants to see how prices changed on the things they actually buy — personal grocery inflation, "what got more expensive", biggest price movers in their basket over time.
---

# silpo-price-watch (personal CPI)

## Prereq
Needs `data/raw/` (run **silpo-collect** first). No live calls — uses prices
already in your history.

## Run
`python3 "${CLAUDE_PLUGIN_ROOT}/analytics/report.py" price-watch [--min=3] [--top=25]`

Unit price you PAID per repeat product, first → latest, biggest swing first.
Relay the top ▲ risers / ▼ drops. Caveat: own paid price (promo-affected), no
pack-size normalization — a swing can be a promo or size change, not only inflation.
