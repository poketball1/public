#!/usr/bin/env bash
# keepwarm-asyncrewake.sh — hook-only keep-warm carrier (no daemon, no relay).
#
# Register on UserPromptSubmit with  "async": true, "asyncRewake": true, "timeout": 4200.
# Every user prompt (typed by a human, or the wake row this script itself produces)
# spawns one watcher process. A watcher:
#   * polls the transcript every TICK_SEC and computes the HONEST cache clock —
#     minutes since the last non-sidechain assistant row with positive cache usage
#     (user rows and 0/0 error rows never advance it);
#   * exits 0 silently when it is SUPERSEDED (a newer user row appeared, so a newer
#     watcher exists — the harness does not dedupe async hooks, we must), when the
#     cache is already COLD (never reheat), when the budget is exhausted or the
#     session opted out, or when no clock can be read;
#   * exits 2 exactly once when the clock enters [FIRE_AT, COLD_AT). Exit 2 from an
#     asyncRewake hook wakes Claude immediately while idle: the harness enqueues a
#     user row carrying this script's stderr, the model answers, the cache is
#     refreshed, and — because that wake is itself a UserPromptSubmit — a fresh
#     watcher is spawned. The loop sustains itself.
# Tested: 40 s / short-scale runs (see README §5.5). A full 50-minute cycle needs
# "timeout" >= COLD_AT + TICK (seconds) — asyncRewake hooks DO honor timeout.
set -u
FIRE_AT_MIN=${KW_FIRE_AT_MIN:-50}
COLD_AT_MIN=${KW_COLD_AT_MIN:-57}
TICK_SEC=${KW_TICK_SEC:-240}
BUDGET=${KW_BUDGET:-24}
TAIL_BYTES=${KW_TAIL_BYTES:-2097152}
MODEL_ALLOW=${KW_MODEL_ALLOW:-.}          # regex on message.model; "." = every model
STATE_DIR=${KW_STATE_DIR:-$HOME/.claude/keepwarm-hook}
INPUT=$(cat)
read -r SID TP < <(printf '%s' "$INPUT" | python3 -c '
import sys, json
d = json.load(sys.stdin)
print(d.get("session_id", ""), d.get("transcript_path", ""))' 2>/dev/null)
[ -n "${SID:-}" ] && [ -n "${TP:-}" ] || exit 0
mkdir -p "$STATE_DIR"
STATE="$STATE_DIR/$SID.json"
LEDGER="$STATE_DIR/ledger.jsonl"
START_EPOCH=$(date +%s.%N)   # sub-second: the answer to my own turn is always later than this
WATCHER="$$"
ledger() {  # event, extra-json-fields (comma-less; we add the separator)
  local extra=""
  [ -n "${2:-}" ] && extra=",$2"
  printf '{"ts":"%s","sid":"%s","watcher":%s,"event":"%s"%s}\n' \
    "$(date -Is)" "$SID" "$WATCHER" "$1" "$extra" >> "$LEDGER"
}
state_get() {  # key default
  python3 - "$STATE" "$1" "$2" <<'PY' 2>/dev/null
import sys, json, os
p, k, dflt = sys.argv[1:4]
try:
    print(json.load(open(p)).get(k, dflt))
except Exception:
    print(dflt)
PY
}
state_set() {  # key value(json literal)
  python3 - "$STATE" "$1" "$2" <<'PY' 2>/dev/null
import sys, json, os, tempfile
p, k, v = sys.argv[1:4]
try:
    d = json.load(open(p))
except Exception:
    d = {}
d[k] = json.loads(v)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p))
with os.fdopen(fd, "w") as f:
    json.dump(d, f)
os.replace(tmp, p)
PY
}
# clock: prints "idle_cache_min superseded answered model"
#   idle_cache_min  "-" when no cache-positive assistant row is in the tail
#   superseded      1 if a user row newer than this watcher's spawn exists (a newer watcher lives)
#   answered        1 if a cache-positive assistant row newer than this watcher's spawn exists —
#                   i.e. the turn that spawned me has been answered. A watcher spawned by a wake
#                   row sees the PREVIOUS turn's clock (still ≥ FIRE_AT) for a second or two; if it
#                   fired on that it would re-wake immediately and cascade until the budget is gone
#                   (observed 2026-09-15: seq 2..5 emitted within 2 s). Never fire before answered.
clock() {
  python3 - "$TP" "$TAIL_BYTES" "$START_EPOCH" <<'PY' 2>/dev/null
import sys, json, os
from datetime import datetime, timezone
tp, tail, start = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
last_cache = None; last_user = None; model = "-"
try:
    size = os.path.getsize(tp)
    with open(tp, "rb") as f:
        if size > tail:
            f.seek(size - tail); f.readline()          # drop the partial first line
        for raw in f:
            try:
                d = json.loads(raw)
            except Exception:
                continue
            if d.get("isSidechain"):
                continue
            t = d.get("type"); m = d.get("message") or {}
            if t == "user" and d.get("timestamp"):
                last_user = max(last_user or 0, ts(d["timestamp"]))
            elif t == "assistant":
                u = m.get("usage") or {}
                if (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) > 0 \
                        and d.get("timestamp"):
                    last_cache = max(last_cache or 0, ts(d["timestamp"]))
                    model = m.get("model") or model
except FileNotFoundError:
    pass
now = datetime.now(timezone.utc).timestamp()
idle = "-" if last_cache is None else f"{(now - last_cache) / 60:.2f}"
# a user row newer than this watcher's own spawn (+5 s slack) means a newer watcher exists
superseded = 1 if (last_user is not None and last_user > start + 5) else 0
# the turn that spawned me is answered once a cache-positive assistant row is newer than my spawn
answered = 1 if (last_cache is not None and last_cache > start) else 0
print(idle, superseded, answered, model)
PY
}
if [ "$(state_get opted_out false)" = "True" ]; then ledger skipped '"reason":"opted_out"'; exit 0; fi
ledger watcher_start "\"fire_at_min\":$FIRE_AT_MIN,\"cold_at_min\":$COLD_AT_MIN,\"tick_sec\":$TICK_SEC"
while :; do
  read -r IDLE SUPERSEDED ANSWERED MODEL < <(clock)
  if [ "${SUPERSEDED:-0}" = "1" ]; then ledger superseded ''; exit 0; fi
  if [ "${IDLE:-"-"}" = "-" ]; then
    # transcript not born yet or no cache row in the tail — keep observing, never fire;
    # but do not poll until the hook timeout if no answer ever comes (prompt errored)
    if [ "$(python3 -c "import time; print(1 if time.time() - $START_EPOCH >= $COLD_AT_MIN * 60 else 0)")" = "1" ]; then
      ledger skipped '"reason":"no_clock"'; exit 0
    fi
  elif [ "${ANSWERED:-0}" != "1" ]; then
    # my own turn is not answered yet (or it failed with 0/0 usage and the honest clock keeps
    # aging toward COLD_AT — the cold gate below still runs so a dead cache ends this watcher)
    cold=$(python3 -c "print(1 if $IDLE >= $COLD_AT_MIN else 0)")
    if [ "$cold" = "1" ]; then ledger cold_missed "\"idle_cache_min\":$IDLE,\"answered\":0"; exit 0; fi
  else
    if ! printf '%s' "$MODEL" | grep -Eq "$MODEL_ALLOW"; then ledger skipped "\"reason\":\"model_ineligible\",\"model\":\"$MODEL\""; exit 0; fi
    cold=$(python3 -c "print(1 if $IDLE >= $COLD_AT_MIN else 0)")
    due=$(python3 -c "print(1 if $IDLE >= $FIRE_AT_MIN else 0)")
    if [ "$cold" = "1" ]; then ledger cold_missed "\"idle_cache_min\":$IDLE"; exit 0; fi
    if [ "$due" = "1" ]; then
      n=$(state_get emit_count 0)
      if [ "$n" -ge "$BUDGET" ]; then ledger skipped "\"reason\":\"count_exhausted\",\"emit_count\":$n"; exit 0; fi
      state_set emit_count "$((n + 1))"
      ledger emit "\"seq\":$((n + 1)),\"idle_cache_min\":$IDLE,\"model\":\"$MODEL\""
      printf '[keep-warm %s] #%d 캐시 유지용 자동 턴입니다. 새 작업을 시작하지 말고 한 줄로 확인만 하고 대기하세요.\n' \
        "$(date +%H:%M)" "$((n + 1))" >&2
      exit 2
    fi
  fi
  sleep "$TICK_SEC"
done
