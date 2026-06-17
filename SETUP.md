# Silpo MCP setup

This plugin needs the **Silpo MCP server** connected in Claude Code. Installing
the plugin auto-registers it (bundled `.mcp.json`) — you usually don't add it by
hand.

## Connect / authenticate
1. Run `/mcp` → pick **silpo** → log in (browser OAuth).
2. `/mcp` should now list **silpo** with its tools.

## If `silpo` is missing or won't connect
Add it manually — the name MUST be exactly `silpo` (the skills call `mcp__silpo__*`):

```sh
claude mcp add silpo --transport http https://mcp.silpo.ua/mcp
```

or put this in `.mcp.json` / your settings:

```json
{ "mcpServers": { "silpo": { "type": "http", "url": "https://mcp.silpo.ua/mcp" } } }
```

then run `/mcp` to authenticate.

Requires a Claude Code version with HTTP-MCP + MCP OAuth support. After connecting,
re-run whatever Silpo skill you started.
