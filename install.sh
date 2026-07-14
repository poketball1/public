#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./install.sh --project /absolute/path/to/project [options]

Options:
  --project PATH        Claude/Codex가 작업할 실제 repository 절대경로 (필수)
  --codex-config PATH   Codex config 경로 (기본: ~/.codex/config.toml)
  --skill-scope SCOPE   project 또는 user (기본: project)
  --dry-run             파일을 바꾸지 않고 계획만 출력
  -h, --help            도움말

이 installer는 CLI를 설치하거나 로그인하지 않는다.
기존 claude-coder MCP table이 있으면 덮어쓰지 않고 중단한다.
EOF
}

PROJECT=""
CODEX_CONFIG="$HOME/.codex/config.toml"
SKILL_SCOPE="project"
DRY_RUN=0

while (($#)); do
  case "$1" in
    --project)
      PROJECT="${2:-}"
      shift 2
      ;;
    --codex-config)
      CODEX_CONFIG="${2:-}"
      shift 2
      ;;
    --skill-scope)
      SKILL_SCOPE="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

if [[ -z "$PROJECT" ]]; then
  echo "--project is required" >&2
  usage >&2
  exit 64
fi
if [[ "$PROJECT" != /* ]]; then
  echo "--project must be an absolute WSL/Linux path: $PROJECT" >&2
  exit 64
fi
if [[ "$CODEX_CONFIG" != /* ]]; then
  echo "--codex-config must be an absolute WSL/Linux path: $CODEX_CONFIG" >&2
  exit 64
fi
if [[ ! -d "$PROJECT" ]]; then
  echo "project directory does not exist: $PROJECT" >&2
  exit 66
fi
if [[ "$SKILL_SCOPE" != "project" && "$SKILL_SCOPE" != "user" ]]; then
  echo "--skill-scope must be project or user" >&2
  exit 64
fi

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MCP_WRAPPER="$ROOT/bridge/claude-coder-mcp/run.sh"
SKILL_SOURCE="$ROOT/skills/codex-bg/SKILL.md"

NODE_BIN="$(command -v node || true)"
CLAUDE_BIN="$(command -v claude || true)"
CODEX_BIN="$(command -v codex || true)"

for pair in "node:$NODE_BIN" "claude:$CLAUDE_BIN" "codex:$CODEX_BIN"; do
  name="${pair%%:*}"
  path="${pair#*:}"
  if [[ -z "$path" || ! -x "$path" ]]; then
    echo "$name executable not found inside WSL PATH" >&2
    exit 127
  fi
done

if [[ ! -f "$MCP_WRAPPER" || ! -f "$SKILL_SOURCE" ]]; then
  echo "installer assets are missing; run this script from a complete poketball1/public clone" >&2
  exit 66
fi

if [[ "$SKILL_SCOPE" == "project" ]]; then
  SKILL_DEST="$PROJECT/.claude/skills/codex-bg/SKILL.md"
else
  SKILL_DEST="$HOME/.claude/skills/codex-bg/SKILL.md"
fi

if [[ -f "$CODEX_CONFIG" ]] &&
  grep -Eq '^\[mcp_servers\.("?claude-coder"?)\][[:space:]]*$' "$CODEX_CONFIG"; then
  echo "existing claude-coder MCP config found: $CODEX_CONFIG" >&2
  echo "nothing was changed; remove or rename that table after reviewing it, then rerun" >&2
  exit 73
fi

STATE_DIR="$HOME/.local/state/claude-codex-bridge"

toml_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '%s' "$value"
}

Q_WRAPPER="$(toml_escape "$MCP_WRAPPER")"
Q_NODE="$(toml_escape "$NODE_BIN")"
Q_CLAUDE="$(toml_escape "$CLAUDE_BIN")"
Q_PROJECT="$(toml_escape "$PROJECT")"
Q_STATE="$(toml_escape "$STATE_DIR")"
SAFE_PATH="$(dirname "$CLAUDE_BIN"):$(dirname "$NODE_BIN"):/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Q_PATH="$(toml_escape "$SAFE_PATH")"

read -r -d '' CONFIG_BLOCK <<EOF || true

[mcp_servers.claude-coder]
command = "$Q_WRAPPER"
args = []
startup_timeout_sec = 10.0
tool_timeout_sec = 1860.0
default_tools_approval_mode = "approve"

[mcp_servers.claude-coder.env]
NODE_BIN = "$Q_NODE"
CLAUDE_BIN = "$Q_CLAUDE"
CLAUDE_MCP_MODEL = "sonnet"
CLAUDE_MCP_ALLOWED_MODELS = "sonnet,opus,haiku"
CLAUDE_MCP_WORKDIR = "$Q_PROJECT"
CLAUDE_MCP_ALLOWED_WORKDIRS = "$Q_PROJECT"
CLAUDE_MCP_DEFAULT_PERMISSION_MODE = "default"
CLAUDE_MCP_DEFAULT_WRITE_PERMISSION_MODE = "acceptEdits"
CLAUDE_MCP_ALLOW_DANGEROUS = "0"
CLAUDE_MCP_ALLOW_BARE = "0"
CLAUDE_MCP_DEFAULT_WAIT_MS = "1800000"
CLAUDE_MCP_MAX_WAIT_MS = "1800000"
CLAUDE_MCP_WRITE_TIMEOUT_MS = "1800000"
CLAUDE_MCP_RUN_AUDIT_PATH = "$Q_STATE/claude-mcp-runs.jsonl"
CLAUDE_MCP_LIFECYCLE_AUDIT_PATH = "$Q_STATE/claude-mcp-lifecycle.jsonl"
MCP_SUPERVISOR_LIFECYCLE_AUDIT_PATH = "$Q_STATE/mcp-supervisor-claude-coder-lifecycle.jsonl"
PATH = "$Q_PATH"
EOF

echo "project:       $PROJECT"
echo "codex config:  $CODEX_CONFIG"
echo "skill target:  $SKILL_DEST"
echo "MCP wrapper:   $MCP_WRAPPER"
echo "state dir:     $STATE_DIR"

if ((DRY_RUN)); then
  printf '\n--- config block that would be appended ---\n%s\n' "$CONFIG_BLOCK"
  exit 0
fi

mkdir -p "$(dirname "$SKILL_DEST")" "$(dirname "$CODEX_CONFIG")" "$STATE_DIR"
chmod 700 "$STATE_DIR"
cp "$SKILL_SOURCE" "$SKILL_DEST"

if [[ -f "$CODEX_CONFIG" ]]; then
  BACKUP="$CODEX_CONFIG.bak.$(date +%Y%m%d-%H%M%S)"
  cp -p "$CODEX_CONFIG" "$BACKUP"
  echo "backup:        $BACKUP"
fi

TMP_CONFIG="$(mktemp "${CODEX_CONFIG}.tmp.XXXXXX")"
trap 'rm -f "$TMP_CONFIG"' EXIT
if [[ -f "$CODEX_CONFIG" ]]; then
  cp "$CODEX_CONFIG" "$TMP_CONFIG"
fi
printf '%s\n' "$CONFIG_BLOCK" >> "$TMP_CONFIG"
chmod 600 "$TMP_CONFIG"
mv "$TMP_CONFIG" "$CODEX_CONFIG"
trap - EXIT

chmod +x "$MCP_WRAPPER"
"$NODE_BIN" --check "$ROOT/bridge/claude-coder-mcp/server.mjs"
"$NODE_BIN" --check "$ROOT/bridge/mcp-stdio-supervisor.mjs"
"$NODE_BIN" --check "$ROOT/bridge/lib/lifecycle-audit.mjs"

echo
echo "installed successfully"
echo "1) close every running Codex process"
echo "2) start Codex again inside: $PROJECT"
echo "3) run: codex mcp get claude-coder"
echo "4) ask Codex to call claude_health"
echo "5) in a new Claude Code session, invoke /codex-bg for the Claude -> Codex smoke test"
