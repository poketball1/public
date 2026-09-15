#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./install.sh --project /absolute/path/to/project [options]

Options:
  --project PATH        Claude/Codex가 작업할 실제 repository 절대경로 (필수)
  --codex-config PATH   Codex config 경로 (기본: $CODEX_HOME/config.toml 또는 ~/.codex/config.toml)
  --skill-scope SCOPE   project 또는 user (기본: project)
  --only codex-bg       Claude -> Codex skill만 설치/update (MCP config는 바꾸지 않음)
  --dry-run             파일을 바꾸지 않고 계획만 출력
  -h, --help            도움말

기본 설치는 skill과 claude-coder MCP를 함께 설정한다.
이 installer는 CLI를 설치하거나 로그인하지 않는다.
기존 claude-coder MCP table이 있으면 덮어쓰지 않고 중단한다.
EOF
}

die() {
  local status="$1"
  shift
  echo "$*" >&2
  exit "$status"
}

require_option_value() {
  local option="$1"
  if (($# < 2)) || [[ -z "${2:-}" ]] || [[ "${2:0:1}" == "-" ]]; then
    echo "$option requires a value" >&2
    usage >&2
    exit 64
  fi
}

PROJECT=""
HOME_DIR="${HOME:-}"
if [[ -z "$HOME_DIR" ]]; then
  die 64 "HOME is required"
fi
if [[ -d "$HOME_DIR" ]]; then
  HOME_DIR="$(cd -- "$HOME_DIR" && pwd -P)"
fi
if [[ -n "${CODEX_HOME:-}" ]]; then
  CODEX_CONFIG="${CODEX_HOME}/config.toml"
else
  CODEX_CONFIG="$HOME_DIR/.codex/config.toml"
fi
SKILL_SCOPE="project"
ONLY=""
DRY_RUN=0

while (($#)); do
  case "$1" in
    --project)
      require_option_value "$@"
      PROJECT="$2"
      shift 2
      ;;
    --codex-config)
      require_option_value "$@"
      CODEX_CONFIG="$2"
      shift 2
      ;;
    --skill-scope)
      require_option_value "$@"
      SKILL_SCOPE="$2"
      shift 2
      ;;
    --only)
      require_option_value "$@"
      ONLY="$2"
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
if [[ "$PROJECT" == *$'\n'* || "$PROJECT" == *$'\r'* || "$PROJECT" == *$'\t'* ]]; then
  echo "path contains a newline, carriage return, or tab and cannot be used as an installer path: $PROJECT" >&2
  exit 64
fi
if [[ ! -d "$PROJECT" ]]; then
  echo "project directory does not exist: $PROJECT" >&2
  exit 66
fi
PROJECT="$(cd -- "$PROJECT" && pwd -P)"
if [[ "$SKILL_SCOPE" != "project" && "$SKILL_SCOPE" != "user" ]]; then
  echo "--skill-scope must be project or user" >&2
  exit 64
fi
if [[ -n "$ONLY" && "$ONLY" != "codex-bg" ]]; then
  echo "--only must be codex-bg" >&2
  exit 64
fi

MODE="both"
if [[ "$ONLY" == "codex-bg" ]]; then
  MODE="only"
fi

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MCP_WRAPPER="$ROOT/bridge/claude-coder-mcp/run.sh"
SKILL_SOURCE_DIR="$ROOT/skills/codex-bg"
SKILL_SOURCE="$SKILL_SOURCE_DIR/SKILL.md"
SKILL_RUN_SOURCE="$SKILL_SOURCE_DIR/scripts/run.mjs"

if [[ "$SKILL_SCOPE" == "project" ]]; then
  SKILL_DEST_DIR="$PROJECT/.claude/skills/codex-bg"
  SKILL_ROOT="$PROJECT"
else
  SKILL_DEST_DIR="$HOME_DIR/.claude/skills/codex-bg"
  SKILL_ROOT="$HOME_DIR"
fi
SKILL_DEST="$SKILL_DEST_DIR/SKILL.md"
STATE_DIR="$HOME_DIR/.local/state/claude-codex-bridge"

NODE_BIN="$(command -v node || true)"
CODEX_BIN="$(command -v codex || true)"
CLAUDE_BIN=""
PYTHON_BIN=""
if [[ "$MODE" == "both" ]]; then
  CLAUDE_BIN="$(command -v claude || true)"
  PYTHON_BIN="$(command -v python3 || true)"
fi

require_executable() {
  local name="$1"
  local path="$2"
  if [[ -z "$path" || ! -x "$path" ]]; then
    echo "$name executable not found inside WSL PATH" >&2
    exit 127
  fi
}

require_executable node "$NODE_BIN"
require_executable codex "$CODEX_BIN"
if [[ "$MODE" == "both" ]]; then
  require_executable claude "$CLAUDE_BIN"
  require_executable python3 "$PYTHON_BIN"
fi

if [[ ! -d "$SKILL_SOURCE_DIR" || ! -f "$SKILL_SOURCE" || ! -f "$SKILL_RUN_SOURCE" ]]; then
  echo "skill installer assets are missing; run this script from a complete poketball1/public clone" >&2
  exit 66
fi
if [[ -L "$SKILL_SOURCE_DIR" || -L "$SKILL_SOURCE" || -L "$SKILL_RUN_SOURCE" ]]; then
  echo "skill installer assets may not be symbolic links: $SKILL_SOURCE_DIR" >&2
  exit 66
fi

mapfile -d '' SKILL_RUNTIME_FILES < <(
  find "$SKILL_SOURCE_DIR" \
    \( -type d \( -name tests -o -name test \) -prune \) -o \
    \( -type f ! -name '*.test.*' ! -name '*.spec.*' -print0 \)
)
if (( ${#SKILL_RUNTIME_FILES[@]} == 0 )); then
  echo "skill runtime assets are missing: $SKILL_SOURCE_DIR" >&2
  exit 66
fi
SKILL_RUNTIME_HAS_RUN=0
for skill_file in "${SKILL_RUNTIME_FILES[@]}"; do
  if [[ "$skill_file" == "$SKILL_RUN_SOURCE" ]]; then
    SKILL_RUNTIME_HAS_RUN=1
  fi
  if [[ ! -r "$skill_file" ]]; then
    echo "skill source is not readable: $skill_file" >&2
    exit 66
  fi
done
if (( ! SKILL_RUNTIME_HAS_RUN )); then
  echo "skill runtime entry is missing from the runtime asset set: $SKILL_RUN_SOURCE" >&2
  exit 66
fi

if [[ "$MODE" == "both" ]]; then
  mapfile -d '' BRIDGE_MJS_FILES < <(find "$ROOT/bridge" -type f -name '*.mjs' -print0)
  REQUIRED_BRIDGE_FILES=(
    "$MCP_WRAPPER"
    "$ROOT/bridge/claude-coder-mcp/server.mjs"
    "$ROOT/bridge/mcp-stdio-supervisor.mjs"
    "$ROOT/bridge/lib/lifecycle-audit.mjs"
  )
  for bridge_file in "${REQUIRED_BRIDGE_FILES[@]}"; do
    if [[ ! -f "$bridge_file" || ! -r "$bridge_file" ]]; then
      echo "installer assets are missing: $bridge_file" >&2
      exit 66
    fi
  done
  if [[ ! -x "$MCP_WRAPPER" ]]; then
    echo "MCP wrapper is not executable: $MCP_WRAPPER" >&2
    exit 66
  fi
fi

check_node_syntax() {
  local source_file="$1"
  if ! "$NODE_BIN" --check "$source_file"; then
    echo "source syntax check failed: $source_file" >&2
    exit 65
  fi
}

for skill_file in "${SKILL_RUNTIME_FILES[@]}"; do
  if [[ "$skill_file" == *.mjs ]]; then
    check_node_syntax "$skill_file"
  fi
done

if [[ "$MODE" == "both" ]]; then
  if ! bash -n "$MCP_WRAPPER"; then
    echo "source syntax check failed: $MCP_WRAPPER" >&2
    exit 65
  fi
  for bridge_file in "${BRIDGE_MJS_FILES[@]}"; do
    check_node_syntax "$bridge_file"
  done
fi

check_parent_paths() {
  local target="$1"
  local parent
  parent="$(dirname -- "$target")"
  while [[ "$parent" != "/" ]]; do
    if [[ -e "$parent" && ! -d "$parent" ]]; then
      echo "path component is not a directory: $parent" >&2
      exit 73
    fi
    parent="$(dirname -- "$parent")"
  done
}

check_no_symlink_below_root() {
  local root="$1"
  local target="$2"
  local label="${3:-skill target}"
  local relative current component candidate
  local -a components

  root="${root%/}"
  [[ -n "$root" ]] || root="/"
  if [[ "$root" == "/" ]]; then
    if [[ "$target" != /* ]]; then
      echo "$label is outside its root: $target" >&2
      exit 73
    fi
    relative="${target#/}"
  else
    case "$target" in
      "$root") relative="" ;;
      "$root"/*) relative="${target#"$root"/}" ;;
      *)
        echo "$label is outside its root: $target" >&2
        exit 73
        ;;
    esac
  fi

  current="$root"
  IFS='/' read -r -a components <<< "$relative"
  for component in "${components[@]}"; do
    [[ -z "$component" || "$component" == "." ]] && continue
    if [[ "$component" == ".." ]]; then
      echo "$label contains a parent traversal: $target" >&2
      exit 73
    fi
    if [[ "$current" == "/" ]]; then
      candidate="/$component"
    else
      candidate="$current/$component"
    fi
    if [[ -L "$candidate" ]]; then
      echo "$label path contains a symbolic link; refusing to follow: $candidate" >&2
      exit 73
    fi
    current="$candidate"
  done
}

validate_config_target() {
  if [[ "$CODEX_CONFIG" != /* ]]; then
    echo "--codex-config must be an absolute WSL/Linux path: $CODEX_CONFIG" >&2
    exit 64
  fi
  check_no_symlink_below_root / "$CODEX_CONFIG" "Codex config"
  if [[ -L "$CODEX_CONFIG" ]]; then
    echo "Codex config path is a symbolic link; refusing to follow: $CODEX_CONFIG" >&2
    exit 73
  fi
  if [[ -e "$CODEX_CONFIG" && ! -f "$CODEX_CONFIG" ]]; then
    echo "Codex config path is not a regular file: $CODEX_CONFIG" >&2
    exit 73
  fi
  check_parent_paths "$CODEX_CONFIG"
}

validate_state_target() {
  check_no_symlink_below_root "$HOME_DIR" "$STATE_DIR" "state directory"
  if [[ -L "$STATE_DIR" ]]; then
    echo "state directory is a symbolic link; refusing to follow: $STATE_DIR" >&2
    exit 73
  fi
  if [[ -e "$STATE_DIR" && ! -d "$STATE_DIR" ]]; then
    echo "state directory is not a directory: $STATE_DIR" >&2
    exit 73
  fi
  check_parent_paths "$STATE_DIR"
}

validate_skill_targets() {
  local skill_file relative_file destination_file
  check_no_symlink_below_root "$SKILL_ROOT" "$SKILL_DEST_DIR"
  if [[ -e "$SKILL_DEST_DIR" && ! -d "$SKILL_DEST_DIR" ]]; then
    echo "skill target path is not a directory: $SKILL_DEST_DIR" >&2
    exit 73
  fi
  for skill_file in "${SKILL_RUNTIME_FILES[@]}"; do
    relative_file="${skill_file#"$SKILL_SOURCE_DIR"/}"
    destination_file="$SKILL_DEST_DIR/$relative_file"
    check_no_symlink_below_root "$SKILL_ROOT" "$destination_file"
    if [[ -L "$destination_file" ]]; then
      echo "skill target path contains a symbolic link; refusing to follow: $destination_file" >&2
      exit 73
    fi
    if [[ -e "$destination_file" && ! -f "$destination_file" ]]; then
      echo "skill target is not a regular file: $destination_file" >&2
      exit 73
    fi
    check_parent_paths "$destination_file"
  done
}

if [[ "$MODE" == "both" ]]; then
  validate_config_target
fi
validate_skill_targets
if [[ "$MODE" == "both" ]]; then
  validate_state_target
fi

toml_control_path() {
  local value="$1"
  [[ "$value" == *$'\n'* || "$value" == *$'\r'* || "$value" == *$'\t'* ]]
}

toml_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '%s' "$value"
}

CONFIG_BLOCK=""
if [[ "$MODE" == "both" ]]; then
  SAFE_PATH="$(dirname -- "$CLAUDE_BIN"):$(dirname -- "$NODE_BIN"):/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  TOML_PATHS=(
    "$MCP_WRAPPER"
    "$NODE_BIN"
    "$CLAUDE_BIN"
    "$PROJECT"
    "$CODEX_CONFIG"
    "$STATE_DIR"
    "$SAFE_PATH"
  )
  for toml_path in "${TOML_PATHS[@]}"; do
    if toml_control_path "$toml_path"; then
      echo "path contains a newline, carriage return, or tab and cannot be written to TOML: $toml_path" >&2
      exit 64
    fi
  done

  Q_WRAPPER="$(toml_escape "$MCP_WRAPPER")"
  Q_NODE="$(toml_escape "$NODE_BIN")"
  Q_CLAUDE="$(toml_escape "$CLAUDE_BIN")"
  Q_PROJECT="$(toml_escape "$PROJECT")"
  Q_STATE="$(toml_escape "$STATE_DIR")"
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
fi

validate_toml_config() {
  "$PYTHON_BIN" - "$CODEX_CONFIG" "$CONFIG_BLOCK" <<'PY'
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    print("default installation requires Python 3.11+ with stdlib tomllib", file=sys.stderr)
    raise SystemExit(66)

try:
    import tomllib
except ModuleNotFoundError:
    print("default installation requires Python 3.11+ with stdlib tomllib", file=sys.stderr)
    raise SystemExit(66)

config_path = Path(sys.argv[1])
appendix = sys.argv[2]
if config_path.is_symlink():
    print(f"Codex config path is a symbolic link; refusing to follow: {config_path}", file=sys.stderr)
    raise SystemExit(73)
if config_path.exists() and not config_path.is_file():
    print(f"Codex config path is not a regular file: {config_path}", file=sys.stderr)
    raise SystemExit(73)

if config_path.exists():
    try:
        current = config_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"existing Codex config is not UTF-8 TOML: {config_path}: {exc}", file=sys.stderr)
        raise SystemExit(65)
    except OSError as exc:
        print(f"cannot read existing Codex config: {config_path}: {exc}", file=sys.stderr)
        raise SystemExit(65)
else:
    current = ""

try:
    current_data = tomllib.loads(current)
except tomllib.TOMLDecodeError as exc:
    print(f"existing Codex config is invalid TOML: {config_path}: {exc}", file=sys.stderr)
    raise SystemExit(65)

mcp_servers = current_data.get("mcp_servers")
if isinstance(mcp_servers, dict) and "claude-coder" in mcp_servers:
    print(f"existing claude-coder MCP config found: {config_path}", file=sys.stderr)
    print("nothing was changed; remove or rename that entry after reviewing it, then rerun; use --only codex-bg to update the skill without changing MCP config", file=sys.stderr)
    raise SystemExit(73)

try:
    tomllib.loads(current + appendix + "\n")
except tomllib.TOMLDecodeError as exc:
    print(f"Codex config cannot be extended with claude-coder MCP settings: {config_path}: {exc}", file=sys.stderr)
    raise SystemExit(65)
PY
}

FLOCK_BIN=""
REALPATH_BIN=""
SHA256SUM_BIN=""
CUT_BIN=""
if [[ "$MODE" == "both" ]] || (( ! DRY_RUN )); then
  FLOCK_BIN="$(command -v flock || true)"
  REALPATH_BIN="$(command -v realpath || true)"
  SHA256SUM_BIN="$(command -v sha256sum || true)"
  CUT_BIN="$(command -v cut || true)"
  require_executable realpath "$REALPATH_BIN"
  require_executable sha256sum "$SHA256SUM_BIN"
  require_executable cut "$CUT_BIN"
  if (( ! DRY_RUN )); then
    require_executable flock "$FLOCK_BIN"
  fi
fi

LOCK_WAIT_SECONDS=30
# Keep this root independent of XDG_RUNTIME_DIR and TMPDIR so every invocation
# for this Unix user shares the same coordination namespace.
LOCK_DIR="/tmp/claude-codex-install-$UID"
SKILL_LOCK_KEY=""
CONFIG_LOCK_KEY=""
SKILL_LOCK_FD=""
CONFIG_LOCK_FD=""

canonical_path() {
  "$REALPATH_BIN" -m -- "$1"
}

check_lock_location() {
  local lock_canonical skill_canonical
  check_no_symlink_below_root / "$LOCK_DIR" "installer coordination directory"
  lock_canonical="$(canonical_path "$LOCK_DIR")"
  skill_canonical="$(canonical_path "$SKILL_DEST_DIR")"
  case "$lock_canonical" in
    "$skill_canonical"|"$skill_canonical"/*)
      die 73 "installer coordination directory overlaps the skill target: $LOCK_DIR"
      ;;
  esac
  case "$skill_canonical" in
    "$lock_canonical"|"$lock_canonical"/*)
      die 73 "skill target overlaps the installer coordination directory: $SKILL_DEST_DIR"
      ;;
  esac
}

paths_overlap() {
  local first="$1"
  local second="$2"
  [[ "$first" == "$second" || "$first" == "$second"/* || "$second" == "$first"/* ]]
}

validate_target_layout() {
  [[ "$MODE" == "both" ]] || return 0

  local config_canonical runtime_dir runtime_canonical
  config_canonical="$(canonical_path "$CODEX_CONFIG")"
  for runtime_dir in "$SKILL_DEST_DIR" "$STATE_DIR" "$LOCK_DIR"; do
    runtime_canonical="$(canonical_path "$runtime_dir")"
    if paths_overlap "$config_canonical" "$runtime_canonical"; then
      die 73 "Codex config path overlaps installer-owned runtime directory: $CODEX_CONFIG"
    fi
  done
}

ensure_lock_dir() {
  local owner mode
  umask 077
  check_lock_location
  if [[ -L "$LOCK_DIR" ]]; then
    die 73 "installer coordination directory is a symbolic link; refusing to follow: $LOCK_DIR"
  fi
  if [[ -e "$LOCK_DIR" && ! -d "$LOCK_DIR" ]]; then
    die 73 "installer coordination path is not a directory: $LOCK_DIR"
  fi
  if [[ ! -e "$LOCK_DIR" ]]; then
    mkdir -p -- "$LOCK_DIR" || die 73 "cannot create installer coordination directory: $LOCK_DIR"
    chmod 700 -- "$LOCK_DIR" || die 73 "cannot secure installer coordination directory: $LOCK_DIR"
  fi
  if [[ -L "$LOCK_DIR" ]]; then
    die 73 "installer coordination directory became a symbolic link; refusing to follow: $LOCK_DIR"
  fi
  owner="$(stat -c '%u' -- "$LOCK_DIR")"
  mode="$(stat -c '%a' -- "$LOCK_DIR")"
  if [[ "$owner" != "$UID" || "$mode" != "700" ]]; then
    die 73 "installer coordination directory must be owned by this user with mode 700: $LOCK_DIR"
  fi
}

release_locks() {
  if [[ "$CONFIG_LOCK_FD" =~ ^[0-9]+$ ]]; then
    "$FLOCK_BIN" -u "$CONFIG_LOCK_FD" 2>/dev/null || true
    eval "exec ${CONFIG_LOCK_FD}>&-" 2>/dev/null || true
    CONFIG_LOCK_FD=""
  fi
  if [[ "$SKILL_LOCK_FD" =~ ^[0-9]+$ ]]; then
    "$FLOCK_BIN" -u "$SKILL_LOCK_FD" 2>/dev/null || true
    eval "exec ${SKILL_LOCK_FD}>&-" 2>/dev/null || true
    SKILL_LOCK_FD=""
  fi
}

acquire_lock() {
  local key="$1"
  local slot="$2"
  local digest lock_file fd
  digest="$(printf '%s' "$key" | "$SHA256SUM_BIN" | "$CUT_BIN" -d ' ' -f1)"
  if [[ -z "$digest" ]]; then
    die 73 "cannot derive installer coordination lock for: $key"
  fi
  lock_file="$LOCK_DIR/$digest.lock"
  if [[ -L "$lock_file" ]]; then
    die 73 "installer coordination lock is a symbolic link; refusing to follow: $lock_file"
  fi
  if ! exec {fd}>>"$lock_file"; then
    die 73 "cannot open installer coordination lock: $lock_file"
  fi
  chmod 600 -- "$lock_file" || die 73 "cannot secure installer coordination lock: $lock_file"
  if ! "$FLOCK_BIN" -w "$LOCK_WAIT_SECONDS" "$fd"; then
    eval "exec ${fd}>&-" 2>/dev/null || true
    die 75 "timed out waiting for installer coordination lock: $key"
  fi
  if [[ "$slot" == "skill" ]]; then
    SKILL_LOCK_FD="$fd"
  else
    CONFIG_LOCK_FD="$fd"
  fi
}

if [[ "$MODE" == "both" ]] || (( ! DRY_RUN )); then
  check_lock_location
fi
if [[ "$MODE" == "both" ]]; then
  validate_target_layout
  validate_toml_config
fi

echo "project:       $PROJECT"
if [[ "$MODE" == "both" ]]; then
  echo "codex config:  $CODEX_CONFIG"
else
  echo "codex config:  $CODEX_CONFIG (unchanged; --only codex-bg)"
fi
echo "skill target:  $SKILL_DEST"
if [[ "$MODE" == "both" ]]; then
  echo "MCP wrapper:   $MCP_WRAPPER"
fi
echo "state dir:     $STATE_DIR"

if ((DRY_RUN)); then
  printf '\n--- skill files that would be installed ---\n'
  for skill_file in "${SKILL_RUNTIME_FILES[@]}"; do
    relative_file="${skill_file#"$SKILL_SOURCE_DIR"/}"
    printf '%s -> %s\n' "$skill_file" "$SKILL_DEST_DIR/$relative_file"
  done
  if [[ "$MODE" == "both" ]]; then
    printf '\n--- config block that would be appended ---\n%s\n' "$CONFIG_BLOCK"
  else
    printf '\n--- Codex MCP config remains unchanged (--only codex-bg) ---\n'
  fi
  exit 0
fi

ensure_lock_dir
SKILL_LOCK_KEY="$(canonical_path "$SKILL_DEST_DIR")"
if [[ "$MODE" == "both" ]]; then
  CONFIG_LOCK_KEY="$(canonical_path "$CODEX_CONFIG")"
  if [[ "$SKILL_LOCK_KEY" == "$CONFIG_LOCK_KEY" ]]; then
    die 73 "skill destination and Codex config must be different paths"
  fi
fi
trap 'release_locks' EXIT
if [[ "$MODE" == "both" ]]; then
  if (LC_ALL=C; [[ "$SKILL_LOCK_KEY" < "$CONFIG_LOCK_KEY" ]]); then
    acquire_lock "$SKILL_LOCK_KEY" skill
    acquire_lock "$CONFIG_LOCK_KEY" config
  else
    acquire_lock "$CONFIG_LOCK_KEY" config
    acquire_lock "$SKILL_LOCK_KEY" skill
  fi
else
  acquire_lock "$SKILL_LOCK_KEY" skill
fi

# Paths and TOML may have changed while waiting for the coordination lock.
check_lock_location
if [[ "$MODE" == "both" ]]; then
  validate_config_target
fi
validate_skill_targets
if [[ "$MODE" == "both" ]]; then
  validate_state_target
  validate_target_layout
  validate_toml_config
fi

unique_backup_path() {
  local target="$1"
  local stamp suffix backup
  stamp="$(date +%Y%m%d-%H%M%S)"
  backup="$target.bak.$stamp"
  suffix=1
  while [[ -e "$backup" || -L "$backup" ]]; do
    backup="$target.bak.$stamp.$suffix"
    suffix=$((suffix + 1))
  done
  printf '%s' "$backup"
}

skill_files_equal() {
  local source_file="$1"
  local destination_file="$2"
  cmp -s "$source_file" "$destination_file" || return 1
  [[ "$(stat -c '%a' -- "$source_file")" == "$(stat -c '%a' -- "$destination_file")" ]]
}

backup_and_report() {
  local target="$1"
  local backup
  backup="$(unique_backup_path "$target")"
  cp -p -- "$target" "$backup"
  printf '%s' "$backup"
}

install_skill_runtime() {
  local skill_file relative_file destination_file backup
  mkdir -p -- "$SKILL_DEST_DIR"
  for skill_file in "${SKILL_RUNTIME_FILES[@]}"; do
    relative_file="${skill_file#"$SKILL_SOURCE_DIR"/}"
    destination_file="$SKILL_DEST_DIR/$relative_file"
    mkdir -p -- "$(dirname -- "$destination_file")"
    if [[ -f "$destination_file" ]]; then
      if skill_files_equal "$skill_file" "$destination_file"; then
        continue
      fi
      backup="$(backup_and_report "$destination_file")"
      echo "skill backup:  $backup"
    fi
    cp -p -- "$skill_file" "$destination_file"
  done
}

write_mcp_config() {
  local backup tmp_config
  mkdir -p -- "$(dirname -- "$CODEX_CONFIG")"
  if [[ -f "$CODEX_CONFIG" ]]; then
    backup="$(backup_and_report "$CODEX_CONFIG")"
    echo "backup:        $backup"
  fi

  tmp_config="$(mktemp "$CODEX_CONFIG.tmp.XXXXXX")"
  trap 'if [[ -n "${tmp_config:-}" ]]; then rm -f -- "$tmp_config"; fi' EXIT
  if [[ -f "$CODEX_CONFIG" ]]; then
    cp -- "$CODEX_CONFIG" "$tmp_config"
  fi
  printf '%s\n' "$CONFIG_BLOCK" >> "$tmp_config"
  chmod 600 -- "$tmp_config"
  mv -- "$tmp_config" "$CODEX_CONFIG"
  trap - EXIT
}

if [[ "$MODE" == "both" ]]; then
  mkdir -p -- "$STATE_DIR"
  chmod 700 -- "$STATE_DIR"
  install_skill_runtime
  write_mcp_config
else
  install_skill_runtime
fi

echo
echo "installed successfully"
if [[ "$MODE" == "only" ]]; then
  echo "skill installed/updated: codex-bg"
  echo "Codex MCP config was not changed"
  exit 0
fi
echo "1) close every running Codex process"
echo "2) start Codex again inside: $PROJECT"
echo "3) run: codex mcp get claude-coder"
echo "4) ask Codex to call claude_health"
echo "5) in a new Claude Code session, invoke /codex-bg for the Claude -> Codex smoke test"
