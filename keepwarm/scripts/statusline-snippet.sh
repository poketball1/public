#!/usr/bin/env bash
# statusline-snippet.sh — render the keep-warm segment: ♨ n/N, ♨ n/∞, ♨ n/N⏸
#
# Drop this into your statusLine command script. Claude Code pipes a JSON blob
# on stdin; `.session_id` is the only field we need.
#
# THE STATUSLINE IS AN OBSERVER. It reads the serialized state file and renders
# it. It never decides whether an arm is alive, never re-judges the model, never
# writes anything. Two consequences worth stating:
#
#   - `budget_unbounded` is a BOOLEAN the daemon derived and wrote. The
#     statusline does not pattern-match the model name. One owner for the model
#     policy means the glyph can never disagree with the daemon's own budget
#     accounting.
#
#   - Staleness is checked by IDENTITY, not by a timestamp. There is no TTL and
#     no mtime comparison anywhere below. We render only while the recorded
#     arm_id still owns the recorded pid, because a PID alone gets reused and a
#     reused PID would make a dead arm look armed forever.
#
# Everything fails open to an empty string: a parse error, a dead pid, an
# identity mismatch, a missing field — all render nothing rather than a wrong
# glyph.

KEEPWARM_STATE_DIR="${KEEPWARM_STATE_DIR:-$HOME/.keepwarm/state}"
KEEPWARM_PROC_ROOT="${KEEPWARM_PROC_ROOT:-/proc}"

# Renders the segment for a session id, or nothing.
keepwarm_segment() {
    local sid="$1"
    local state pid arm_id confirmed budget unbounded status suffix cmdline

    [[ "$sid" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || return 0
    state="$KEEPWARM_STATE_DIR/$sid.state.json"
    [[ -f "$state" ]] || return 0
    command -v jq >/dev/null 2>&1 || return 0

    # One jq pass, with every field validated inside the `select`. An invalid
    # field means the whole row is rejected — a half-read state file must not
    # produce a half-right glyph.
    #
    # NOTE the empty-string field is LAST on purpose: `IFS=$'\t' read` collapses
    # consecutive tabs, so an empty field in the middle silently shifts every
    # later field one position left.
    local fields
    fields=$(jq -r --arg sid "$sid" '
        select(
          (.status == "armed" or .status == "suspended")
          and .sid == $sid
          and (.pid | type) == "number" and .pid > 0
          and (.arm_id | type) == "string" and (.arm_id | length) > 0
          and (.confirmed_count | type) == "number" and .confirmed_count >= 0
          and (.count_budget | type) == "number" and .count_budget > 0
        )
        | [ .status,
            (.pid | tostring),
            .arm_id,
            (.confirmed_count | tostring),
            (.count_budget | tostring),
            (if .budget_unbounded == true then "1" else "0" end),
            (if .status == "armed" then "" else "⏸" end) ]
        | @tsv
    ' "$state" 2>/dev/null) || return 0

    [[ -n "$fields" && "$fields" != *$'\n'* ]] || return 0
    IFS=$'\t' read -r status pid arm_id confirmed budget unbounded suffix <<< "$fields"

    # Identity check. A live pid is necessary but not sufficient.
    [[ -d "$KEEPWARM_PROC_ROOT/$pid" ]] || return 0
    cmdline=$(tr '\0' ' ' < "$KEEPWARM_PROC_ROOT/$pid/cmdline" 2>/dev/null) || return 0
    [[ "$cmdline" == *"$arm_id"* && "$cmdline" == *"$sid"* ]] || return 0

    if [[ "$unbounded" == "1" ]]; then
        printf ' | ♨ %s/∞%s' "$confirmed" "$suffix"
    else
        printf ' | ♨ %s/%s%s' "$confirmed" "$budget" "$suffix"
    fi
}

# --- standalone use ---------------------------------------------------------
# If this file is executed rather than sourced, read the statusline JSON from
# stdin and print just the segment.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    input=$(cat)
    if command -v jq >/dev/null 2>&1; then
        sid=$(printf '%s' "$input" | jq -r '.session_id // empty')
    else
        sid=$(printf '%s' "$input" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    fi
    keepwarm_segment "$sid"
    echo
fi

# --- reading the glyph ------------------------------------------------------
#   ♨ 3/24    armed, 3 of 24 warm turns spent (retries are not counted)
#   ♨ 3/∞     armed on an unbounded model — stays warm until you say off
#   ♨ 0/24⏸   SUSPENDED: the last warm turn got a 0/0 answer (a limit or an
#             overload). The budget is intact, the daemon is alive, and it will
#             resume on its own once the model answers normally AND the fire
#             window is satisfied again.
#   (nothing)  no arm, a terminal arm, or an identity mismatch.
#
# The two suspension sub-states (`suspended_limit` vs `suspended_resume_wait`)
# are deliberately NOT distinguished here — one glyph. Those labels live in the
# state file and in the sweep report, where a reader can afford a word. A
# statusline that grows a vocabulary is a statusline nobody reads.
