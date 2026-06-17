---
name: silpo-cart
description: Use when the user wants to build or modify their Silpo shopping cart — add items by name, reorder a past basket, build a restock/budget cart, or clear it. Write actions via the connected MCP; previews first and logs a revertible snapshot before changing anything.
---

# silpo-cart

Modifies the Silpo cart via the **connected MCP** write tools. **Write-enabled.**

## Safety / audit (do NOT skip)
`P = ${CLAUDE_PLUGIN_ROOT}`. Before ANY mutation:
1. Call `mcp__silpo__silpo_get_my_shopping_cart`.
2. Write its JSON to `P/logs/cart-pre-<ISO-timestamp>.json`.
3. Append one line `{"ts","action","args"}` to `P/logs/cart-actions.log`.

Then mutate. This makes every change revertible (required for external writes).
Always show the plan and get explicit confirmation before mutating.

## Add from a spec file (used by auto-restock-cart / budget-cart)
Spec = JSON `[{name,qty}]` (e.g. `P/data/restock-cart.json`).
1. For each item call `silpo_find_products_batch {queries:[name]}`; take the best
   hit's id. Show the resolved plan (name → product, qty; flag NO MATCH).
2. On confirmation: do the audit steps, then
   `silpo_add_or_update_cart_products {products:[{id, quantity}]}`.
3. Confirm with `silpo_get_my_shopping_cart`.

## Other actions
- **Add by name**: resolve a user's list the same way.
- **Reorder last basket**: `python3 "$P/analytics/report.py" last-order --out="$P/data/reorder-cart.json"`,
  then add-from-spec.
- **Clear**: audit, then `silpo_clear_shopping_cart`.
- **Remove**: `silpo_remove_cart_products`.

Preview before applying. Never skip the audit log.
