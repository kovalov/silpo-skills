---
name: silpo-collect
description: Use when the user wants to pull, collect, refresh, or sync their Silpo purchase history / account data — the first step before any Silpo analytics (spend, restock, promos). Pages the order history into local files via the already-connected Silpo MCP, keeping the huge responses out of the main chat.
---

# silpo-collect

**Preflight:** run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/check_mcp.sh"`. If it exits
non-zero, relay its output (Silpo MCP setup steps) to the user and stop.

Pulls in-store (offline) + online purchase history into `data/raw/` using the
**already-connected** Silpo MCP (`mcp__silpo__*`). No separate login.

## Two things that bite (read first)
1. **Order pages are ~260KB each** → calling the history tools in the MAIN thread
   floods context. So do it in a **subagent** (its context absorbs the payloads,
   then is discarded). Never call `silpo_get_my_offline_orders` from the main thread.
2. **`silpo_get_my_offline_orders` REQUIRES a valid delivery slot context** —
   `branchId`, `deliveryType`, `timeslotStart`, `timeslotEnd`. The cart's saved
   timeslot is usually **expired** (validation `timeslot.not_found`). You MUST fetch
   a fresh available slot first, or the call fails. (This was the original bug.)

## Steps
`P = ${CLAUDE_PLUGIN_ROOT}`

Dispatch ONE subagent (Agent tool, general-purpose) with this task:

> Use the connected Silpo MCP. Save raw pages to disk; do NOT return raw data.
>
> **A. Get a valid slot context (required for offline history):**
> 1. `silpo_get_my_shopping_cart` → `shoppingCartId`.
> 2. `silpo_get_shopping_cart_by_id {shoppingCartId}` → read
>    `cart.shipments[0].branchId` and `cart.deliveryType`.
>    (If `deliveryType == "DeliveryExpressByPromise"`, use `"DeliveryHome"` instead.)
> 3. `silpo_get_time_slots {branchId, deliveryTypes:[deliveryType], start:<today ISO>, limit:10}`
>    → pick the FIRST slot with `available:true`; its `start`/`end` are
>    `timeslotStart`/`timeslotEnd`. (Do NOT trust the cart's own timeslot — it's
>    usually expired.)
>
> **B. Offline history (paginate, write to disk):**
> Call `silpo_get_my_offline_orders {branchId, deliveryType, timeslotStart,
> timeslotEnd, limit:10, offset:0}` (leave dateStart/dateEnd unset → last 6 months).
> Write the full JSON verbatim to `P/data/raw/offline-0.json`. Repeat with
> `offset += 10` (`offline-10.json`, `offline-20.json`, …) until a page has < 10
> orders. (Pages may exceed the inline limit and spill to the MCP cache — copy
> that file's content verbatim to the target filename.)
>
> **C. Online history:** `silpo_get_my_online_orders {limit:50, offset:0}` →
> `P/data/raw/online-0.json`; paginate if a page is full. (May be 0 — that's fine.)
>
> **D. Snapshots:** `silpo_get_promotions`, `silpo_get_my_coupons`,
> `silpo_get_loyalty_info` → `P/data/snapshots/{promotions,coupons,loyalty}.json`.
>
> Return ONLY: orders per source, date span, slot used, any errors.

Then summarize: `python3 "$P/analytics/report.py" spend` (prints `orders=N span=…`).
Relay counts/span; offer the analytics skills.
