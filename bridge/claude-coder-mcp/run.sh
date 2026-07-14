#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_ROOT="$(cd -- "$HERE/.." && pwd)"

if [[ -z "${NODE_BIN:-}" ]]; then
  NODE_BIN="$(command -v node || true)"
fi
if [[ -z "${CLAUDE_BIN:-}" ]]; then
  CLAUDE_BIN="$(command -v claude || true)"
fi

if [[ -z "$NODE_BIN" || ! -x "$NODE_BIN" ]]; then
  echo "claude-coder: node executable not found; set NODE_BIN to an absolute executable path" >&2
  exit 127
fi
if [[ -z "$CLAUDE_BIN" || ! -x "$CLAUDE_BIN" ]]; then
  echo "claude-coder: claude executable not found; set CLAUDE_BIN to an absolute executable path" >&2
  exit 127
fi

export CLAUDE_BIN
export CLAUDE_MCP_WORKDIR="${CLAUDE_MCP_WORKDIR:-$PWD}"
export CLAUDE_MCP_ALLOWED_WORKDIRS="${CLAUDE_MCP_ALLOWED_WORKDIRS:-$CLAUDE_MCP_WORKDIR}"

STATE_DIR="${CLAUDE_CODEX_BRIDGE_STATE_DIR:-$HOME/.local/state/claude-codex-bridge}"
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

export CLAUDE_MCP_RUN_AUDIT_PATH="${CLAUDE_MCP_RUN_AUDIT_PATH:-$STATE_DIR/claude-mcp-runs.jsonl}"
export CLAUDE_MCP_LIFECYCLE_AUDIT_PATH="${CLAUDE_MCP_LIFECYCLE_AUDIT_PATH:-$STATE_DIR/claude-mcp-lifecycle.jsonl}"
export MCP_SUPERVISOR_LIFECYCLE_AUDIT_PATH="${MCP_SUPERVISOR_LIFECYCLE_AUDIT_PATH:-$STATE_DIR/mcp-supervisor-claude-coder-lifecycle.jsonl}"

exec "$NODE_BIN" "$BRIDGE_ROOT/mcp-stdio-supervisor.mjs" \
  --name claude-coder \
  -- "$NODE_BIN" "$HERE/server.mjs" "$@"
