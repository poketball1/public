#!/usr/bin/env python3
"""keepwarm_ctl.py — the control surface: start | stop | status | all.

This is what a user (or a slash command) actually types. It owns no predicates:
every judgement about whether a session may be armed lives in
`keepwarm_daemon.py`, and this file only enumerates sessions, spawns daemons,
and prints lines a human can read.

    keepwarm_ctl.py start  --sid <sid> [--count 12]
    keepwarm_ctl.py stop   --sid <sid>
    keepwarm_ctl.py status [--sid <sid>]
    keepwarm_ctl.py all    [--count 24]

TWO RULES THAT COST US AN INCIDENT
----------------------------------
1. `stopped` HAS EXACTLY ONE AUTHOR: the `stop` subcommand. A daemon killed by
   a signal writes `signal_terminated`, never `stopped`. On 2026-09-08 a WSL
   shutdown SIGTERM'd 13 daemons seven minutes before a reboot; each wrote
   `stopped`, and every automatic actor afterwards skipped those 13 sessions as
   `opted_out` until a human noticed. An external signal is a death, not a
   decision.

2. `all` NEVER ARMS A COLD SESSION. Arming a session whose cache is already
   dead means the first fire pays a full rewrite. The sweep therefore refuses
   anything at or past the warm margin, and refuses anything whose clock would
   have to come from file mtime — mtime advances on sidechain and synthetic
   writes, so trusting it is how a cold session gets armed and then warmed.
   Every refusal is REPORTED with its reason; silent skips are how coverage
   holes hide.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from keepwarm_daemon import (           # noqa: E402
    DEFAULT_COUNT,
    DEFAULT_UNATTENDED_COUNT,
    DEFAULT_COLD_AT_MS,
    DEFAULT_FIRE_AT_MS,
    DEFAULT_TICK_SEC,
    MAX_COUNT,
    MINUTE_MS,
    append_ledger,
    atomic_write_json,
    inspect_transcript,
    is_arm_target,
    model_budget,
    now_ms,
    read_state,
    state_path,
    transcript_for,
)

DAEMON = Path(__file__).resolve().parent / "keepwarm_daemon.py"

#: Terminal statuses — an arm in one of these is not running any more.
TERMINAL_STATUSES = frozenset({
    "stopped", "session_dead", "delivery_failure", "count_exhausted",
    "cold_missed", "stale", "replaced", "model_ineligible",
    "signal_terminated", "missing_transcript",
})


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def clamp_count(value: Optional[int], fallback: int) -> int:
    if value is None:
        return fallback
    return max(1, min(MAX_COUNT, int(value)))


def pid_alive(pid: Optional[int]) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    return Path("/proc", str(pid)).exists()


def daemon_is_live(state: Optional[dict]) -> str:
    """alive | dead | indeterminate — identity, not just a PID.

    A PID alone is not identity: PIDs get reused, and a reused PID with a live
    process would make a dead arm look alive forever. We additionally require
    the recorded arm_id to appear in the process command line. When we cannot
    read /proc at all the answer is `indeterminate`, which BLOCKS the terminal
    transition rather than guessing — a probe error is not evidence of death.
    """
    if state is None:
        return "dead"
    if state.get("status") in TERMINAL_STATUSES:
        return "dead"
    pid = state.get("pid")
    if not pid_alive(pid):
        return "dead"
    try:
        cmdline = Path("/proc", str(pid), "cmdline").read_bytes().replace(b"\0", b" ").decode()
    except OSError:
        return "indeterminate"
    arm_id = state.get("arm_id") or ""
    sid = state.get("sid") or ""
    if arm_id and arm_id in cmdline and sid in cmdline:
        return "alive"
    return "dead"       # PID reuse: someone else owns this number now


def enumerate_sessions(sessions_dir: Path) -> list[dict]:
    """Live rows from the session registry, newest file order.

    Registry file: ~/.claude/sessions/<pid>.json, one per session process.
    Fields we use: sessionId, cwd, kind, entrypoint.
    """
    rows: list[dict] = []
    if not sessions_dir.is_dir():
        return rows
    for entry in sorted(sessions_dir.glob("*.json")):
        pid = entry.stem
        if not pid.isdigit():
            continue
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or not data.get("sessionId"):
            continue
        # A row whose PID is dead does not speak for the session. Reading
        # identity off a corpse is how a live interactive arm gets terminated
        # as "not an arm target".
        if not pid_alive(int(pid)):
            continue
        data["_pid"] = int(pid)
        rows.append(data)
    return rows


def spawn_daemon(sid: str, transcript: Path, count: int, args: argparse.Namespace,
                 natal: bool, arm_source: str, model: Optional[str]) -> dict:
    """Detach a daemon and return the snapshot we published for it."""
    arm_id = f"arm_{uuid.uuid4().hex[:10]}"
    state_dir = Path(args.state_dir).expanduser()
    state_dir.mkdir(parents=True, exist_ok=True)
    log_path = state_dir / f"{sid}.daemon.log"

    cmd = [
        sys.executable, str(DAEMON),
        "--sid", sid,
        "--transcript", str(transcript),
        "--count", str(count),
        "--arm-id", arm_id,
        "--arm-source", arm_source,
        "--fire-at-min", str(args.fire_at_min),
        "--cold-at-min", str(args.cold_at_min),
        "--tick-sec", str(args.tick_sec),
        "--transport", args.transport,
        "--state-dir", str(state_dir),
        "--ledger", str(Path(args.ledger).expanduser()),
        "--sessions-dir", str(Path(args.sessions_dir).expanduser()),
    ]
    if natal:
        cmd.append("--natal")
    if args.tmux_pane:
        cmd += ["--tmux-pane", args.tmux_pane]

    with log_path.open("ab") as log:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            # start_new_session == setsid(): the daemon survives the shell that
            # spawned it, and never receives the terminal's signals.
            start_new_session=True,
        )

    snapshot = {
        "sid": sid, "arm_id": arm_id, "pid": proc.pid, "arm_source": arm_source,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count_budget": count, "model": model,
        "budget_unbounded": model_budget(model) == "unbounded",
        "emit_count": 0, "confirmed_count": 0,
        "idle_ms": int(args.fire_at_min * MINUTE_MS),
        "tick_ms": int(args.tick_sec * 1000),
        "status": "starting", "natal": natal,
        "suspension_reason": None,
        "verdict_watermark_assistant_uuid": None,
        "resume_candidate_assistant_uuid": None,
        "last_delivery_nonce": None,
    }
    atomic_write_json(state_path(state_dir, sid), snapshot)
    return snapshot


def budget_glyph(state: dict) -> str:
    n = state.get("confirmed_count", 0)
    if state.get("budget_unbounded"):
        return f"{n}/∞"
    return f"{n}/{state.get('count_budget', '?')}"


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------

def cmd_start(args: argparse.Namespace) -> int:
    """Explicit, user-typed arm. This is the ONLY surface that may replace a
    live arm: when a human names a session, that outranks every automatic rule.
    """
    state_dir = Path(args.state_dir).expanduser()
    sessions_dir = Path(args.sessions_dir).expanduser()
    count = clamp_count(args.count, DEFAULT_COUNT)

    session = next((s for s in enumerate_sessions(sessions_dir)
                    if s["sessionId"] == args.sid), None)
    if session is None:
        print(f"skipped {args.sid[:8]} reason=session_not_live")
        return 0

    transcript = Path(args.transcript) if args.transcript else transcript_for(
        args.sid, session.get("cwd", ""), Path(args.claude_root).expanduser())
    if not transcript.exists():
        print(f"skipped {args.sid[:8]} reason=missing_transcript")
        return 0

    facts = inspect_transcript(transcript, now_ms())
    budget = model_budget(facts.last_assistant_model)
    if budget == "ineligible":
        # Below the policy floor. Refuse, and say the model — "it is cold" would
        # be a true statement about the clock and a misleading one about the sid.
        print(f"skipped {args.sid[:8]} reason=model_ineligible "
              f"model={facts.last_assistant_model}")
        return 0

    previous = read_state(state_path(state_dir, args.sid))
    if previous and daemon_is_live(previous) == "alive":
        _terminate_previous(previous, state_dir, Path(args.ledger).expanduser())

    snapshot = spawn_daemon(args.sid, transcript, count, args,
                            natal=False, arm_source="start",
                            model=facts.last_assistant_model)
    print(f"armed arm_id={snapshot['arm_id']} count_budget={budget_glyph(snapshot)}")
    return 0


def _terminate_previous(previous: dict, state_dir: Path, ledger: Path) -> None:
    pid = previous.get("pid")
    if isinstance(pid, int) and pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        for _ in range(30):
            if not pid_alive(pid):
                break
            time.sleep(0.1)
    append_ledger(ledger, {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "terminated", "lane": "arm",
        "sid": previous.get("sid"), "arm_id": previous.get("arm_id"),
        "reason": "replaced",
    })


def cmd_stop(args: argparse.Namespace) -> int:
    """Sticky opt-out. The one and only writer of `stopped`.

    It works whether or not an arm exists: a session that was never armed can
    still say "leave me out", and the marker is what carries that decision to
    every future automatic actor. That is why the marker is schema-identical to
    a real snapshot — every consumer already branches on terminal status first,
    so none of them probe a synthetic identity.
    """
    state_dir = Path(args.state_dir).expanduser()
    ledger = Path(args.ledger).expanduser()
    path = state_path(state_dir, args.sid)
    previous = read_state(path)

    if previous and daemon_is_live(previous) == "alive":
        pid = previous.get("pid")
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        for _ in range(50):
            if not pid_alive(pid):
                break
            time.sleep(0.1)
        else:
            # The daemon is still alive. Do NOT mint `stopped` on top of a
            # running arm — that would be a false opt-out over something that
            # keeps firing. Fail loudly; the user can retry.
            print(f"error {args.sid[:8]} reason=daemon_did_not_exit", file=sys.stderr)
            return 1
        append_ledger(ledger, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": "terminated", "lane": "arm", "sid": args.sid,
            "arm_id": previous.get("arm_id"), "reason": "signal_terminated",
        })

    marker = {
        "sid": args.sid,
        "arm_id": previous.get("arm_id") if previous else f"arm_optout_{uuid.uuid4().hex[:8]}",
        "pid": None,                      # "no pid" IS the marker discriminator
        "arm_source": "stop",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count_budget": previous.get("count_budget", 0) if previous else 0,
        "confirmed_count": previous.get("confirmed_count", 0) if previous else 0,
        "emit_count": previous.get("emit_count", 0) if previous else 0,
        "model": previous.get("model") if previous else None,
        "budget_unbounded": False,
        "natal": False,
        "status": "stopped",
        "suspension_reason": None,
        "verdict_watermark_assistant_uuid": None,
        "resume_candidate_assistant_uuid": None,
        "last_delivery_nonce": None,
        "idle_ms": None, "tick_ms": None,
    }
    atomic_write_json(path, marker)
    append_ledger(ledger, {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "terminated", "lane": "arm", "sid": args.sid,
        "arm_id": marker["arm_id"], "reason": "stopped",
        **({"reason_detail": "no_live_arm"} if not previous or previous.get("pid") is None else {}),
    })
    suffix = " reason=no_live_arm" if (not previous or previous.get("pid") is None) else ""
    print(f"stopped {args.sid[:8]}{suffix}")
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    """The hook-facing entry: birth (SessionStart) and rearm (Stop).

    Not a user command. It exists so the shell hooks own NO verdict — they
    validate a sid, take a lock, and call this. Every rule about whether an
    automatic actor may arm lives in `automatic_arm_plan`, which both hooks
    share, so they can never disagree about who is armed.
    """
    from keepwarm_daemon import automatic_arm_plan

    state_dir = Path(args.state_dir).expanduser()
    ledger = Path(args.ledger).expanduser()
    sessions_dir = Path(args.sessions_dir).expanduser()
    claude_root = Path(args.claude_root).expanduser()
    source = args.source

    def skip(reason: str, **extra) -> int:
        append_ledger(ledger, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": f"{source}_skipped", "lane": "arm", "sid": args.sid,
            "reason": reason, **extra,
        })
        print(f"skipped {args.sid[:8]} reason={reason}")
        return 0

    previous = read_state(state_path(state_dir, args.sid))
    liveness = daemon_is_live(previous) if previous else None

    # Resolve the transcript. During the birth window the registry row may not
    # exist yet, which is why the hook hands us `--transcript`: without it every
    # newborn would be skipped for a missing transcript.
    session = next((s for s in enumerate_sessions(sessions_dir)
                    if s["sessionId"] == args.sid), None)
    transcript: Optional[Path] = None
    if args.transcript:
        transcript = Path(args.transcript)
    elif session is not None:
        transcript = transcript_for(args.sid, session.get("cwd", ""), claude_root)

    # Read the model only when it can change the answer. On the vast majority of
    # Stop hooks the answer is "a live arm already owns this sid", and no model
    # observation can change that — so we do not open the transcript for it.
    model: Optional[str] = None
    budget: Optional[str] = None
    if transcript and transcript.exists() and (previous is None or liveness != "alive"):
        try:
            model = inspect_transcript(transcript, now_ms()).last_assistant_model
            budget = model_budget(model)
        except OSError:
            model, budget = None, None
        if budget == "ineligible":
            # Skip BEFORE spawning anything: an automatic actor that spawns a
            # daemon only for it to terminate itself two ticks later is churn
            # with a ledger row attached.
            return skip("model_ineligible", model=model)

    plan = automatic_arm_plan(previous, nonterminal_liveness=liveness, budget=budget)
    if plan["action"] == "skip":
        return skip(plan["reason"], prior_status=(previous or {}).get("status"))

    if transcript is None:
        return skip("missing_transcript")

    natal = True   # both automatic surfaces arm in the non-firing state
    snapshot = spawn_daemon(args.sid, transcript, plan["count"], args,
                            natal=natal, arm_source=source, model=model)
    append_ledger(ledger, {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "armed" if source == "birth" else "rearmed", "lane": "arm",
        "sid": args.sid, "arm_id": snapshot["arm_id"], "arm_source": source,
        "natal": True, "count_budget": plan["count"],
        "recovery_reason": plan.get("recovery_reason"),
        "prior_id": (previous or {}).get("arm_id"),
        "prior_confirmed_count": (previous or {}).get("confirmed_count"),
        "model": model,
    })
    print(f"armed arm_id={snapshot['arm_id']} count_budget={budget_glyph(snapshot)} natal=true")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state_dir = Path(args.state_dir).expanduser()
    if args.sid:
        state = read_state(state_path(state_dir, args.sid))
        print(json.dumps({"sid": args.sid, "state": state,
                          "daemon": daemon_is_live(state)},
                         ensure_ascii=False, indent=2))
        return 0
    rows = []
    for path in sorted(state_dir.glob("*.state.json")):
        state = read_state(path)
        if state is None:
            continue
        rows.append({"sid": state.get("sid", "?")[:8],
                     "status": state.get("status"),
                     "budget": budget_glyph(state),
                     "model": state.get("model"),
                     "daemon": daemon_is_live(state)})
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    """Arm every live interactive session that is still warm.

    Each gate below is reported, never silent. The cold gate especially: the
    day a coverage hole opens, the ledger has to say which sessions fell out
    and why — we lost 16 of 23 live sessions once and only found out because a
    human noticed a missing glyph.
    """
    state_dir = Path(args.state_dir).expanduser()
    sessions_dir = Path(args.sessions_dir).expanduser()
    claude_root = Path(args.claude_root).expanduser()
    count = clamp_count(args.count, DEFAULT_UNATTENDED_COUNT)
    warm_cutoff_ms = int(args.cold_at_min * MINUTE_MS)

    armed: list[str] = []
    skipped: list[dict] = []
    lines: list[str] = []

    for session in enumerate_sessions(sessions_dir):
        sid = session["sessionId"]
        sid8 = sid[:8]
        reason: Optional[str] = None
        model = "-"
        idle_min: Optional[int] = None

        existing = read_state(state_path(state_dir, sid))

        # Gate ①: the user's own opt-out outranks everything, including a
        # model we would otherwise keep warm forever.
        if existing and existing.get("status") == "stopped":
            reason = "opted_out"

        # Gate ②: a live arm already owns this sid — arming again would churn.
        # A suspended arm is sticky-skipped too: replacing it would throw away
        # its remaining budget and its resume watermark.
        if reason is None and existing and daemon_is_live(existing) == "alive":
            if existing.get("status") == "suspended":
                reason = existing.get("suspension_reason") or "suspended_limit"
            else:
                reason = f"existing_arm:{existing.get('status')}"

        # Gate ③: identity. Two discriminators, both fail-closed.
        if reason is None and not is_arm_target(session):
            reason = f"non_interactive:{session.get('kind')}/{session.get('entrypoint')}"

        transcript = transcript_for(sid, session.get("cwd", ""), claude_root)
        facts = None
        if reason is None or str(reason).startswith("suspended"):
            # Resolve observation BEFORE any early return, so a sticky-skipped
            # row is still identifiable in the report. A line of dashes is not
            # a report.
            try:
                facts = inspect_transcript(transcript, now_ms())
                model = facts.last_assistant_model or "unknown"
                if facts.effective_idle_ms is not None:
                    idle_min = max(0, facts.effective_idle_ms // MINUTE_MS)
            except OSError:
                facts = None

        if reason is None and facts is None:
            reason = "missing_transcript"

        # Gate ④: identity before timing — a session the policy does not keep
        # warm is skipped for WHAT IT IS, not for how cold it happens to be.
        if reason is None and model_budget(facts.last_assistant_model) == "ineligible":
            reason = "model_ineligible"

        # Gate ⑤: THE COLD GATE. Two clauses, and the first is the subtle one:
        # with no cache row and no activity row in the tail, the effective clock
        # degrades to file mtime, which sidechain and synthetic writes keep
        # fresh. Arming on that could warm a genuinely cold session.
        if reason is None and (not facts.has_row_evidence
                               or (facts.effective_idle_ms or 0) >= warm_cutoff_ms):
            reason = "cold_or_near_cliff"

        # Gate ⑥: an open decision dialog. Note arming is not injecting — a
        # merely mid-turn session is still armed, and the tick gate decides each
        # individual fire. Only a visibly open dialog blocks arming.
        if reason is None and facts.turn_state == "dialog_pending":
            reason = "dialog_pending"

        if reason:
            skipped.append({"sid8": sid8, "reason": reason, "model": model})
            lines.append(f"{sid8} | {model:24s} | idle={idle_min if idle_min is not None else '-':>4} "
                         f"| skipped: {reason}")
            continue

        snapshot = spawn_daemon(sid, transcript, count, args, natal=False,
                                arm_source="all_sweep",
                                model=facts.last_assistant_model)
        armed.append(sid8)
        lines.append(f"{sid8} | {model:24s} | idle={idle_min:>4} "
                     f"| armed {budget_glyph(snapshot)}")

    append_ledger(Path(args.ledger).expanduser(), {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "all_sweep", "lane": "arm", "sid": "all",
        "requested_count": count, "armed": armed, "skipped": skipped,
    })
    print("\n".join(lines) if lines else "(no live interactive sessions)")
    return 0


# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="keep-warm control surface")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--state-dir", default=str(Path.home() / ".keepwarm" / "state"))
        sp.add_argument("--ledger", default=str(Path.home() / ".keepwarm" / "keepwarm.jsonl"))
        sp.add_argument("--sessions-dir", default=str(Path.home() / ".claude" / "sessions"))
        sp.add_argument("--claude-root", default=str(Path.home() / ".claude"))
        sp.add_argument("--fire-at-min", type=float, default=DEFAULT_FIRE_AT_MS / MINUTE_MS)
        sp.add_argument("--cold-at-min", type=float, default=DEFAULT_COLD_AT_MS / MINUTE_MS)
        sp.add_argument("--tick-sec", type=float, default=DEFAULT_TICK_SEC)
        sp.add_argument("--transport", choices=("dry-run", "wake-file", "tmux"),
                        default="wake-file")
        sp.add_argument("--tmux-pane", default=None)

    sp = sub.add_parser("start", help="arm one session (explicit; may replace a live arm)")
    sp.add_argument("--sid", required=True)
    sp.add_argument("--count", type=int, default=None)
    sp.add_argument("--transcript", default=None)
    common(sp)

    sp = sub.add_parser("stop", help="sticky opt-out for one session")
    sp.add_argument("--sid", required=True)
    common(sp)

    sp = sub.add_parser("status", help="show arm state")
    sp.add_argument("--sid", default=None)
    common(sp)

    sp = sub.add_parser("all", help="arm every live interactive session that is still warm")
    sp.add_argument("--count", type=int, default=None)
    common(sp)

    # Hook-facing, not a user command. It exists so the shell hooks own no
    # verdict; see cmd_auto.
    sp = sub.add_parser("auto", help=argparse.SUPPRESS)
    sp.add_argument("--sid", required=True)
    sp.add_argument("--source", required=True, choices=("birth", "rearm"))
    sp.add_argument("--transcript", default=None)
    sp.add_argument("--count", type=int, default=None)
    common(sp)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return {
        "start": cmd_start, "stop": cmd_stop,
        "status": cmd_status, "all": cmd_all, "auto": cmd_auto,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
