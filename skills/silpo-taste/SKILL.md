---
name: silpo-taste
description: Use when the user wants product recommendations / new things to try at Silpo that match their tastes — "what new should I buy", discovery based on their favorites and top categories.
---

# silpo-taste (recommender)

Suggests items you haven't bought, in your favorite categories.

## Steps
`P = ${CLAUDE_PLUGIN_ROOT}`

1. Find your top favorites: `python3 "$P/analytics/report.py" restock` (the most
   frequent staples) — or read them from spend output.
2. Fetch candidates via the connected MCP (small payloads; a subagent is fine):
   for the top ~8 favorite product names, call `silpo_find_products_batch` to get
   each id, then `silpo_get_similar_products {id}`; also call
   `silpo_get_popular_categories`. Collect into
   `P/data/snapshots/discover.json` as `{"similar":[...], "popular":[...]}`.
3. Recommend: `python3 "$P/analytics/report.py" taste [--top=20]`

Requires `data/raw/` (run **silpo-collect** first). Output = new items in your top
categories you've never bought. Relay grouped by category.

> First live run: confirm `silpo_get_similar_products` takes `{id}` and the id
> field from `find_products_batch`.
