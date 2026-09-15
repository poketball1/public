#!/usr/bin/env python3
"""keepwarm_daemon.py — one keep-warm daemon per Claude Code session.

Reference implementation of the keep-warm lane described in Part B of the guide.
Python 3.10+, standard library only. No repo imports.

WHAT IT DOES
------------
A Claude Code session's prompt cache has a ~1h sliding TTL. If nobody talks to
the session for that long, the cache dies, and the next turn re-pays the whole
conversation prefix as fresh input. This daemon watches ONE session's transcript
and, when the cache is about to expire, injects a tiny "keep-warm" turn so the
prefix is re-read (cheap) instead of re-written (expensive).

The whole design rests on three predicates, each of which cost us an incident:

  1. THE HONEST CLOCK. Idle is not "how long since the transcript file changed"
     and not "how long since the last row". It is "how long since a model
     actually processed tokens" — the last non-sidechain assistant row with
     positive cache usage. A failed injection writes a user row and an
     all-zero synthetic assistant row; both would advance a naive clock while
     the cache is in fact dead. See §7 of the guide (2026-08-13 incident).

  2. THE COLD CLIFF. Never wake a session whose cache is already dead. A fire
     is only allowed inside the window [fire_at, cold_at). Past the cliff the
     daemon terminates rather than firing: a fire there pays a full rewrite for
     a turn nobody asked for — the exact accident this thing exists to prevent.

  3. SUBMISSION IS NOT DELIVERY, AND DELIVERY IS NOT REACHING THE MODEL.
     The relay reporting "injected" only means a terminal API call returned.
     Landing in the transcript is a second fact (confirm), and the model
     actually using cache is a third (verdict). We measured 10/10 "injected"
     against 8/10 actually submitted, so all three are checked separately.

USAGE
-----
    keepwarm_daemon.py --sid <session-id> --transcript <path> --count 24 \\
        [--fire-at-min 50] [--cold-at-min 57] [--tick-sec 240] \\
        [--transport dry-run|wake-file|tmux] [--state-dir DIR] [--ledger PATH]

The module is import-safe: every predicate below is a pure function over parsed
JSONL rows, which is what `test_keepwarm.py` exercises.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

# ---------------------------------------------------------------------------
# Numbers. Every one of these is measured or user-ruled; see §3.5 of the guide.
# ---------------------------------------------------------------------------

MINUTE_MS = 60_000

#: Fire at this idle. 50 min in our arm lane. The nominal TTL is 60 min, but the
#: measured effective edge is ~55.8 min (two post-mortems put eviction at 55.82
#: and 55.91 min — the cache can die ~4 min EARLY, the 1h is not a floor).
#: 50 min leaves ~4.8 min of margin instead of the ~4.1 min that a 55-min
#: cadence had, which was exactly the width of the observed early eviction.
DEFAULT_FIRE_AT_MS = 50 * MINUTE_MS

#: Hard cold cutoff. Past this, the cache is assumed dead and we never fire.
#: Our runner lane uses 58 min (measured excess-death onset 58.5 min). The
#: arm-time gate — "is this session still warm enough to arm at all?" — uses
#: 57 min, a 1-min safety margin under the cliff. The reference implementation
#: exposes one knob, `--cold-at-min`, defaulting to the arm-time value (57).
DEFAULT_COLD_AT_MS = 57 * MINUTE_MS

#: Tick period. Our arm lane ticks at 90 s, the in-runner lane at 4 min. The
#: reference default is 240 s to keep the loop cheap; the invariant that matters
#: is asserted below: the fire window must be at least one tick wide, or a
#: daemon can step straight over it from "not idle yet" to "past the cliff".
DEFAULT_TICK_SEC = 240

#: Budgets. A count, not a duration (a user ruling: "12시간으로 생각 안 하는 게
#: 낫겠다, 카운트가 낫지"). One *reached* keep-warm turn spends one count; a
#: retry inside the same window does not.
DEFAULT_COUNT = 12          # explicit, user-typed `start`
DEFAULT_UNATTENDED_COUNT = 24   # any surface that picks a budget without a human
MAX_COUNT = 48

#: Delivery windows for the `warm` delivery class. The ladder must finish inside
#: the cache slack: 55.8 (TTL edge) − 52 (latest-firing lane) − 1 (fire jitter)
#: = 2.8 min = 168 s, and 45+45+45 = 135 s fits. A draft that widened these to
#: 90/90/240 was rejected for resting on a retired 8-min slack figure.
CONFIRM_MS = 45_000
RETRY_CONFIRM_MS = 45_000
UNCONSUMED_MS = 180_000
CONFIRM_POLL_MS = 5_000

#: After the injected user row lands, wait this long for the assistant answer
#: before giving up on a verdict. Absence of a verdict is not failure.
VERDICT_GRACE_MS = 180_000

#: Bounded reads. Transcripts reach tens of MB; a full slurp is forbidden.
TAIL_BYTES = 256 * 1024

#: Two consecutive "session is not live" ticks before we call it dead. The
#: registry row for a newborn session lands ~2 s in, so a single absent read is
#: not evidence — at a 90 s tick this grace is ~3 min.
DEAD_TICKS_BEFORE_TERMINAL = 2

#: Dialog tools whose open question must never be answered by an injected CR.
DIALOG_TOOL_NAMES = frozenset({"AskUserQuestion", "ExitPlanMode"})

#: Which models are kept warm and for how long. Ordered: first match wins.
#: `fable*` is unbounded (stays warm until the user says off), `opus*` is
#: bounded by the count budget, and anything else observed is not armed at all.
#: A third party edits exactly this table.
MODEL_POLICY: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"fable", re.I), "unbounded"),
    (re.compile(r"opus", re.I), "bounded"),
)

KST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def now_ms() -> int:
    return int(time.time() * 1000)


def parse_ts_ms(value: Any) -> Optional[int]:
    """Parse an ISO-8601 timestamp to epoch ms. Returns None when unparseable.

    Unparseable is a real state, not an error: harness metadata rows carry no
    timestamp at all, and "no timestamp" is precisely what keeps such rows from
    moving any clock.
    """
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def hhmm_kst(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, KST).strftime("%H:%M")


def read_jsonl_tail(path: str | os.PathLike[str], max_bytes: int = TAIL_BYTES) -> list[dict]:
    """Read at most the last `max_bytes` of a JSONL file and parse whole rows.

    Bounded by construction. We measured transcripts up to 53 MB; slurping one
    is an OOM class of bug, and every reader in the lane is bounded the same way.
    The first line is dropped when we seeked, because it is almost certainly a
    fragment.
    """
    p = Path(path)
    size = p.stat().st_size
    start = max(0, size - max_bytes)
    with p.open("rb") as fh:
        fh.seek(start)
        blob = fh.read()
    text = blob.decode("utf-8", errors="replace")
    lines = text.split("\n")
    if start > 0 and lines:
        lines = lines[1:]
    rows: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue   # a torn tail line is not a row
        if isinstance(row, dict):
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Row predicates
# ---------------------------------------------------------------------------

def is_user_row(row: dict) -> bool:
    return row.get("type") == "user" or (row.get("message") or {}).get("role") == "user"


def is_assistant_row(row: dict) -> bool:
    return row.get("type") == "assistant" or (row.get("message") or {}).get("role") == "assistant"


def is_real_assistant_row(row: dict) -> bool:
    """An assistant row that carries a real model name.

    `<synthetic>` is what the harness writes for an API error (429/529): it has
    the shape of an assistant row but no model ran.
    """
    return is_assistant_row(row) and (row.get("message") or {}).get("model") != "<synthetic>"


def is_enqueue_row(row: dict) -> bool:
    """A queue-operation row: the CLI accepted input while a turn was running."""
    return row.get("type") == "queue-operation" and row.get("operation") == "enqueue"


def usage_from_row(row: dict) -> Optional[tuple[Optional[int], Optional[int]]]:
    """(cache_read_input_tokens, cache_creation_input_tokens) or None."""
    usage = (row.get("message") or {}).get("usage") or row.get("usage")
    if not isinstance(usage, dict):
        return None
    read = usage.get("cache_read_input_tokens")
    creation = usage.get("cache_creation_input_tokens")
    return (
        read if isinstance(read, int) else None,
        creation if isinstance(creation, int) else None,
    )


def has_positive_cache_usage(row: dict) -> bool:
    usage = usage_from_row(row)
    if usage is None:
        return False
    read, creation = usage
    return (read or 0) > 0 or (creation or 0) > 0


def row_text_values(row: dict) -> Iterable[str]:
    """Every string inside a row's message content, recursively."""
    def walk(value: Any) -> Iterable[str]:
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                yield from walk(item)
    yield from walk(row.get("message", {}).get("content", row.get("content")))


def tool_use_names(row: dict) -> list[str]:
    content = (row.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    return [
        block.get("name")
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name")
    ]


def has_tool_result(row: dict) -> bool:
    content = (row.get("message") or {}).get("content")
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "tool_result"
        for block in content
    )


# ---------------------------------------------------------------------------
# Predicate 1 — the honest cache clock
# ---------------------------------------------------------------------------

@dataclass
class TailFacts:
    """Everything one bounded tail read tells us. One read per tick."""
    idle_cache_ms: Optional[int] = None
    idle_row_ms: Optional[int] = None
    idle_mtime_ms: Optional[int] = None
    last_assistant_model: Optional[str] = None
    turn_state: str = "ended"
    turn_age_ms: Optional[int] = None
    turn_row_uuid: Optional[str] = None
    turn_row_type: Optional[str] = None
    dialog_tool: Optional[str] = None

    @property
    def effective_idle_ms(self) -> Optional[int]:
        """idle_cache ?? idle_row ?? idle_mtime — in that order, always.

        The fallbacks are NOT safer than the primary: they are the OLD behavior.
        mtime in particular advances on sidechain and synthetic writes, which is
        why arming (as opposed to firing) refuses an mtime-only clock entirely.
        """
        if self.idle_cache_ms is not None:
            return self.idle_cache_ms
        if self.idle_row_ms is not None:
            return self.idle_row_ms
        return self.idle_mtime_ms

    @property
    def has_row_evidence(self) -> bool:
        return self.idle_cache_ms is not None or self.idle_row_ms is not None


def transcript_tail_facts(rows: list[dict], now: int) -> TailFacts:
    """Derive the clock, the model, and the turn state from one tail read."""
    last_cache_evidence_ts: Optional[int] = None
    last_row_ts: Optional[int] = None
    last_model: Optional[str] = None

    for row in rows:
        # Sidechain = sub-agent activity. It does not refresh the MAIN
        # conversation's cache, so it must not move this clock.
        if row.get("isSidechain") is True:
            continue
        ts = parse_ts_ms(row.get("timestamp"))

        # THE CLOCK. Only an assistant row with positive cache read/creation is
        # evidence that a model processed tokens against this prefix.
        if ts is not None and is_assistant_row(row) and has_positive_cache_usage(row):
            last_cache_evidence_ts = ts

        # A raw activity observable, kept as a separate field so the divergence
        # between the two signals can be read off the ledger rather than guessed.
        if ts is not None and (is_user_row(row) or is_real_assistant_row(row)):
            last_row_ts = ts

        if is_assistant_row(row):
            model = (row.get("message") or {}).get("model")
            if isinstance(model, str) and model and model != "<synthetic>":
                last_model = model

    turn = judge_turn_state(rows, now)
    return TailFacts(
        idle_cache_ms=None if last_cache_evidence_ts is None else now - last_cache_evidence_ts,
        idle_row_ms=None if last_row_ts is None else now - last_row_ts,
        last_assistant_model=last_model,
        turn_state=turn.state,
        turn_age_ms=turn.age_ms,
        turn_row_uuid=turn.last_row_uuid,
        turn_row_type=turn.last_row_type,
        dialog_tool=turn.dialog_tool,
    )


def inspect_transcript(path: str | os.PathLike[str], now: int) -> TailFacts:
    """Tail-read + stat. Raises FileNotFoundError when the transcript is gone."""
    mtime_ms = int(Path(path).stat().st_mtime * 1000)
    try:
        facts = transcript_tail_facts(read_jsonl_tail(path), now)
    except Exception:
        # An unreadable tail reads as an ENDED turn, matching the delivery
        # client's fail-open default. Holding on silence would stop every warm
        # turn in the fleet the moment one reader hiccups.
        facts = TailFacts()
    facts.idle_mtime_ms = now - mtime_ms
    return facts


# ---------------------------------------------------------------------------
# Predicate 2 — has the turn ended?
# ---------------------------------------------------------------------------

@dataclass
class TurnState:
    state: str                       # ended | mid_turn | dialog_pending
    age_ms: Optional[int] = None
    last_row_uuid: Optional[str] = None
    last_row_type: Optional[str] = None
    dialog_tool: Optional[str] = None


def is_excluded_row(row: dict) -> bool:
    """Sidechain or meta, at row level or inside `message`."""
    message = row.get("message") or {}
    return bool(row.get("isSidechain") or row.get("isMeta")
                or message.get("isSidechain") or message.get("isMeta"))


def is_turn_content_row(row: dict) -> bool:
    """A row that says something about whether the turn is over.

    Defined by what a row HAS, not by an enumeration of metadata types. Our
    harness writes at least eight kinds of metadata row (attachment,
    file-history-delta, last-prompt, custom-title, agent-name, mode,
    permission-mode, bridge-session); every one of them lacks a timestamp or
    lacks message content, so requiring BOTH excludes them — including the next
    metadata type the harness invents, which a hand list would miss.
    """
    if is_excluded_row(row):
        return False
    if not isinstance(row.get("timestamp"), str) or not row["timestamp"]:
        return False
    if is_enqueue_row(row):
        return True
    if row.get("type") not in ("user", "assistant"):
        return False
    content = (row.get("message") or {}).get("content")
    if isinstance(content, (str, list)):
        return len(content) > 0
    return content is not None


def ends_turn(row: dict) -> bool:
    """The turn is over iff the last content row is an assistant row with no tool_use."""
    return row.get("type") == "assistant" and not tool_use_names(row)


def judge_turn_state(rows: list[dict], now: int) -> TurnState:
    """Is the session's last turn finished?

    This replaced an earlier guard that asked "is a dialog tool_use the last
    row?". That guard was structurally blind: the harness does not flush an
    unanswered AskUserQuestion's assistant block to the transcript until the
    answer arrives, so the guard read `false` in 5 out of 5 real incidents while
    injected CRs silently confirmed option 1 of open dialogs (option-1 rate
    91% vs a 48% baseline). The fact we CAN see on disk is whether the turn
    ended — an interrupted-looking tail that is ~50 min old is exactly what an
    unflushed pending dialog looks like.

    Three rules, one pass:
      dialog_pending — a dialog tool_use sits AFTER the last user-role row,
                       i.e. it was never answered. (Answering writes a user
                       tool_result row, which pushes the user index past it, so
                       an answered dialog still visible in the tail is not
                       pending.)
      mid_turn       — the last content row is not an assistant row without
                       tool_use. This one rule covers every open shape:
                       unanswered tool_result, tool_use with no result, a user
                       sentence with no reply, a pending enqueue row.
      ended          — everything else.
    """
    last_user_index = -1
    dialog_index = -1
    dialog_tool: Optional[str] = None
    last_content: Optional[dict] = None

    for index, row in enumerate(rows):
        if row.get("isSidechain") is True:
            continue
        if is_user_row(row):
            last_user_index = index
        if is_assistant_row(row):
            found = next((n for n in tool_use_names(row) if n in DIALOG_TOOL_NAMES), None)
            if found:
                dialog_index, dialog_tool = index, found
        if is_turn_content_row(row):
            last_content = row

    if dialog_index > last_user_index:
        state = "dialog_pending"
    elif last_content is not None and not ends_turn(last_content):
        state = "mid_turn"
        dialog_tool = None
    else:
        # Includes the fail-open case: no content row at all reads as `ended`.
        # Holding on silence would stop every warm turn the moment one reader
        # hiccups, which is worse than one injection into a quiet session.
        state = "ended"
        dialog_tool = None

    age = None
    if last_content is not None:
        ts = parse_ts_ms(last_content.get("timestamp"))
        if ts is not None:
            age = now - ts

    return TurnState(
        state=state,
        age_ms=age,
        last_row_uuid=(last_content or {}).get("uuid"),
        last_row_type=(last_content or {}).get("type"),
        dialog_tool=dialog_tool,
    )


# ---------------------------------------------------------------------------
# Predicate 3 — model policy
# ---------------------------------------------------------------------------

def model_budget(model: Optional[str]) -> str:
    """unbounded | bounded | ineligible | unknown — one owner, no second regex.

    `unknown` (nothing observed yet, blank, or `<synthetic>`) behaves as
    `bounded`: absence is not a verdict. `ineligible` is a real observed model
    that matches nothing, and that session is not kept warm at all.
    """
    if not isinstance(model, str):
        return "unknown"
    observed = model.strip()
    if not observed or observed == "<synthetic>":
        return "unknown"
    for pattern, budget in MODEL_POLICY:
        if pattern.search(observed):
            return budget
    return "ineligible"


# ---------------------------------------------------------------------------
# Message, fingerprint, confirm
# ---------------------------------------------------------------------------

MAX_MESSAGE_LEN = 300


def build_message(arm_id: str, seq: int, now: int, retry: bool = False) -> str:
    """The injected text. Only the placeholders and the retry suffix vary.

    Two rules are load-bearing:
      - a nonce `<arm_id>#<seq>` so the sender can recognise its own landing;
      - wall-clock HH:MM, never "idle 52 min". The idle numbers live in the
        ledger; a model-visible string that narrates infrastructure invites the
        session to act on it.
    Vocabulary is kept cache-safe: words like "보안/경계/복원력" have been
    observed to trigger a model fallback, which blows up the very cache we are
    protecting.
    """
    text = (
        f"[keep-warm {hhmm_kst(now)}] {arm_id}#{seq} — warm 유지용 자동 턴. "
        f"새 작업을 시작하지 말고 한 줄 확인만 하고 대기를 계속한다."
    )
    if retry:
        text += " - retry"
    if "\n" in text or "\r" in text or len(text) > MAX_MESSAGE_LEN:
        raise ValueError(f"keep-warm message invariant violated (len={len(text)})")
    return text


#: The relay truncates what it types at this many characters, AFTER normalizing.
#: A message longer than this loses its tail — including a trailing nonce, which
#: makes confirm impossible and turns every fire into a retry. Senders that can
#: exceed it must spill the body to a file and inject `head … (pointer)` + nonce
#: inside the budget. Keep-warm's message is ~120 chars, so it never spills.
RELAY_MAX_MESSAGE_CHARS = 500


def normalize_for_match(text: str) -> str:
    """Normalize exactly the way the relay does before it types.

    Two substitutions, IN THIS ORDER — the order is load-bearing: "a\\rb"
    becomes "a b", not "ab".
      1. runs of CR/LF/TAB    -> a single space
      2. other control chars  -> removed

    The needle must be normalized with the SAME rule as the payload. A mirror
    drift here makes every confirm fail and every fire retry, which reads in the
    ledger as a delivery problem and is in fact a matching problem.
    """
    text = re.sub(r"[\r\n\t]+", " ", text)
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)


def make_nonce_predicate(nonce: str) -> Callable[[dict], bool]:
    """Recognise the injected row by exact nonce token.

    Exact token boundaries matter: `#1` must not match `#10`. Everything in the
    lane — submit confirm, queue confirm, late confirm, verdict attribution —
    uses this one predicate so they can never disagree about which row is ours.
    """
    escaped = re.escape(nonce)
    token = re.compile(rf"(^|[^A-Za-z0-9_#-]){escaped}($|[^A-Za-z0-9_#-])")

    def predicate(row: dict) -> bool:
        if not (is_user_row(row) or is_enqueue_row(row)):
            return False
        return any(token.search(normalize_for_match(v)) for v in row_text_values(row))

    return predicate


@dataclass
class ConfirmResult:
    status: str                 # confirmed | queued_confirmed | not_confirmed
    row_uuid: Optional[str] = None


def inspect_submission(rows: list[dict], nonce: str) -> ConfirmResult:
    """Did our message land? One pass, user row wins over a queue row.

    Landing as a QUEUE row is also a success — the CLI accepted the input while
    a turn was running. Waiting out the whole window for a user row after seeing
    the queue row cost every busy-session sender a full window (measured: every
    queued confirm landed at exactly 45.0 s), so the queue row confirms
    immediately. Within one poll, though, a user row still wins.
    """
    predicate = make_nonce_predicate(nonce)
    queued: Optional[dict] = None
    for row in rows:
        if not predicate(row):
            continue
        if is_user_row(row):
            return ConfirmResult("confirmed", row.get("uuid"))
        if is_enqueue_row(row) and queued is None:
            queued = row
    if queued is not None:
        return ConfirmResult("queued_confirmed", queued.get("uuid"))
    return ConfirmResult("not_confirmed")


# ---------------------------------------------------------------------------
# Verdict — did the injected turn actually reach a model?
# ---------------------------------------------------------------------------

VERDICT_MAX_HOPS = 8


def _resolves_to(row: dict, injected_uuid: str, by_uuid: dict[str, dict]) -> bool:
    """Walk the parent chain, but only across NON-turn rows.

    A strict `parentUuid == injected.uuid` rule died the day the harness began
    interposing `attachment` rows between a user row and its assistant: 135 of
    135 verdicts went blank overnight. Walking the chain restores attribution;
    stopping at any user/assistant ancestor preserves the thing the strict rule
    was protecting — an assistant that belongs to a DIFFERENT turn can never be
    attributed to ours.
    """
    parent = row.get("parentUuid")
    for _ in range(VERDICT_MAX_HOPS):
        if not isinstance(parent, str) or not parent:
            return False
        if parent == injected_uuid:
            return True
        node = by_uuid.get(parent)
        if node is None:
            return False
        if is_user_row(node) or is_assistant_row(node):
            return False      # turn boundary
        parent = node.get("parentUuid")
    return False


@dataclass
class Verdict:
    status: str                 # reached | not-reached | no-verdict | pending
    reason: str
    injected_user_uuid: Optional[str] = None
    assistant_uuid: Optional[str] = None
    cache_read: Optional[int] = None
    cache_creation: Optional[int] = None
    cache_outcome: Optional[str] = None      # hit | rewrite | None
    is_api_error: Optional[bool] = None
    api_error_status: Optional[int] = None


def classify_verdict(rows: list[dict], nonce: str,
                     injected_user_uuid: Optional[str] = None) -> Verdict:
    """Delivery success is the client's truth; this asks the separate question.

    reached      — the direct assistant used cache (read or creation > 0).
    not-reached  — the direct assistant reports EXACTLY 0/0: a limit/error row.
                   The budget is preserved and the arm suspends.
    no-verdict   — no attributable assistant yet, or no usage on it. This is not
                   a failure and not a suspend; the arm stays armed.
    """
    predicate = make_nonce_predicate(nonce)
    if injected_user_uuid:
        injected = next(
            (r for r in rows if r.get("uuid") == injected_user_uuid and predicate(r)), None
        )
    else:
        injected = next((r for r in rows if predicate(r) and r.get("uuid")), None)
    if injected is None:
        return Verdict("pending", "injected_user_not_found")

    by_uuid = {r["uuid"]: r for r in rows if isinstance(r.get("uuid"), str)}
    assistant = next(
        (r for r in rows
         if r.get("isSidechain") is not True
         and is_assistant_row(r)
         and _resolves_to(r, injected["uuid"], by_uuid)),
        None,
    )
    if assistant is None:
        return Verdict("pending", "direct_assistant_not_found",
                       injected_user_uuid=injected.get("uuid"))

    err = {
        "is_api_error": assistant.get("isApiErrorMessage") is True,
        "api_error_status": assistant.get("apiErrorStatus")
        if isinstance(assistant.get("apiErrorStatus"), int) else None,
    }
    usage = usage_from_row(assistant)
    if usage is None or usage[0] is None or usage[1] is None:
        return Verdict("no-verdict", "usage_missing",
                       injected_user_uuid=injected.get("uuid"),
                       assistant_uuid=assistant.get("uuid"), **err)

    read, creation = usage
    if read == 0 and creation == 0:
        status, reason = "not-reached", "cache_usage_zero"
    else:
        status, reason = "reached", "cache_usage_positive"

    # `rewrite` means the turn reached the model but re-paid the conversation
    # body — the body cache was cold. `read > 0` alone cannot mean "hit": the
    # shared workspace system+tools prefix (~20-30k tokens) stays warm via
    # concurrent sessions, so a body-dead rewrite still reads a positive number.
    # Measured body-survival ratios are bimodal (~1.0 and ~0.0), so read>=creation
    # is a robust split. A rewrite still refills the cache, so it is still
    # `reached` and still spends a count — the label exposes the COST, which was
    # the thing that stayed silent for a day and 2.6M rewritten tokens.
    outcome = None
    if status == "reached":
        outcome = "hit" if read >= creation else "rewrite"

    return Verdict(status, reason,
                   injected_user_uuid=injected.get("uuid"),
                   assistant_uuid=assistant.get("uuid"),
                   cache_read=read, cache_creation=creation,
                   cache_outcome=outcome, **err)


def classify_resume(rows: list[dict], watermark_assistant_uuid: Optional[str]) -> dict:
    """Is a suspended arm allowed to resume?

    Two conditions, and only the first lives here: a NEW assistant after the
    failing row that actually used cache. Transcript movement alone is not
    enough — the limit response itself moves the transcript, which is how a
    naive "it's advancing again" rule would resume straight into a dead cache.
    The second condition (the fire window is satisfied again) is re-checked by
    the tick, deliberately, because that is the cold-cliff guard.

    Sidechain rows are NOT excluded here, unlike the clock. The question is
    different: the clock asks "was the MAIN conversation's cache touched", this
    asks "is the model answering at all again".
    """
    if not watermark_assistant_uuid:
        return {"status": "waiting", "reason": "watermark_not_found"}
    try:
        index = next(i for i, r in enumerate(rows) if r.get("uuid") == watermark_assistant_uuid)
    except StopIteration:
        return {"status": "waiting", "reason": "watermark_not_found"}
    for row in rows[index + 1:]:
        if not is_assistant_row(row):
            continue
        if has_positive_cache_usage(row):
            return {"status": "ready", "assistant_uuid": row.get("uuid")}
    return {"status": "waiting", "reason": "positive_cache_usage_not_found"}


# ---------------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------------

class Transport:
    """A transport types a string into a live terminal and presses Enter.

    It does NOT confirm anything. That asymmetry is the whole point: the relay
    is a dumb pipe, and every confirm/retry/ledger decision stays with the
    sender, which owns the message and can read the transcript.
    """
    name = "abstract"

    def deliver(self, sid: str, message: str) -> None:
        raise NotImplementedError


class DryRunTransport(Transport):
    """Writes nothing to any live session. Used for tests and demos.

    With `echo_transcript`, it simulates what a healthy session would do:
    append the user row and a positive-cache assistant answer. That lets a
    third party watch a complete fire -> confirm -> verdict cycle without ever
    touching a real terminal.
    """
    name = "dry-run"

    def __init__(self, sink: Optional[Path] = None,
                 echo_transcript: Optional[Path] = None,
                 echo_usage: tuple[int, int] = (250_000, 1_200),
                 echo_model: str = "claude-opus-5"):
        self.sink = sink
        self.echo_transcript = echo_transcript
        self.echo_usage = echo_usage
        self.echo_model = echo_model

    def deliver(self, sid: str, message: str) -> None:
        line = f"[dry-run] would inject into {sid}: {message}"
        print(line, file=sys.stderr)
        if self.sink:
            with self.sink.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        if self.echo_transcript:
            self._echo(message)

    def _echo(self, message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        user_uuid = str(uuid.uuid4())
        read, creation = self.echo_usage
        rows = [
            {"type": "user", "uuid": user_uuid, "parentUuid": None, "timestamp": ts,
             "message": {"role": "user", "content": message}},
            {"type": "assistant", "uuid": str(uuid.uuid4()), "parentUuid": user_uuid,
             "timestamp": ts,
             "message": {"role": "assistant", "model": self.echo_model,
                         "content": [{"type": "text", "text": "확인. 대기 계속."}],
                         "usage": {"cache_read_input_tokens": read,
                                   "cache_creation_input_tokens": creation}}},
        ]
        with self.echo_transcript.open("a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")


class WakeFileTransport(Transport):
    """Drops a request file that an editor-side relay picks up and types.

    The write is NO-CLOBBER on purpose: an unconsumed request belongs to
    whoever wrote it, and overwriting it loses that message silently. When the
    slot is occupied we wait briefly and then give up for this tick.
    """
    name = "wake-file"

    def __init__(self, wake_dir: Path, sender: str = "keepwarm-arm",
                 slot_wait_ms: int = 30_000):
        self.wake_dir = wake_dir
        self.sender = sender
        self.slot_wait_ms = slot_wait_ms

    def deliver(self, sid: str, message: str) -> None:
        self.wake_dir.mkdir(parents=True, exist_ok=True)
        target = self.wake_dir / f"{sid}.json"
        deadline = now_ms() + self.slot_wait_ms
        while target.exists():
            if now_ms() >= deadline:
                raise RuntimeError("REQUEST_SLOT_OCCUPIED")
            time.sleep(1.0)
        payload = {
            "sid": sid,                     # authoritative target, NOT the filename
            "message": message,
            "source": self.sender,          # diagnostic label only
            "requested_at": int(time.time()),   # epoch SECONDS
            # How the relay should type it. `body` writes the text without a
            # newline, `cr` writes a bare carriage return. Two separate writes,
            # because one `sendText(text, true)` was measured to drop input.
            "submit_plan": ["body", "cr"],
        }
        tmp = self.wake_dir / f".{sid}.json.tmp.{os.getpid()}"
        tmp.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            # link(2) cannot replace an existing inode, so this is no-clobber by
            # construction. Overwriting would silently destroy an unconsumed
            # message that belongs to another sender.
            os.link(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)


def build_transport(args: argparse.Namespace) -> Transport:
    if args.transport == "dry-run":
        return DryRunTransport(
            sink=Path(args.dry_run_sink) if args.dry_run_sink else None,
            echo_transcript=Path(args.transcript) if args.dry_run_echo else None,
        )
    if args.transport == "wake-file":
        return WakeFileTransport(Path(args.wake_dir).expanduser())
    if args.transport == "tmux":
        from transport_tmux import TmuxTransport   # local import: optional dependency
        return TmuxTransport(pane=args.tmux_pane)
    raise SystemExit(f"unknown transport: {args.transport}")


# ---------------------------------------------------------------------------
# State file + ledger
# ---------------------------------------------------------------------------

def state_path(state_dir: Path, sid: str) -> Path:
    return state_dir / f"{sid}.state.json"


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)          # atomic: a reader never sees a half file


def read_state(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def append_ledger(path: Path, entry: dict) -> None:
    """Append one JSON line under an exclusive lock. Never raises upward."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with path.open("a", encoding="utf-8") as fh:
            try:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass                # best effort on platforms without flock
            fh.write(line)
            fh.flush()
    except OSError as err:
        print(f"[keepwarm] ledger append failed: {err}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Session liveness (registry)
# ---------------------------------------------------------------------------

def session_is_live(sessions_dir: Path, sid: str) -> str:
    """alive | dead | indeterminate.

    The registry is `~/.claude/sessions/<pid>.json`, one file per session
    process, carrying at least `sessionId` and `cwd`. A row whose PID is dead
    does not speak for the session: reading identity off a corpse is how a live
    arm gets terminated as "not interactive".

    `indeterminate` is a first-class answer — it blocks the terminal transition
    rather than guessing, because a probe error is not evidence of death.
    """
    if not sessions_dir.is_dir():
        return "indeterminate"
    found_row = False
    for entry in sorted(sessions_dir.glob("*.json")):
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("sessionId") != sid:
            continue
        found_row = True
        pid = entry.stem
        if not pid.isdigit():
            continue
        if Path("/proc", pid).exists():
            return "alive"
    return "dead" if found_row else "dead"


def is_arm_target(entry: dict) -> bool:
    """A terminal-launched interactive session, and nothing else.

    Two discriminators, both fail-closed on an unknown value: `kind` excludes a
    background caller, `entrypoint` excludes a headless SDK run. Neither is
    excluded "naturally" — we measured 4 bg and 2 sdk-cli rows sitting right
    next to 151 real ones.
    """
    kind = entry.get("kind", "interactive")
    entrypoint = entry.get("entrypoint", "cli")
    return kind == "interactive" and entrypoint == "cli"


def munge_cwd(cwd: str) -> str:
    """`/home/me/proj` -> `-home-me-proj`. Dots become dashes too."""
    return re.sub(r"[/.]", "-", cwd)


def transcript_for(sid: str, cwd: str, claude_root: Path) -> Path:
    return claude_root / "projects" / munge_cwd(cwd) / f"{sid}.jsonl"


# ---------------------------------------------------------------------------
# The daemon
# ---------------------------------------------------------------------------

@dataclass
class Arm:
    """One armed session. The daemon owns exactly one of these."""
    sid: str
    arm_id: str
    transcript: Path
    state_dir: Path
    ledger: Path
    transport: Transport
    sessions_dir: Path
    count_budget: int = DEFAULT_UNATTENDED_COUNT
    fire_at_ms: int = DEFAULT_FIRE_AT_MS
    cold_at_ms: int = DEFAULT_COLD_AT_MS
    tick_ms: int = DEFAULT_TICK_SEC * 1000
    natal: bool = False
    arm_source: str = "start"

    # runtime
    seq: int = 0
    emit_count: int = 0
    confirmed_count: int = 0
    status: str = "armed"
    suspended: bool = False
    suspension_reason: Optional[str] = None
    watermark_assistant_uuid: Optional[str] = None
    resume_candidate_uuid: Optional[str] = None
    model: Optional[str] = None
    last_emit_at: Optional[int] = None
    last_nonce: Optional[str] = None
    dead_ticks: int = 0
    started_at: int = field(default_factory=now_ms)
    last_idle: Optional[TailFacts] = None
    turn_hold_key: Optional[str] = None

    # --- observation ------------------------------------------------------
    @property
    def budget_unbounded(self) -> bool:
        return model_budget(self.model) == "unbounded"

    def snapshot(self) -> dict:
        return {
            "sid": self.sid,
            "arm_id": self.arm_id,
            "pid": os.getpid(),
            "arm_source": self.arm_source,
            "started_at": datetime.fromtimestamp(self.started_at / 1000,
                                                 timezone.utc).isoformat().replace("+00:00", "Z"),
            "count_budget": self.count_budget,
            "model": self.model,
            # The daemon derives this ONCE and the statusline reads the boolean.
            # No consumer re-implements the model policy.
            "budget_unbounded": self.budget_unbounded,
            "emit_count": self.emit_count,
            "confirmed_count": self.confirmed_count,
            "idle_ms": self.fire_at_ms,
            "tick_ms": self.tick_ms,
            "status": self.status,
            "natal": self.natal,
            "suspension_reason": self.suspension_reason,
            "verdict_watermark_assistant_uuid": self.watermark_assistant_uuid,
            "resume_candidate_assistant_uuid": self.resume_candidate_uuid,
            "last_delivery_nonce": self.last_nonce,
        }

    def publish(self) -> None:
        atomic_write_json(state_path(self.state_dir, self.sid), self.snapshot())

    def log(self, event: str, **fields: Any) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event,
            "lane": "arm",
            "sid": self.sid,
            "arm_id": self.arm_id,
            "seq": self.seq,
        }
        entry.update({k: v for k, v in fields.items() if v is not None})
        append_ledger(self.ledger, entry)

    # --- lifecycle --------------------------------------------------------
    def arm(self) -> None:
        assert_timing_window(self.fire_at_ms, self.cold_at_ms, self.tick_ms)
        self.status = "armed"
        self.publish()
        self.log("armed",
                 idle_ms=self.fire_at_ms, tick_ms=self.tick_ms,
                 count_budget=self.count_budget,
                 natal=True if self.natal else None,
                 arm_source=self.arm_source,
                 model=self.model)

    def terminate(self, reason: str) -> None:
        self.status = reason
        idle = self.last_idle
        self.log("terminated", reason=reason,
                 nonce=self.last_nonce, model=self.model,
                 idle_row_ms=idle.idle_row_ms if idle else None,
                 idle_cache_ms=idle.idle_cache_ms if idle else None,
                 idle_mtime_ms=idle.idle_mtime_ms if idle else None)
        if keeps_debris(reason, self.confirmed_count):
            self.publish()
        else:
            state_path(self.state_dir, self.sid).unlink(missing_ok=True)


#: Terminal reasons whose state file must survive, each naming a live consumer.
FUNCTIONAL_TERMINAL_REASONS = frozenset({
    "stopped",            # the durable carrier of sticky opt-out
    "delivery_failure",   # the diagnostic twin of the red popup
    "count_exhausted",    # blocks an automatic actor from re-granting a budget
    "cold_missed",        # carries the remainder to the next automatic arm
    "replaced",           # the successor owns these artifacts
})


def keeps_debris(reason: str, confirmed_count: int) -> bool:
    """Keep the state file only when something still reads it.

    Two things can: a terminal reason with a live consumer, or a budget this arm
    already spent. The second clause is not decoration — the state file is the
    ONLY carrier of "how much budget is left", so deleting a consumed snapshot
    hands the next automatic arm a fresh 24 and silently re-creates the budget.
    Emission history alone keeps nothing: that story belongs to the ledger.
    """
    return reason in FUNCTIONAL_TERMINAL_REASONS or confirmed_count > 0


#: Every status that means "this arm is not running any more".
TERMINAL_STATUSES = frozenset({
    "stopped", "session_dead", "delivery_failure", "count_exhausted",
    "cold_missed", "stale", "replaced", "model_ineligible",
    "signal_terminated", "missing_transcript",
})


def automatic_arm_plan(previous: Optional[dict],
                       nonterminal_liveness: Optional[str] = None,
                       budget: Optional[str] = None) -> dict:
    """The single owner of "may an AUTOMATIC actor arm this sid, and with what?"

    Both automatic surfaces — the SessionStart birth hook and the Stop re-arm
    hook — ask this one function, so they can never disagree about who is armed.
    An explicit, user-typed `start` does NOT go through here: when a human names
    a session, that outranks every rule below.

    Returns {"action": "arm"|"skip", ...}.

    THE RULE THAT MATTERS: an automatic actor never CREATES budget. It inherits
    `max(0, count_budget - confirmed_count)` from the debris, and a fresh
    unattended budget is granted only when there is no state file at all. We
    learned this from the other direction: two terminal paths used to DELETE the
    state file, and since the spent `confirmed_count` lived only in that file,
    the next automatic arm read "absent" and handed out a fresh 24. One measured
    session spent 1, died, and was re-granted 24.

    A malformed or negative historical counter is fail-closed as exhausted: we
    do not guess a budget.
    """
    def exhausted(**extra: Any) -> dict:
        if budget == "unbounded":
            # Not a loophole in the budget rule — it IS the budget rule for an
            # unbounded model. Such a session has no count to consume, so an
            # exhausted-looking snapshot is a leftover from the arm that ran
            # BEFORE the model was known, not a spent budget.
            return {"action": "arm", "count": DEFAULT_UNATTENDED_COUNT,
                    "prior": previous, "recovery_reason": "unbounded_model_revive",
                    **extra}
        return {"action": "skip",
                # The budget question and the eligibility question meet here,
                # and eligibility is the honest answer: on a below-policy
                # session "count_exhausted" is a true statement about the
                # counter and a misleading one about the sid, because the spent
                # budget is not why it will never be armed again.
                "reason": "model_ineligible" if budget == "ineligible" else "count_exhausted",
                "prior": previous, **extra}

    if not previous:
        return {"action": "arm", "count": DEFAULT_UNATTENDED_COUNT,
                "prior": None, "recovery_reason": "state_missing"}

    status = previous.get("status")

    # The user's explicit opt-out outranks everything, including an unbounded
    # model. `stopped` has exactly one author — the `stop` command — which is
    # what keeps an external SIGTERM from ever looking like a decision.
    if status == "stopped":
        return {"action": "skip", "reason": "opted_out", "prior": previous}

    if status == "count_exhausted":
        return exhausted()

    if status not in TERMINAL_STATUSES:
        # A non-terminal state means a daemon claims this sid. Only a
        # CONFIRMED-dead identity lets us take it over.
        if nonterminal_liveness == "indeterminate":
            return {"action": "skip", "reason": "daemon_identity_indeterminate",
                    "prior": previous}
        if nonterminal_liveness != "dead":
            return {"action": "skip", "reason": f"existing_arm:{status or 'unknown'}",
                    "prior": previous}

    count_budget = previous.get("count_budget")
    confirmed = previous.get("confirmed_count")
    if not isinstance(count_budget, int) or count_budget < 0 \
            or not isinstance(confirmed, int) or confirmed < 0 \
            or isinstance(count_budget, bool) or isinstance(confirmed, bool):
        return exhausted(remainder=0)

    remainder = max(0, count_budget - confirmed)
    if remainder == 0:
        return exhausted(remainder=remainder)

    return {
        "action": "arm", "count": remainder, "prior": previous, "remainder": remainder,
        "recovery_reason": (f"terminal_debris:{status}" if status in TERMINAL_STATUSES
                            else "dead_daemon"),
    }


def assert_timing_window(fire_at_ms: int, cold_at_ms: int, tick_ms: int) -> None:
    """The fire window must be at least one tick wide.

    Otherwise a daemon can go from "not idle yet" on one tick to "past the
    cliff" on the next, never firing, and the failure is silent — which is
    exactly what an env override can do to you at 3 a.m.
    """
    if cold_at_ms - fire_at_ms < tick_ms:
        raise ValueError(
            f"fire window [{fire_at_ms}, {cold_at_ms}) is narrower than one tick "
            f"({tick_ms}ms): a daemon could step over it without ever firing"
        )


# --- one tick --------------------------------------------------------------

def tick(arm: Arm, now: int) -> str:
    """Evaluate one tick. Returns the outcome label (also the test contract).

    Order is deliberate and each step is a guard someone learned the hard way.
    """
    # 0. Transcript. A transcript that vanished mid-run can no longer be warmed.
    try:
        idle = inspect_transcript(arm.transcript, now)
    except FileNotFoundError:
        # During the natal window this is normal: the transcript file is only
        # born with the session's first content row, which can lag the first
        # tick. Post-natal it is terminal.
        return "no_transcript"
    arm.last_idle = idle
    if idle.last_assistant_model:
        arm.model = idle.last_assistant_model    # sticky: a tail can scroll past it

    # 1. Liveness BEFORE anything else, suspension included. A suspended daemon
    #    whose session has disappeared must not keep reporting a resume wait.
    live = session_is_live(arm.sessions_dir, arm.sid)
    if live == "indeterminate":
        return "session_liveness_indeterminate"
    if live != "alive":
        return "not_live"

    # 2. Natal: a newborn session has no assistant row and therefore no model
    #    and no row-anchored clock. It must not enter the emission machine at
    #    all — that is a structural guarantee, not a threshold.
    if arm.natal:
        return natal_tick(arm, idle)

    # 3. Model policy. A `/model` switch below Opus ends the arm quietly.
    if model_budget(arm.model) == "ineligible":
        return "model_ineligible"

    # 4. Suspension: only a latched resume candidate lets us continue, and the
    #    fire window still has to be satisfied afterwards.
    if arm.suspended:
        outcome = resume_tick(arm, idle, now)
        if outcome is not None:
            return outcome

    effective = idle.effective_idle_ms
    if effective is None:
        return "no_clock"
    if not arm.suspended and effective < arm.fire_at_ms:
        return "not_idle"

    # 5. THE COLD CLIFF. Waking a cold session pays a full rewrite with no
    #    consumer. This is a hard rule, and it is why we terminate here instead
    #    of firing late.
    if effective >= arm.cold_at_ms:
        return "past_ttl_cliff"

    # 6. Never inject into an open turn. An interrupted tool or a pending
    #    decision costs this session its refresh until its next turn — cache
    #    loss is cheaper than forging a user decision.
    if idle.turn_state != "ended":
        key = f"{idle.turn_row_uuid}:{idle.turn_state}"
        if arm.turn_hold_key != key:
            arm.turn_hold_key = key
            arm.log("turn_hold", turn_state=idle.turn_state,
                    turn_age_ms=idle.turn_age_ms, turn_row_uuid=idle.turn_row_uuid,
                    dialog_tool=idle.dialog_tool)
        return "turn_hold"
    arm.turn_hold_key = None

    if arm.last_emit_at is not None and now - arm.last_emit_at < arm.fire_at_ms:
        return "recent_emit"

    # 7. Resume is recorded only at the moment we are actually about to fire —
    #    resume means "the window is satisfied again", not "the model answered".
    if arm.suspended:
        arm.log("resumed",
                watermark_assistant_uuid=arm.watermark_assistant_uuid,
                resume_assistant_uuid=arm.resume_candidate_uuid,
                idle_cache_ms=idle.idle_cache_ms, idle_row_ms=idle.idle_row_ms)
        arm.suspended = False
        arm.suspension_reason = None
        arm.status = "armed"

    return fire(arm, idle, now)


def natal_tick(arm: Arm, idle: TailFacts) -> str:
    """Observe without firing until BOTH kinds of evidence exist.

    ① a timestamp-parseable row (so the clock anchors on rows, not mtime), and
    ② a real assistant model.
    Plus the same warm-margin gate the arm-time surfaces use: a newborn that is
    already past the margin keeps waiting rather than escaping into the loop and
    dying `cold_missed` on its first standard tick.
    Waiting costs nothing: no budget is spent while natal.
    """
    if not idle.last_assistant_model:
        return "natal_wait"
    if not idle.has_row_evidence:
        return "natal_wait"
    if (idle.effective_idle_ms or 0) >= arm.cold_at_ms:
        return "natal_wait"

    arm.model = idle.last_assistant_model
    arm.log("natal_resolved", verdict="interactive", model=arm.model)
    if model_budget(arm.model) == "ineligible":
        return "model_ineligible"
    arm.natal = False
    arm.publish()
    return "natal_resolved"


def resume_tick(arm: Arm, idle: TailFacts, now: int) -> Optional[str]:
    """Returns an outcome label to stop the tick, or None to keep going."""
    if arm.resume_candidate_uuid is None:
        try:
            rows = read_jsonl_tail(arm.transcript)
        except OSError:
            return "suspended"
        verdict = classify_resume(rows, arm.watermark_assistant_uuid)
        if verdict["status"] != "ready":
            return "suspended"
        arm.resume_candidate_uuid = verdict.get("assistant_uuid")
        arm.suspension_reason = "suspended_resume_wait"
        arm.publish()

    effective = idle.effective_idle_ms
    if effective is None:
        return "suspended"
    if effective < arm.fire_at_ms:
        return "suspended_wait_idle"
    if effective >= arm.cold_at_ms:
        return "suspended_past_ttl_cliff"
    if idle.turn_state != "ended":
        return "suspended_turn_hold"
    return None


def fire(arm: Arm, idle: TailFacts, now: int) -> str:
    """Emit, confirm (with one retry), then judge the verdict."""
    arm.seq += 1
    nonce = f"{arm.arm_id}#{arm.seq}"
    message = build_message(arm.arm_id, arm.seq, now)
    arm.last_nonce = nonce
    ledger_idle = {
        "idle_cache_ms": idle.idle_cache_ms,
        "idle_row_ms": idle.idle_row_ms,
        "idle_mtime_ms": idle.idle_mtime_ms,
    }

    # The cursor: everything the verdict reads must come from AFTER the emit.
    # Without it a re-read of the whole tail can attribute an older row with the
    # same nonce and produce a confident wrong answer.
    cursor = len(read_jsonl_tail_safe(arm.transcript))

    try:
        arm.transport.deliver(arm.sid, message)
    except Exception as err:
        arm.log("delivery_failed", failure_class="request_write_failed",
                reason=str(err), **ledger_idle)
        return "emit_failed"

    arm.emit_count += 1
    arm.last_emit_at = now
    arm.log("emit", nonce=nonce, delivery_class="warm",
            confirm_ms=CONFIRM_MS, retry_confirm_ms=RETRY_CONFIRM_MS,
            turn_row_uuid=idle.turn_row_uuid, **ledger_idle)

    confirm = wait_for_submission(arm.transcript, nonce, CONFIRM_MS, cursor)
    if confirm.status == "not_confirmed":
        # ONE retry, same text plus ` - retry`. If the Enter was swallowed, the
        # original is still sitting in the input box and the retry text appends
        # to it, so a single Enter submits the merged line — which is why the
        # nonce is accepted from either copy.
        retry_message = build_message(arm.arm_id, arm.seq, now, retry=True)
        try:
            arm.transport.deliver(arm.sid, retry_message)
        except Exception as err:
            arm.log("delivery_failed", failure_class="request_write_failed",
                    reason=str(err), nonce=nonce)
            return "delivery_failed"
        arm.log("retry_emit", nonce=nonce)
        confirm = wait_for_submission(arm.transcript, nonce, RETRY_CONFIRM_MS, cursor)
        if confirm.status == "not_confirmed":
            arm.log("delivery_failed", failure_class="injected_not_submitted",
                    reason="submission_not_confirmed_after_retry", nonce=nonce)
            return "delivery_failed"
        arm.log("retry_confirmed", nonce=nonce, row_uuid=confirm.row_uuid)
    else:
        arm.log(confirm.status, nonce=nonce, row_uuid=confirm.row_uuid)

    verdict = wait_for_verdict(arm.transcript, nonce, confirm.row_uuid, VERDICT_GRACE_MS)
    arm.log("verdict", nonce=nonce, status=verdict.status, reason=verdict.reason,
            assistant_uuid=verdict.assistant_uuid,
            cache_read_input_tokens=verdict.cache_read,
            cache_creation_input_tokens=verdict.cache_creation,
            cache_outcome=verdict.cache_outcome,
            is_api_error=verdict.is_api_error,
            api_error_status=verdict.api_error_status)

    if verdict.status == "reached":
        # The budget is spent HERE, not at confirm. Delivery success is not
        # model success, and spending at confirm burned the last budget slot on
        # turns that never reached a model.
        arm.confirmed_count += 1
        arm.publish()
        if model_budget(arm.model) != "unbounded" and arm.confirmed_count >= arm.count_budget:
            return "count_exhausted"
        return "emitted"

    if verdict.status == "not-reached":
        # A limit/overload response: 0/0 usage. Non-terminal. Keep the budget,
        # keep the daemon, remember the failing row as the resume watermark.
        arm.suspended = True
        arm.suspension_reason = "suspended_limit"
        arm.status = "suspended"
        arm.watermark_assistant_uuid = verdict.assistant_uuid
        arm.resume_candidate_uuid = None
        arm.publish()
        return "suspended"

    # no-verdict / pending: stay armed, spend nothing, wait for a normal window.
    arm.publish()
    return "emitted"


def read_jsonl_tail_safe(path: Path) -> list[dict]:
    try:
        return read_jsonl_tail(path)
    except OSError:
        return []


def wait_for_submission(transcript: Path, nonce: str, window_ms: int,
                        cursor: int = 0,
                        sleep: Callable[[float], None] = time.sleep) -> ConfirmResult:
    """Poll the transcript for our nonce until the window expires."""
    deadline = now_ms() + window_ms
    while True:
        rows = read_jsonl_tail_safe(transcript)[cursor:]
        result = inspect_submission(rows, nonce)
        if result.status != "not_confirmed":
            return result
        if now_ms() >= deadline:
            return ConfirmResult("not_confirmed")
        sleep(CONFIRM_POLL_MS / 1000)


def wait_for_verdict(transcript: Path, nonce: str, injected_uuid: Optional[str],
                     window_ms: int,
                     sleep: Callable[[float], None] = time.sleep) -> Verdict:
    deadline = now_ms() + window_ms
    while True:
        rows = read_jsonl_tail_safe(transcript)
        verdict = classify_verdict(rows, nonce, injected_uuid)
        if verdict.status not in ("pending",):
            return verdict
        if now_ms() >= deadline:
            return Verdict("no-verdict", "usage_not_found",
                           injected_user_uuid=injected_uuid)
        sleep(CONFIRM_POLL_MS / 1000)


#: Tick outcomes that end the daemon, mapped to their terminal reason.
TERMINAL_OUTCOMES = {
    "past_ttl_cliff": "cold_missed",
    "delivery_failed": "delivery_failure",
    "count_exhausted": "count_exhausted",
    "model_ineligible": "model_ineligible",
}


def run(arm: Arm, max_ticks: Optional[int] = None,
        sleep: Callable[[float], None] = time.sleep) -> str:
    """The loop. Returns the terminal reason."""
    arm.arm()
    ticks = 0
    while True:
        if max_ticks is not None and ticks >= max_ticks:
            return "max_ticks"
        sleep(arm.tick_ms / 1000)
        ticks += 1
        outcome = tick(arm, now_ms())

        if outcome in TERMINAL_OUTCOMES:
            reason = TERMINAL_OUTCOMES[outcome]
            arm.terminate(reason)
            return reason
        if outcome == "no_transcript" and not arm.natal:
            arm.terminate("missing_transcript")
            return "missing_transcript"
        if outcome == "not_live":
            arm.dead_ticks += 1
            if arm.dead_ticks >= DEAD_TICKS_BEFORE_TERMINAL:
                arm.terminate("session_dead")
                return "session_dead"
        else:
            arm.dead_ticks = 0
        arm.publish()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="keep-warm daemon for one Claude Code session")
    p.add_argument("--sid", required=True)
    p.add_argument("--transcript", required=True)
    p.add_argument("--count", type=int, default=DEFAULT_UNATTENDED_COUNT)
    p.add_argument("--fire-at-min", type=float, default=DEFAULT_FIRE_AT_MS / MINUTE_MS)
    p.add_argument("--cold-at-min", type=float, default=DEFAULT_COLD_AT_MS / MINUTE_MS)
    p.add_argument("--tick-sec", type=float, default=DEFAULT_TICK_SEC)
    p.add_argument("--transport", choices=("dry-run", "wake-file", "tmux"), default="dry-run")
    p.add_argument("--state-dir", default=str(Path.home() / ".keepwarm" / "state"))
    p.add_argument("--ledger", default=str(Path.home() / ".keepwarm" / "keepwarm.jsonl"))
    p.add_argument("--sessions-dir", default=str(Path.home() / ".claude" / "sessions"))
    p.add_argument("--wake-dir", default=str(Path.home() / ".claude" / "wake-request"))
    p.add_argument("--tmux-pane", default=None)
    p.add_argument("--arm-id", default=None)
    p.add_argument("--arm-source", default="start",
                   choices=("start", "birth", "rearm", "all_sweep"))
    p.add_argument("--natal", action="store_true",
                   help="start in the non-firing observation state (birth lane)")
    p.add_argument("--once", action="store_true", help="run a single tick and exit")
    p.add_argument("--max-ticks", type=int, default=None)
    p.add_argument("--dry-run-sink", default=None)
    p.add_argument("--dry-run-echo", action="store_true",
                   help="dry-run only: append a simulated user+assistant pair so a "
                        "full fire->confirm->verdict cycle can be demonstrated")
    p.add_argument("--no-sleep", action="store_true",
                   help="do not sleep between ticks (demo/test)")
    return p


def arm_from_args(args: argparse.Namespace) -> Arm:
    count = max(1, min(MAX_COUNT, args.count))
    return Arm(
        sid=args.sid,
        arm_id=args.arm_id or f"arm_{uuid.uuid4().hex[:10]}",
        transcript=Path(args.transcript),
        state_dir=Path(args.state_dir).expanduser(),
        ledger=Path(args.ledger).expanduser(),
        transport=build_transport(args),
        sessions_dir=Path(args.sessions_dir).expanduser(),
        count_budget=count,
        fire_at_ms=int(args.fire_at_min * MINUTE_MS),
        cold_at_ms=int(args.cold_at_min * MINUTE_MS),
        tick_ms=int(args.tick_sec * 1000),
        natal=args.natal,
        arm_source=args.arm_source,
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    arm = arm_from_args(args)
    sleep = (lambda _s: None) if args.no_sleep else time.sleep
    if args.once:
        arm.arm()
        outcome = tick(arm, now_ms())
        print(json.dumps({"outcome": outcome, "state": arm.snapshot()},
                         ensure_ascii=False, indent=2))
        return 0
    reason = run(arm, max_ticks=args.max_ticks, sleep=sleep)
    print(json.dumps({"terminal_reason": reason, "state": arm.snapshot()},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
