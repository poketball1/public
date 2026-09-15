#!/usr/bin/env python3
"""cache_clock.py — the honest cache clock for live sessions.

WHAT IT MEASURES
    For every transcript touched in the last N hours, three different "how idle is
    this session" clocks, and the verdict a keep-warm daemon would draw from them:

      idle_cache   minutes since the last NON-SIDECHAIN assistant row with positive
                   cache usage (read > 0 or creation > 0).   <- the real TTL clock
      idle_row     minutes since the last non-sidechain row of any real kind
                   (user row, or assistant row whose model is not "<synthetic>").
      idle_mtime   minutes since the file's mtime.
      effective    idle_cache ?? idle_row ?? idle_mtime      (first non-null wins)

    Verdict against --fire-at / --cold-at:
      warm  effective < fire-at        nothing to do
      due   fire-at <= eff < cold-at   inject now if you want to keep the cache
      cold  effective >= cold-at       the body cache is presumed dead; waking the
                                       session now pays a full rewrite, so DON'T

WHY THE THREE CLOCKS DIFFER, AND WHY ONLY ONE IS HONEST
    This is the single most expensive bug we shipped in this area, so it is worth
    spelling out. A keep-warm daemon injects a turn; the API answers 429 or 529;
    the harness writes a synthetic assistant row with usage 0/0. The cache was NOT
    refreshed. But the *injected user row* is a real row, so a clock built on "last
    row timestamp" jumps back to zero. The daemon then believes the session is 50
    minutes old forever, the cold-cliff guard never fires, and every subsequent
    injection re-pays the whole context. Our measurement (2026-08-13, one day):
    12 overload turns, all on injected turns, 7 measurable ones all with
    cache_read == 0 and cache_creation 217k-554k -- 2.6M tokens re-written in a day,
    while the ledger recorded "delivered" every time.
    The fix is one predicate: only a row that PROVES the model processed tokens may
    advance the clock. That proof is positive cache usage on an assistant row.
    User rows cannot advance it. Synthetic/error rows cannot advance it (their usage
    is 0/0, so they fail the test naturally rather than by a model-name blacklist).
    mtime cannot be the clock either: hooks, title writers and the harness itself
    append non-model rows, so mtime under-reports idleness. It is the last resort
    only, for a file we could not parse.
    Sidechain (subagent) rows are skipped: a subagent turn runs on its own 5m-TTL
    cache and does not refresh the main thread's 1h entry.

    This is exactly the predicate the keep-warm daemon uses. If you build one, build
    it on this function, not on mtime and not on "last row".

TAIL SIZE IS A CORRECTNESS PARAMETER, NOT A PERFORMANCE ONE
    A session with large tool outputs can push every assistant row out of a small
    tail. Then both honest clocks read null, the tool falls back to mtime, and mtime
    UNDER-reports idleness -- so a dead session looks young and a daemon silently
    stops firing. Measured on this machine (2026-09-15, same instant):

      tail 256KB   <sid-a>   cache -       row -       mtime 14.2   -> warm  (WRONG)
      tail 2MB     <sid-a>   cache 14149.1 row 8894.3  mtime 14.4   -> cold  (right)

    So this tool ESCALATES: it re-reads with a larger tail (doubling up to
    --max-tail-bytes) whenever the cache clock came back null and the file is bigger
    than what was read. `--no-escalate` reproduces a fixed-window daemon exactly.

USAGE
    python3 cache_clock.py                       # sessions touched in the last 6h
    python3 cache_clock.py --hours 24 --fire-at 50 --cold-at 57
    python3 cache_clock.py --json

Python 3.10+, stdlib only. Reads only the last --tail-bytes of each file.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_TAIL_BYTES = 256 * 1024     # what our daemon reads; ~150-400 rows


def parse_ts(text) -> float | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def is_user_row(row: dict) -> bool:
    return row.get("type") == "user" or (row.get("message") or {}).get("role") == "user"


def is_assistant_row(row: dict) -> bool:
    return row.get("type") == "assistant" or (row.get("message") or {}).get("role") == "assistant"


def is_real_assistant_row(row: dict) -> bool:
    return is_assistant_row(row) and (row.get("message") or {}).get("model") != "<synthetic>"


def read_tail_rows(path: Path, max_bytes: int):
    """Last <= max_bytes of a JSONL file, parsed. The first line is dropped when
    the read started mid-file -- it is a fragment, not a row."""
    size = path.stat().st_size
    length = min(size, max_bytes)
    start = size - length
    with path.open("rb") as handle:
        handle.seek(start)
        blob = handle.read(length)
    lines = blob.split(b"\n")
    if start > 0 and lines:
        lines = lines[1:]
    rows = []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except Exception:
            continue          # a torn last line while the session is writing
    return rows


def tail_facts(rows, now: float) -> dict:
    """Mirror of the daemon's transcriptTailFacts()."""
    last_row_ts = None
    last_cache_ts = None
    last_model = None
    last_outcome = None
    last_error = None
    for row in rows:
        if row.get("isSidechain") is True:
            continue
        ts = parse_ts(row.get("timestamp"))
        if ts is not None and is_assistant_row(row):
            usage = (row.get("message") or {}).get("usage") or {}
            read = int(usage.get("cache_read_input_tokens") or 0)
            creation = int(usage.get("cache_creation_input_tokens") or 0)
            if read > 0 or creation > 0:
                last_cache_ts = ts
                last_outcome = "hit" if read >= creation else "rewrite"
        if ts is not None and (is_user_row(row) or is_real_assistant_row(row)):
            last_row_ts = ts
        if is_assistant_row(row):
            model = (row.get("message") or {}).get("model")
            if isinstance(model, str) and model and model != "<synthetic>":
                last_model = model
            if row.get("isApiErrorMessage"):
                last_error = row.get("apiErrorStatus")
    return {
        "idle_row_min": None if last_row_ts is None else (now - last_row_ts) / 60.0,
        "idle_cache_min": None if last_cache_ts is None else (now - last_cache_ts) / 60.0,
        "last_model": last_model,
        "last_cache_outcome": last_outcome,
        "last_api_error_status": last_error,
    }


def fmt(value) -> str:
    return "-" if value is None else f"{value:.1f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projects-dir", default="~/.claude/projects")
    ap.add_argument("--project", default=None, help="restrict to one munged project dir name")
    ap.add_argument("--hours", type=float, default=6.0, help="only files touched this recently (default: %(default)s)")
    ap.add_argument("--fire-at", type=float, default=50.0, help="minutes: inject at or past this (default: %(default)s)")
    ap.add_argument("--cold-at", type=float, default=57.0, help="minutes: presume the cache dead (default: %(default)s)")
    ap.add_argument("--tail-bytes", type=int, default=DEFAULT_TAIL_BYTES,
                    help="first read size per file (default: %(default)s)")
    ap.add_argument("--max-tail-bytes", type=int, default=8 * 1024 * 1024,
                    help="escalation ceiling (default: %(default)s)")
    ap.add_argument("--no-escalate", action="store_true",
                    help="never re-read with a larger tail -- reproduces a fixed-window daemon")
    ap.add_argument("--include-subagents", action="store_true",
                    help="also list <sid>/subagents/agent-*.jsonl (informational; those run on 5m TTL)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.projects_dir).expanduser()
    now = datetime.now(timezone.utc).timestamp()
    horizon = now - args.hours * 3600

    paths = []
    for project in sorted(p for p in root.iterdir() if p.is_dir()):
        if args.project and project.name != args.project:
            continue
        paths.extend(project.glob("*.jsonl"))
        if args.include_subagents:
            paths.extend(project.glob("*/subagents/*.jsonl"))

    report = []
    for path in paths:
        stat = path.stat()
        if stat.st_mtime < horizon:
            continue
        read_bytes = args.tail_bytes
        try:
            rows = read_tail_rows(path, read_bytes)
            facts = tail_facts(rows, now)
            while (not args.no_escalate and facts["idle_cache_min"] is None
                   and read_bytes < min(args.max_tail_bytes, stat.st_size)):
                read_bytes = min(read_bytes * 4, args.max_tail_bytes, stat.st_size)
                rows = read_tail_rows(path, read_bytes)
                facts = tail_facts(rows, now)
        except Exception as exc:
            facts = {"idle_row_min": None, "idle_cache_min": None, "last_model": None,
                     "last_cache_outcome": None, "last_api_error_status": None,
                     "error": type(exc).__name__}
            rows = []
        idle_mtime = (now - stat.st_mtime) / 60.0
        effective = facts["idle_cache_min"]
        source = "cache"
        if effective is None:
            effective, source = facts["idle_row_min"], "row"
        if effective is None:
            effective, source = idle_mtime, "mtime"
        verdict = "warm" if effective < args.fire_at else ("due" if effective < args.cold_at else "cold")
        def rounded(value):
            return None if value is None else round(value, 2)

        report.append({
            "session": path.stem,
            "kind": "subagent" if path.parent.name == "subagents" else "main",
            "project": path.parts[len(root.parts)],
            "idle_cache_min": rounded(facts["idle_cache_min"]),
            "idle_row_min": rounded(facts["idle_row_min"]),
            "idle_mtime_min": rounded(idle_mtime),
            "effective_idle_min": rounded(effective),
            "clock_source": source,
            "verdict": verdict,
            "last_model": facts["last_model"],
            "last_cache_outcome": facts["last_cache_outcome"],
            "last_api_error_status": facts["last_api_error_status"],
            "tail_rows": len(rows),
            "tail_bytes_read": read_bytes,
        })

    report.sort(key=lambda r: r["effective_idle_min"])
    if args.json:
        print(json.dumps({"now": datetime.now(timezone.utc).isoformat(),
                          "fire_at": args.fire_at, "cold_at": args.cold_at,
                          "sessions": report}, indent=1))
        return 0

    print(f"# cache_clock  now={datetime.now().astimezone().isoformat(timespec='seconds')}  "
          f"fire-at={args.fire_at}m  cold-at={args.cold_at}m  tail={args.tail_bytes // 1024}KB"
          f"{'' if args.no_escalate else f' (escalating to {args.max_tail_bytes // 1024}KB)'}")
    print(f"# {len(report)} session file(s) touched in the last {args.hours}h")
    print()
    head = (f"{'session':<10} {'kind':<6} {'read':>6} {'cache':>7} {'row':>7} {'mtime':>7} {'eff':>7} "
            f"{'src':<6} {'verdict':<8} {'outcome':<8} {'model':<22} {'err':>4}")
    print(head)
    print("-" * len(head))
    for entry in report:
        print(f"{entry['session'][:8]:<10} {entry['kind'][:5]:<6} {entry['tail_bytes_read'] // 1024:>5}K "
              f"{fmt(entry['idle_cache_min']):>7} {fmt(entry['idle_row_min']):>7} "
              f"{fmt(entry['idle_mtime_min']):>7} {fmt(entry['effective_idle_min']):>7} "
              f"{entry['clock_source']:<6} {entry['verdict']:<8} "
              f"{(entry['last_cache_outcome'] or '-'):<8} {(entry['last_model'] or '-')[:22]:<22} "
              f"{(entry['last_api_error_status'] or '-'):>4}")
    print("-" * len(head))
    counts = {"warm": 0, "due": 0, "cold": 0}
    for entry in report:
        counts[entry["verdict"]] += 1
    print(f"warm {counts['warm']}   due {counts['due']}   cold {counts['cold']}")
    disagree = [e for e in report
                if e["idle_cache_min"] is not None and e["idle_row_min"] is not None
                and abs(e["idle_cache_min"] - e["idle_row_min"]) >= 1.0]
    if disagree:
        print()
        print("clock disagreement >= 1 min (the cache clock is the honest one):")
        for entry in disagree:
            print(f"  {entry['session'][:8]}  cache {entry['idle_cache_min']:.1f}m  "
                  f"row {entry['idle_row_min']:.1f}m  "
                  f"delta {entry['idle_cache_min'] - entry['idle_row_min']:+.1f}m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
