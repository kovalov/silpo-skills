#!/usr/bin/env bash
# Preflight: is the Silpo MCP connected in Claude Code?
# Exit 0 + "OK" if yes. Otherwise print SETUP.md (the one instruction source) and exit 1.
# Skills run this first; on non-zero they relay the output and stop.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"

show_setup() {
  echo
  cat "$DIR/SETUP.md"
}

if ! command -v claude >/dev/null 2>&1; then
  echo "✗ 'claude' CLI not on PATH — can't verify the Silpo MCP."
  show_setup
  exit 1
fi

out="$(claude mcp list 2>/dev/null)"
line="$(printf '%s\n' "$out" | grep -i silpo || true)"

if [ -z "$line" ]; then
  echo "✗ Silpo MCP not found in Claude Code."
  show_setup
  exit 1
fi

# present, but registered != connected; flag obvious failure states
if printf '%s' "$line" | grep -qiE 'fail|error|✗|disconnect|not connected'; then
  echo "⚠ Silpo MCP registered but not connected/authenticated:"
  printf '   %s\n' "$line"
  show_setup
  exit 1
fi

echo "✓ Silpo MCP connected."
printf '   %s\n' "$line"
exit 0
