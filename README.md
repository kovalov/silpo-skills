# silpo — personal grocery analytics over the Silpo MCP

A Claude Code **plugin**: collect your Silpo purchase history, then analyze spend,
predict restocks, match promos, track personal price inflation, get
recommendations, and build/reorder carts — all on top of the **already-connected**
Silpo MCP (`mcp__silpo__*`). No separate login: auth is the session's MCP
connection.

## Install / share

Self-contained: Python stdlib + skills + the bundled Silpo MCP server config.
Needs `python3` on PATH. No npm, no build step.

Recipient, in Claude Code:
```
/plugin marketplace add /path/to/silpo-plugin     # unpacked folder, or a git URL
/plugin install silpo@silpo
/mcp                                               # authenticate "silpo" once (browser login)
```
Then: "онови мої дані Сільпо" → analytics skills.

## The one rule

Order-history responses are ~260KB per page. If the **main thread** calls the
history tools, they flood context (this is why collecting in plain chat failed).
So collection is done by a **subagent** that pages through and writes raw JSON to
`data/raw/`; its context absorbs the payloads and is discarded. Analytics are
plain stdlib Python that read `data/raw/` and emit summaries / an HTML dashboard.
The main thread never ingests raw history.

## Skills

| Skill | Does |
|-------|------|
| **silpo-collect** | Subagent pages order history → `data/raw/` + snapshots. Run first. |
| **silpo-spend**   | Spend dashboard: category split, top products, monthly trend → `data/spend.html`. |
| **silpo-restock** | Per-product repurchase cycle → OVERDUE / SOON "running low" list. |
| **silpo-promos**  | Match current promotions against your restock-due staples. |
| **silpo-coupons** | Coupons soonest-expiry-first; flags ones expiring ≤7d. |
| **silpo-price-watch** | Personal CPI: unit price you paid per repeat product, first→latest. |
| **silpo-taste**   | Recommends new items in your top categories (similar-to-favorites + popular). |
| **silpo-auto-restock-cart** | Restock forecast → cart of what's due (promo items first). |
| **silpo-budget-cart** | Cart of staples filled to a ₴ budget from last paid prices. |
| **silpo-cart**    | Add by name / from spec / reorder / clear. Previews + audit-logs before writing. |

## Data flow

```
connected MCP ──(subagent, paginated)──▶ data/raw/*.json       (raw order pages)
                                          data/snapshots/*.json (promotions, coupons, loyalty, discover)
data/raw/  ──(python report.py)──▶ console summaries + data/spend.html + cart specs
cart specs ──(model: find_products_batch → add_or_update_cart)──▶ Silpo cart   (audit-logged)
```

## Analytics CLI (read-only, no network)

```sh
P=/path/to/silpo-plugin
python3 $P/analytics/report.py spend|restock|promo-match|coupons|price-watch|taste
python3 $P/analytics/report.py restock-cart --out=$P/data/restock-cart.json
python3 $P/analytics/report.py budget-cart  --budget=1500 --out=$P/data/budget-cart.json
python3 $P/analytics/report.py last-order   --out=$P/data/reorder-cart.json
python3 $P/analytics/report.py --selftest
# test against any file/dir of raw pages:
python3 $P/analytics/report.py spend --orders=/some/dir-or-file.json
```

## Safety

- **Cart writes** snapshot the pre-state to `logs/cart-pre-*.json` and append to
  `logs/cart-actions.log` before any change; the skill previews first.
- **PII**: only promotions/coupons/loyalty are snapshotted — no profile/family,
  so nothing identifying is written to disk.
- `data/` and `logs/` are gitignored (your account data stays local).

## Collecting offline history (important)

`silpo_get_my_offline_orders` needs a valid delivery-slot context, not just
`limit/offset`. The collect subagent does: `get_my_shopping_cart` →
`get_shopping_cart_by_id` (branchId + deliveryType) → `get_time_slots` (pick an
`available:true` slot) → then paginate offline orders with
`{branchId, deliveryType, timeslotStart, timeslotEnd, limit:10, offset}`. The
cart's own timeslot is usually expired, so a fresh slot is always fetched. The
slot only enriches reorder-availability; it does not filter which orders return.
`limit` max is 10; history defaults to the last 6 months.

## Known checks

- Online orders may be 0 (in-store-only shoppers) — that's fine.
- Cart resolve uses best-guess product-id fields from `find_products_batch`;
  `silpo_get_similar_products` assumed to take `{id}` — confirm and adjust.
- `price-watch` is own-paid price (promo-affected), no pack-size normalization.
