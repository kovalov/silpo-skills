---
name: silpo-coupons
description: Use when the user wants to make the most of their Silpo coupons — which are expiring soon, what discounts they hold, "use them before they burn". Lists coupons soonest-expiry-first and flags ones expiring within a week.
---

# silpo-coupons (coupon maximizer)

**Preflight:** run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/check_mcp.sh"`. If non-zero,
relay its output (Silpo MCP setup) and stop.

## Steps
`P = ${CLAUDE_PLUGIN_ROOT}`

1. Refresh coupons (small payload): call `mcp__silpo__silpo_get_my_coupons` and
   write its JSON to `P/data/snapshots/coupons.json`. (silpo-collect also does this.)
2. Report: `python3 "$P/analytics/report.py" coupons`

Every coupon with value + days-to-expiry, soonest first; ⏰ flags ≤7 days. Relay
the expiring-soon ones (use-it-or-lose-it).

> Coupon field names vary; parser is defensive. If expiry shows blank, inspect
> `data/snapshots/coupons.json` and add the date key to `cmd_coupons` in
> `analytics/report.py`.
