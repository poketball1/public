#!/usr/bin/env bash
# keepwarm-birth.sh — SessionStart hook: arm every newborn session.
#
# REGISTERED AS
#   event   SessionStart
#   matcher "startup|resume|clear"
#   async   true
#   timeout 15
#
# WHY THOSE THREE SOURCES AND NOT THE OTHER TWO
#   startup  a brand-new session: obviously unarmed.
#   clear    /clear MINTS A NEW SESSION ID. The old arm is not inherited — it
#            simply stops seeing its sid in the registry and self-cleans two
#            ticks later. Without this matcher, every /clear opened a permanent
#            coverage hole (measured: sessions 5 days past a /clear, unarmed).
#   resume   `--resume` is a NEW PROCESS. There is no arm to inherit.
#   compact  EXCLUDED: same sid, same process, the arm survives. Arming again
#            would only churn.
#   fork     EXCLUDED, conservatively. Revisit if forked sessions turn out to
#            want a budget.
#
# WHAT THIS SCRIPT DECIDES: NOTHING.
# It forwards a session id and exits. Whether to arm — opt-out, model policy,
# budget inheritance, warm margin, an existing live arm — is decided by the arm
# module, which owns the state file and the ledger. The only thing filtered here
# is input that is not a session at all. Keeping the rules in one place is what
# stops the shell and the module from disagreeing about who is armed.
#
# ALWAYS exit 0. keep-warm is a fail-open side effect; it must never block a
# session from starting.

set -uo pipefail

ARM_CTL="${KEEPWARM_CTL:-$HOME/keepwarm/scripts/keepwarm_ctl.py}"
PYTHON_BIN="${KEEPWARM_PYTHON:-$(command -v python3 || true)}"
LOG="${KEEPWARM_HOOK_LOG:-$HOME/.keepwarm/hook-events.jsonl}"

# Read stdin in full, FIRST. A hook that pipes stdin into a heredoc later can
# lose it; read it once into a variable and work from there.
INPUT=$(cat)

log_event() {
    local result="$1" detail="$2"
    mkdir -p -- "$(dirname -- "$LOG")" 2>/dev/null || return 0
    printf '{"ts":"%s","hook":"keepwarm-birth","sid":"%s","result":"%s","detail":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${SID:-}" "$result" "${detail//\"/\'}" \
        >> "$LOG" 2>/dev/null || true
}

# The hook payload. Only two fields are used.
#   session_id      the sid to arm
#   transcript_path where the session's JSONL lives
# `transcript_path` is load-bearing during the birth window: the registry row
# lands ~2 s into session life, and until it does there is no other way to
# resolve the transcript. Drop it and every newborn is skipped.
if command -v jq >/dev/null 2>&1; then
    SID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
    TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
else
    SID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    TRANSCRIPT=$(printf '%s' "$INPUT" | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
fi

# --- the only filtering this script does: "is this even a session?" ---------

[[ -n "${SID:-}" ]] || { log_event skipped no-sid; exit 0; }

# A sub-agent has no registry row and no prompt cache of its own.
case "$SID" in
    agent-*) log_event skipped agent-sid; exit 0 ;;
esac
case "${TRANSCRIPT:-}" in
    */subagents/*) log_event skipped subagent-transcript; exit 0 ;;
esac

[[ -n "$PYTHON_BIN" && -x "$PYTHON_BIN" ]] || { log_event skipped python-missing; exit 0; }
[[ -f "$ARM_CTL" ]] || { log_event skipped ctl-missing; exit 0; }

# --- hand off ---------------------------------------------------------------
#
# `auto --source birth` is the hook-facing entry point. It applies the
# inheritance rules (opt-out, exhausted budget, a live incumbent, remaining
# budget) and, if the answer is "arm", spawns a NATAL daemon.
#
# NATAL means the daemon starts in a non-firing observation state. A newborn
# transcript holds harness metadata only — no assistant row (so no model) and no
# timestamped row (so the clock would fall through to file mtime). Firing on an
# mtime clock is exactly the cold-reheat accident this whole thing exists to
# prevent, so a natal daemon does not enter the firing machine AT ALL until both
# kinds of evidence exist. Structural guarantee, not a threshold. Waiting costs
# nothing: no budget is spent while natal.
#
# `setsid nohup ... &` detaches immediately: the hook returns in milliseconds
# and the 15 s timeout is never the binding constraint. It also means the spawn
# survives the session-start shell, and never receives its signals.

ARGS=(auto --sid "$SID" --source birth)
[[ -n "${TRANSCRIPT:-}" ]] && ARGS+=(--transcript "$TRANSCRIPT")

setsid nohup "$PYTHON_BIN" "$ARM_CTL" "${ARGS[@]}" </dev/null >/dev/null 2>&1 &
disown 2>/dev/null || true
log_event ok "dispatched birth sid=${SID:0:8}"

exit 0
