#!/usr/bin/env bash
# keepwarm-rearm.sh — Stop hook: self-heal this session's keep-warm coverage.
#
# REGISTERED AS
#   event   Stop       (fires every time the assistant finishes a turn)
#   async   true
#
# WHY THE STOP EVENT IS THE RIGHT CADENCE
#   A daemon can die between arming and the next thing a human looks at: a WSL
#   shutdown, a reboot, a stray kill, an OOM. Nothing else notices. Stop fires
#   on every turn of every live session, which makes it the only zero-cost,
#   zero-infrastructure heartbeat available — no cron, no supervisor, no second
#   resident process. The common answer is "a live arm already owns this sid",
#   which costs a couple of stat calls.
#
#   There is deliberately NO cooldown. The Stop event IS the cadence, and a
#   positive cooldown can skip exactly the final self-heal turn after a daemon
#   dies.
#
# WHAT THIS SCRIPT DECIDES: NOTHING.
# It validates the sid, takes a per-sid lock, and calls the control script. No
# budget arithmetic, no identity comparison, no snapshot, no ledger row lives
# here. That boundary is worth enforcing mechanically rather than by good
# intentions: a grep of this file for the arm-state vocabulary must come back
# empty, and the hook test does exactly that grep.
#
# ALWAYS exit 0, and discard all output: a hook that fails must not disturb the
# turn that triggered it.

INPUT=$(cat 2>/dev/null || true)
exec >/dev/null 2>&1

# Registered directly as a Stop hook, the sid arrives on stdin. If you instead
# fan out Stop work from one dispatcher script (which is what we do, so that ten
# independent tasks share a single hook entry), export HOOK_SESSION_ID there and
# this falls through to it.
SID="${HOOK_SESSION_ID:-}"
if [[ -z "$SID" && -n "$INPUT" ]]; then
    if command -v jq >/dev/null 2>&1; then
        SID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
    else
        SID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    fi
fi

# Validate before the value ever reaches argv. This regex rejects traversal
# shapes (a leading dot or slash) and anything with whitespace, which is what
# stops a malformed sid from turning into an unexpected path or an extra
# argument.
[[ "$SID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || exit 0

PYTHON_BIN="${KEEPWARM_PYTHON:-$(command -v python3)}"
ARM_CTL="${KEEPWARM_CTL:-$HOME/keepwarm/scripts/keepwarm_ctl.py}"
LOCK_DIR="${KEEPWARM_REARM_LOCK_DIR:-/tmp/keepwarm-rearm}"

[[ -n "$PYTHON_BIN" && -x "$PYTHON_BIN" && -f "$ARM_CTL" ]] || exit 0
mkdir -p -- "$LOCK_DIR" || exit 0

# Per-sid, NON-BLOCKING lock. Two Stop hooks for the same session must not both
# decide; a held lock is a silent no-op rather than a queue. Per-sid scope
# matters: a busy session must never block a peer's self-heal.
(
    flock -n 9 || exit 0
    "$PYTHON_BIN" "$ARM_CTL" auto --sid "$SID" --source rearm || true
) 9>"$LOCK_DIR/$SID.lock" || true

exit 0
