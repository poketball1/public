#!/usr/bin/env python3
"""codex_cache_curve.py — the same gap -> cold-probability curve for Codex rollouts.

APPENDIX SCRIPT. The other three read Claude Code transcripts; this one reads the
Codex CLI's rollout logs, so you can compare two harnesses with one method.

WHAT IT MEASURES
    Per thread, per API call: the cached fraction of the input
        ratio = cached_input_tokens / input_tokens
    and the gap in minutes to the previous call of the SAME thread. Bucketed by
    gap, reported per model as n / warm% / cold% / median ratio.

DATA SHAPE (verified by reading real rollouts, 2026-08 and 2026-09)
    ~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<thread-id>.jsonl, one JSON object
    per line, each with a top-level "type":

      session_meta   payload.id                 thread id (== the filename suffix)
                     payload.thread_source      "subagent" when spawned by another
                     payload.agent_role         role name, when a subagent
                     payload.parent_thread_id   parent, when a subagent
      turn_context   payload.model              the model for the turns that follow
                     payload.effort             reasoning effort
      event_msg      payload.type == "token_count"
                     payload.info.last_token_usage.{input_tokens,cached_input_tokens,
                                                    output_tokens,...}
                                                one entry per API call  <- the source
      token_usage_record                        newer builds only (absent in our
                     payload.usage.{...}        2026-08 rollouts); same numbers.
                                                We read token_count so the script
                                                works across versions.

    `input_tokens` here is the FULL prompt (cached portion included) -- unlike the
    Claude transcript, where `input_tokens` is already the uncached remainder. So
    the Codex hit ratio is cached/input, while the Claude one is
    read/(read+creation). Do not copy one formula into the other tool.

PREDICATES
  * one call == one token_count event with input_tokens >= --floor. The floor
    (default 20000) drops trivial calls -- title generation, tiny follow-ups --
    whose ratio is dominated by a prompt too small to have a meaningful prefix.
  * consecutive token_count events with an identical last_token_usage tuple are
    the same call re-emitted; only the first is kept.
  * warm == ratio > 0.8, cold == ratio < 0.2. As on the Claude side the
    distribution is bimodal (the entry lives or it is gone), so the two masses are
    the reading, not the mean. Our 2026-09-15 run over 28,279 calls: 97.4% warm,
    1.2% cold, median 0.993.
  * gap is measured between calls of one thread. A cold first call of a thread is
    NOT a gap phenomenon (there was nothing to keep warm), so it is reported
    separately as `thread_head` rather than folded into a bucket.

USAGE
    python3 codex_cache_curve.py --since 2026-09-08
    python3 codex_cache_curve.py --since 2026-09-01 --by role
    python3 codex_cache_curve.py --since 2026-09-08 --json > codex-curve.json

Python 3.10+, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

BUCKETS = [
    (0, 2, "<2m"), (2, 5, "2-5m"), (5, 15, "5-15m"), (15, 30, "15-30m"),
    (30, 40, "30-40m"), (40, 45, "40-45m"), (45, 50, "45-50m"), (50, 55, "50-55m"),
    (55, 60, "55-60m"), (60, 70, "60-70m"), (70, 90, "70-90m"), (90, 1e9, "90m+"),
]
WARM_AT = 0.8
COLD_AT = 0.2
TOKEN_MARKER = b'"token_count"'


def parse_tz(spec: str) -> timezone:
    if spec in ("local", ""):
        return timezone(datetime.now().astimezone().utcoffset() or timedelta(0))
    if spec.lower() in ("utc", "z"):
        return timezone.utc
    sign = -1 if spec[0] == "-" else 1
    body = spec.lstrip("+-")
    hh, _, mm = body.partition(":")
    return timezone(sign * timedelta(hours=int(hh), minutes=int(mm or 0)))


def parse_bound(text: str, tz: timezone) -> datetime:
    text = text.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        dt = datetime.fromisoformat(text + "T00:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def parse_ts(text) -> float | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def bucket_of(minutes: float) -> str | None:
    for lo, hi, name in BUCKETS:
        if lo <= minutes < hi:
            return name
    return None


def read_rollout(path: Path, floor: int):
    """Stream one rollout. Return (meta, calls). calls are (ts, model, input, cached)."""
    meta = {"thread_id": path.stem.split("-", 2)[-1], "thread_source": None,
            "agent_role": None, "parent_thread_id": None}
    model = None
    calls = []
    last_tuple = None
    with path.open("rb") as handle:
        for raw in handle:
            if b'"session_meta"' in raw or b'"turn_context"' in raw:
                try:
                    row = json.loads(raw)
                except Exception:
                    continue
                payload = row.get("payload") or {}
                if row.get("type") == "session_meta":
                    meta["thread_id"] = payload.get("id") or meta["thread_id"]
                    meta["thread_source"] = payload.get("thread_source")
                    meta["agent_role"] = payload.get("agent_role")
                    meta["parent_thread_id"] = payload.get("parent_thread_id")
                elif row.get("type") == "turn_context":
                    model = payload.get("model") or model
                continue
            if TOKEN_MARKER not in raw:
                continue
            try:
                row = json.loads(raw)
            except Exception:
                continue
            payload = row.get("payload") or {}
            if payload.get("type") != "token_count":
                continue
            info = payload.get("info") or {}
            usage = info.get("last_token_usage") or {}
            total_in = int(usage.get("input_tokens") or 0)
            cached = int(usage.get("cached_input_tokens") or 0)
            out = int(usage.get("output_tokens") or 0)
            signature = (total_in, cached, out)
            if signature == last_tuple:
                continue                   # same call re-emitted
            last_tuple = signature
            if total_in < floor:
                continue
            ts = parse_ts(row.get("timestamp"))
            if ts is None:
                continue
            calls.append((ts, model or "unknown", total_in, cached))
    calls.sort(key=lambda c: c[0])
    return meta, calls


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sessions-dir", default="~/.codex/sessions")
    ap.add_argument("--since", default=None)
    ap.add_argument("--until", default=None)
    ap.add_argument("--tz", default="local")
    ap.add_argument("--floor", type=int, default=20000,
                    help="ignore calls whose total input is below this (default: %(default)s)")
    ap.add_argument("--by", default="model", choices=("model", "role", "all"))
    ap.add_argument("--min-n", type=int, default=5, help="hide buckets thinner than this")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tz = parse_tz(args.tz)
    since = parse_bound(args.since, tz) if args.since else None
    until = parse_bound(args.until, tz) if args.until else None
    root = Path(args.sessions_dir).expanduser()

    # per (group, bucket) -> stats ; plus a thread_head bucket per group
    table = defaultdict(lambda: defaultdict(lambda: {"n": 0, "warm": 0, "cold": 0, "ratios": []}))
    stats = {"files": 0, "files_skipped_mtime": 0, "calls": 0, "pairs": 0, "thread_heads": 0}

    for path in sorted(root.rglob("rollout-*.jsonl")):
        if since is not None:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if mtime < since:
                stats["files_skipped_mtime"] += 1
                continue
        meta, calls = read_rollout(path, args.floor)
        if not calls:
            continue
        stats["files"] += 1
        if args.by == "model":
            group_of = lambda call: call[1]
        elif args.by == "role":
            label = meta["agent_role"] or (meta["thread_source"] or "root")
            group_of = lambda call, label=label: label
        else:
            group_of = lambda call: "all"

        for index, call in enumerate(calls):
            ts, model, total_in, cached = call
            if until is not None and ts >= until.timestamp():
                continue
            if since is not None and ts < since.timestamp():
                continue
            ratio = cached / total_in if total_in else 0.0
            stats["calls"] += 1
            group = group_of(call)
            if index == 0:
                stats["thread_heads"] += 1
                slot = table[group]["thread_head"]
            else:
                gap = (ts - calls[index - 1][0]) / 60.0
                name = bucket_of(gap)
                if name is None:
                    continue
                stats["pairs"] += 1
                slot = table[group][name]
            slot["n"] += 1
            slot["warm"] += 1 if ratio > WARM_AT else 0
            slot["cold"] += 1 if ratio < COLD_AT else 0
            slot["ratios"].append(ratio)

    out = {"window": {"since": since.isoformat() if since else None,
                      "until": until.isoformat() if until else None, "tz": args.tz},
           "floor": args.floor, "by": args.by, "coverage": stats, "groups": {}}
    names = [name for _, _, name in BUCKETS] + ["thread_head"]
    for group, rows in table.items():
        total = sum(slot["n"] for slot in rows.values())
        block = {}
        for name in names:
            slot = rows.get(name)
            if not slot or slot["n"] < args.min_n:
                continue
            block[name] = {
                "n": slot["n"],
                "warm_pct": round(100.0 * slot["warm"] / slot["n"], 1),
                "cold_pct": round(100.0 * slot["cold"] / slot["n"], 1),
                "median": round(statistics.median(slot["ratios"]), 3),
            }
        out["groups"][group] = {"calls": total, "buckets": block}

    if args.json:
        print(json.dumps(out, indent=1))
        return 0

    print(f"# codex_cache_curve  by={args.by}  floor={args.floor}  tz={args.tz}")
    print(f"# window {out['window']['since']} .. {out['window']['until']}")
    print(f"# rollouts={stats['files']} (mtime-skipped {stats['files_skipped_mtime']})  "
          f"calls={stats['calls']:,}  gap-pairs={stats['pairs']:,}  thread-heads={stats['thread_heads']:,}")
    for group, block in sorted(out["groups"].items(), key=lambda kv: -kv[1]["calls"]):
        if not block["buckets"]:
            continue
        print()
        print(f"== {group}   ({block['calls']:,} calls)")
        head = f"{'gap bucket':<12} {'n':>7} {'warm%':>7} {'cold%':>7} {'median':>8}"
        print(head)
        print("-" * len(head))
        for name, slot in block["buckets"].items():
            print(f"{name:<12} {slot['n']:>7,} {slot['warm_pct']:>7.1f} "
                  f"{slot['cold_pct']:>7.1f} {slot['median']:>8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
