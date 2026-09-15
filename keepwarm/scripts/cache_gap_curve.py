#!/usr/bin/env python3
"""cache_gap_curve.py — idle gap -> cold probability. Find your own TTL cliff.

WHAT IT MEASURES
    Inside one thread, take the API calls that actually touched the cache, in
    timestamp order. For each consecutive pair (prev, cur) compute
        gap  = cur.ts - prev.ts                    (minutes of idle)
        body = cur.read / (cur.read + cur.creation) (body-survival ratio)
    Bucket by gap and report, per bucket: n, warm%, cold%, and p10/median body.
    The curve's knee is the effective TTL of your prompt cache.

WHY warm%/cold% AND NOT THE MEAN
    The body-survival ratio is BIMODAL, not continuous: a cache entry is alive or
    it is gone. Our 2026-08-15 run over 8,325 clean probes saw 7,444 near 1.0,
    828 near 0.0, and 7 anywhere in between. A mean over that distribution is a
    number no single call ever had. Report the two masses.

PREDICATES
  * dedup by `message.id` (one API response is written once per content block;
    see cache_census.py for the full note).
  * a call "touched the cache" iff read > 0 or creation > 0. Rows with 0/0 are
    synthetic/error rows -- they never reached the model, so they are neither an
    endpoint nor a start of a gap.
  * warm  == read >= creation   (body survived)
    cold  == creation > read    (body re-paid)
    `read > 0` alone is meaningless: the workspace-shared system+tools prefix
    (~20-30k) is kept warm by concurrent sessions, so dead-body calls still read
    18-28k tokens.
  * the clock anchors on the RESPONSE row, not on the user row that opened the
    turn. We tested the submission-side anchor and rejected it: with a
    submission-side clock there is no 60-minute cliff at all (303 hits past 60
    minutes, max 628 minutes). Cache refresh is per API call, not per turn.
  * CONFOUND EXCLUSIONS (on by default, --keep-confounds to disable). A cold call
    can be cold for reasons other than TTL, and those must not be counted as TTL
    deaths:
      model flip       a different `message.model` than the previous call --
                       caches are per model, so the first call after a flip is
                       cold by construction
      compaction       a `system`/`compact_boundary` row between the two calls --
                       the prefix was rewritten on purpose
      version change   a different harness `version` -- the system prompt moved
      thread break     `isSidechain` differs, or the pair spans two files
    Our measurement kept 8,325 of ~8,700 probes after these exclusions, and the
    residual "prefix changed for unrelated reasons" floor was 1.9-4.9% depending
    on the band -- i.e. do not read a 2% cold rate as a TTL signal.

USAGE
    python3 cache_gap_curve.py --since 2026-08-20                  # main threads (1h TTL)
    python3 cache_gap_curve.py --since 2026-09-08 --sidechain      # subagent threads (5m TTL)
    python3 cache_gap_curve.py --since 2026-09-01 --json > curve.json

Python 3.10+, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

USAGE_MARKER = b'"cache_read_input_tokens"'
COMPACT_MARKER = b"compact_boundary"

MAIN_BUCKETS = [
    (0, 2, "<2m"), (2, 5, "2-5m"), (5, 15, "5-15m"), (15, 30, "15-30m"),
    (30, 40, "30-40m"), (40, 45, "40-45m"), (45, 50, "45-50m"), (50, 55, "50-55m"),
    (55, 60, "55-60m"), (60, 70, "60-70m"), (70, 90, "70-90m"), (90, 1e9, "90m+"),
]
SIDE_BUCKETS = [
    (0, 0.5, "<30s"), (0.5, 1, "30-60s"), (1, 2, "1-2m"), (2, 3, "2-3m"),
    (3, 4, "3-4m"), (4, 5, "4-5m"), (5, 6, "5-6m"), (6, 8, "6-8m"),
    (8, 10, "8-10m"), (10, 15, "10-15m"), (15, 30, "15-30m"), (30, 1e9, "30m+"),
]


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


def parse_ts(text: str) -> float | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def bucket_of(minutes: float, buckets) -> str | None:
    for lo, hi, name in buckets:
        if lo <= minutes < hi:
            return name
    return None


def iter_transcripts(root: Path, sidechain: bool):
    for project in sorted(p for p in root.iterdir() if p.is_dir()):
        if sidechain:
            yield from sorted(project.glob("*/subagents/*.jsonl"))
        else:
            yield from sorted(project.glob("*.jsonl"))


def calls_in_file(path: Path, until, want_sidechain: bool):
    """Stream one transcript. Return deduped cache-touching calls, ordered,
    each tagged with the compaction count seen before it."""
    groups: dict[str, dict] = {}
    order: list[str] = []
    compactions = 0
    with path.open("rb") as handle:
        for raw in handle:
            if COMPACT_MARKER in raw:
                compactions += 1
                continue
            if USAGE_MARKER not in raw:
                continue
            try:
                row = json.loads(raw)
            except Exception:
                continue
            if row.get("type") != "assistant":
                continue
            if bool(row.get("isSidechain")) != want_sidechain:
                continue
            message = row.get("message")
            if not isinstance(message, dict):
                continue
            message_id = message.get("id")
            if not isinstance(message_id, str) or not message_id:
                continue
            ts = parse_ts(row.get("timestamp") or "")
            if ts is None:
                continue
            usage = message.get("usage") or {}
            read = int(usage.get("cache_read_input_tokens") or 0)
            creation = int(usage.get("cache_creation_input_tokens") or 0)
            if read == 0 and creation == 0:
                continue                      # synthetic / error: never reached the model
            if message_id in groups:
                continue                      # extra content block of the same response
            groups[message_id] = {
                "ts": ts, "read": read, "creation": creation,
                "model": message.get("model") or "unknown",
                "version": row.get("version"),
                "compactions": compactions,
            }
            order.append(message_id)
    calls = [groups[mid] for mid in order]
    calls.sort(key=lambda c: c["ts"])
    # --until is applied here; --since is NOT, because the predecessor of the
    # first in-window call may legitimately sit just before the window edge and
    # dropping it would silently delete the longest gaps. The window test runs
    # on the CURRENT call of each pair instead (see main()).
    hi = until.timestamp() if until else None
    return [c for c in calls if hi is None or c["ts"] < hi]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projects-dir", default="~/.claude/projects")
    ap.add_argument("--project", default=None, help="restrict to one munged project dir name")
    ap.add_argument("--since", default=None)
    ap.add_argument("--until", default=None)
    ap.add_argument("--tz", default="local")
    ap.add_argument("--sidechain", action="store_true",
                    help="read subagent threads (<sid>/subagents/agent-*.jsonl, 5m TTL) "
                         "and use sub-minute buckets")
    ap.add_argument("--keep-confounds", action="store_true",
                    help="do not drop model-flip / compaction / version-change pairs")
    ap.add_argument("--min-gap", type=float, default=0.0, help="ignore pairs closer than N minutes")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tz = parse_tz(args.tz)
    since = parse_bound(args.since, tz) if args.since else None
    until = parse_bound(args.until, tz) if args.until else None
    buckets = SIDE_BUCKETS if args.sidechain else MAIN_BUCKETS

    root = Path(args.projects_dir).expanduser()
    per_bucket = defaultdict(lambda: {"n": 0, "warm": 0, "cold": 0, "survival": []})
    dropped = {"model_flip": 0, "compaction": 0, "version_change": 0, "min_gap": 0, "out_of_window": 0}
    stats = {"files": 0, "files_skipped_mtime": 0, "calls": 0, "pairs": 0}
    edge = {"last_warm_gap": 0.0, "first_cold_gap": None}

    for path in iter_transcripts(root, args.sidechain):
        if args.project and path.parts[len(root.parts)] != args.project:
            continue
        if since is not None:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if mtime < since:
                stats["files_skipped_mtime"] += 1
                continue
        calls = calls_in_file(path, until, args.sidechain)
        stats["files"] += 1
        stats["calls"] += len(calls)
        for prev, cur in zip(calls, calls[1:]):
            stats["pairs"] += 1
            if since is not None and cur["ts"] < since.timestamp():
                dropped["out_of_window"] += 1
                continue
            gap_min = (cur["ts"] - prev["ts"]) / 60.0
            if gap_min < args.min_gap:
                dropped["min_gap"] += 1
                continue
            if not args.keep_confounds:
                if cur["model"] != prev["model"]:
                    dropped["model_flip"] += 1
                    continue
                if cur["compactions"] != prev["compactions"]:
                    dropped["compaction"] += 1
                    continue
                if cur["version"] != prev["version"]:
                    dropped["version_change"] += 1
                    continue
            name = bucket_of(gap_min, buckets)
            if name is None:
                continue
            total = cur["read"] + cur["creation"]
            survival = cur["read"] / total if total else 0.0
            warm = cur["read"] >= cur["creation"]
            slot = per_bucket[name]
            slot["n"] += 1
            slot["warm" if warm else "cold"] += 1
            slot["survival"].append(survival)
            if warm:
                edge["last_warm_gap"] = max(edge["last_warm_gap"], gap_min)
            else:
                edge["first_cold_gap"] = gap_min if edge["first_cold_gap"] is None \
                    else min(edge["first_cold_gap"], gap_min)

    out = {"mode": "sidechain" if args.sidechain else "main",
           "window": {"since": since.isoformat() if since else None,
                      "until": until.isoformat() if until else None, "tz": args.tz},
           "coverage": stats, "dropped": dropped,
           "longest_warm_gap_min": round(edge["last_warm_gap"], 2),
           "shortest_cold_gap_min": round(edge["first_cold_gap"], 2) if edge["first_cold_gap"] is not None else None,
           "buckets": {}}
    for _, _, name in buckets:
        slot = per_bucket.get(name)
        if not slot or not slot["n"]:
            continue
        vals = sorted(slot["survival"])
        p10 = vals[max(0, int(0.10 * (len(vals) - 1)))]
        out["buckets"][name] = {
            "n": slot["n"],
            "warm": slot["warm"], "cold": slot["cold"],
            "warm_pct": round(100.0 * slot["warm"] / slot["n"], 1),
            "cold_pct": round(100.0 * slot["cold"] / slot["n"], 1),
            "survival_p10": round(p10, 3),
            "survival_median": round(statistics.median(vals), 3),
        }

    if args.json:
        print(json.dumps(out, indent=1))
        return 0

    print(f"# cache_gap_curve  mode={out['mode']}  tz={args.tz}")
    print(f"# window {out['window']['since']} .. {out['window']['until']}")
    print(f"# files={stats['files']} (mtime-skipped {stats['files_skipped_mtime']})  "
          f"cache-touching calls={stats['calls']:,}  pairs={stats['pairs']:,}")
    print(f"# dropped: " + "  ".join(f"{k}={v:,}" for k, v in dropped.items()))
    print()
    head = f"{'gap bucket':<12} {'n':>7} {'warm%':>7} {'cold%':>7} {'p10 body':>9} {'median body':>12}"
    print(head)
    print("-" * len(head))
    for name, slot in out["buckets"].items():
        print(f"{name:<12} {slot['n']:>7,} {slot['warm_pct']:>7.1f} {slot['cold_pct']:>7.1f} "
              f"{slot['survival_p10']:>9.3f} {slot['survival_median']:>12.3f}")
    print("-" * len(head))
    print(f"longest gap that still came back warm : {out['longest_warm_gap_min']:.2f} min")
    print(f"shortest gap that came back cold      : "
          f"{out['shortest_cold_gap_min'] if out['shortest_cold_gap_min'] is not None else '-'} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
