---
name: silpo-spend
description: Use when the user wants to analyze their Silpo grocery spending — where money goes by category, top products, average basket, monthly trend, savings/bonuses. Builds an HTML dashboard from the locally collected order history.
---

# silpo-spend

## Prereq
Needs collected data in `data/raw/`. If empty, run **silpo-collect** first.

## Run
`python3 "${CLAUDE_PLUGIN_ROOT}/analytics/report.py" spend`

Reads the raw pages directly (pure stdlib, no network), prints KPIs + top
categories, writes `data/spend.html`. Relay the KPIs; offer to open the HTML.
Don't paste raw order JSON into the conversation.
