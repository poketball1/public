#!/usr/bin/env python3
"""cache_census.py — per-call prompt-cache hit/miss census over Claude Code transcripts.

WHAT IT MEASURES
    One row per *API response* (not per transcript line) with:
      thread kind   main | sidechain          (top-level `isSidechain`)
      ttl mode      1h | 5m | unsplit | none  (`usage.cache_creation.ephemeral_*`)
      cache_outcome hit | rewrite | none      (see PREDICATES)
      cold_rewrite  the documented cold-front signature
      synthetic     API error / harness-fabricated rows (usage 0/0)
    and aggregates them by session, day, thread kind, or model.

PREDICATES (each one exists because a naive version of it produced a wrong number)
  1. DEDUP BY `message.id`.
     One API response whose content has several blocks is written as several
     `assistant` lines sharing one `message.id` (and one `requestId`), with an
     increasing `apiBlockIndex`. Every line repeats the SAME cache/input counters.
     Summing lines inflates token totals ~2.1x, and the multiplier tracks tool-call
     density, so it *fabricates trends* across days. Cache and input counters never
     varied inside a group in our corpus; output/thinking only grow (streamed), so
     the merge rule is: cache/input as-is from the first line, output/thinking = max.
  2. cache_outcome
       none    read == 0 and creation == 0   -> the model never touched the cache
                                               (synthetic/error rows land here)
       hit     read >= creation              -> the conversation body survived
       rewrite creation  > read              -> the body was re-paid (cold)
     `read > 0` alone is NOT a hit. The workspace-shared system+tools prefix
     (~20-30k tokens) stays warm because concurrent sessions keep rewriting it, so a
     turn whose body is completely dead still reads 18-28k tokens. Our measurement
     (2026-08-15, 8,325 clean probes) found the body-survival ratio
     read/(read+creation) to be BIMODAL (~1.0: 7,444 / ~0.0: 828 / middle: 7), which
     is why the row-local threshold read>=creation is insensitive to where you put it.
  3. cold_rewrite = creation > 150_000 and read < 1_000
     The "cold front" signature: a whole context re-written from scratch. Used to
     spot account/credential swaps and >TTL wakes. Threshold from our own corpus.
  4. MISS REASON (bonus: the harness sometimes tells you why)
     `message.diagnostics.cache_miss_reason` carries `{type, cache_missed_input_tokens}`.
     Observed types in our 30-day corpus (1,700 calls that had one):
       messages_changed            the conversation body no longer matched (this is
                                   where a TTL expiry shows up)
       unavailable                 no reason given, no token count
       previous_message_not_found  the anchor row was gone
       tools_changed               the tool list changed (MCP connect/disconnect)
       system_changed              the system prompt changed
       model_changed               a different model == a different cache key
     Coverage is partial -- only 1,700 of 6,876 rewrite calls carried one -- so use it
     as a hint, never as the denominator.
  5. QUOTA UNITS (subscription calibration, our measurement 2026-07-22)
       quota_units = uncached_input*1 + cache_creation*1 + output*1 + cache_read*0
     `cache_read` counts ~0x toward the subscription cap. Calibration: a credential
     swap re-wrote ~1.1-2.25M tokens and consumed 5% of a weekly cap => cap is tens
     of millions of tokens, while measured cache_read alone was ~1.31B/account/week.
     At 0.1x that single term would exceed the cap several times over, which is
     impossible given the account kept working. So 0x, and the real driver is
     cache_creation.
     NOTE: this is NOT the API dollar weighting (read 0.1x, 1h-write 2x, 5m-write
     1.25x). Pass --weights api to price the same rows the API way instead.

USAGE
    python3 cache_census.py --since 2026-09-08 --by day
    python3 cache_census.py --since 2026-09-14 --by session --json > out.json
    python3 cache_census.py --by thread --include-subagents

Python 3.10+, stdlib only. Streams line by line; never holds a file in memory.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------- tunables
COLD_CREATION_MIN = 150_000
COLD_READ_MAX = 1_000

# A line without this byte string cannot be an assistant usage row. Cheapest
# possible filter; a 5 GB corpus is mostly user/attachment/tool-result rows.
USAGE_MARKER = b'"cache_read_input_tokens"'

WEIGHTS = {
    # subscription cap calibration (see docstring #4)
    "quota": {"input": 1.0, "write_1h": 1.0, "write_5m": 1.0, "read": 0.0, "output": 1.0},
    # API dollar weighting, expressed in "input-token equivalents"
    "api": {"input": 1.0, "write_1h": 2.0, "write_5m": 1.25, "read": 0.1, "output": 0.0},
}


# ---------------------------------------------------------------- time helpers
def parse_tz(spec: str) -> timezone:
    if spec in ("local", ""):
        off = datetime.now().astimezone().utcoffset() or timedelta(0)
        return timezone(off)
    if spec in ("utc", "UTC", "Z"):
        return timezone.utc
    sign = 1
    body = spec
    if body[0] in "+-":
        sign = -1 if body[0] == "-" else 1
        body = body[1:]
    hh, _, mm = body.partition(":")
    return timezone(sign * timedelta(hours=int(hh), minutes=int(mm or 0)))


def parse_bound(text: str, tz: timezone) -> datetime:
    """'2026-09-08' or '2026-09-08T13:00' interpreted in --tz, returned as UTC."""
    text = text.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        dt = datetime.fromisoformat(text + "T00:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def parse_ts(text: str) -> datetime | None:
    """Transcript timestamps are UTC ISO-8601 with a trailing 'Z'."""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------- file walk
def iter_transcripts(root: Path, include_subagents: bool):
    """Yield (path, kind). kind == 'main' for <project>/<sid>.jsonl,
    'subagent' for <project>/<sid>/subagents/agent-<id>.jsonl."""
    for project in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(project.glob("*.jsonl")):
            yield path, "main"
        if include_subagents:
            for path in sorted(project.glob("*/subagents/*.jsonl")):
                yield path, "subagent"


# ---------------------------------------------------------------- core scan
def scan_file(path: Path, since: datetime | None, until: datetime | None):
    """Return (groups, stats). groups maps message.id -> merged call record."""
    groups: dict[str, dict] = {}
    lines = 0
    usage_lines = 0
    merged = 0
    with path.open("rb") as handle:
        for raw in handle:
            lines += 1
            if USAGE_MARKER not in raw:
                continue
            try:
                row = json.loads(raw)
            except Exception:
                continue
            if row.get("type") != "assistant":
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
            if since and ts < since:
                continue
            if until and ts >= until:
                continue
            usage_lines += 1

            usage = message.get("usage")
            usage = usage if isinstance(usage, dict) else {}
            creation_total = int(usage.get("cache_creation_input_tokens") or 0)
            split = usage.get("cache_creation")
            if isinstance(split, dict):
                write_1h = int(split.get("ephemeral_1h_input_tokens") or 0)
                write_5m = int(split.get("ephemeral_5m_input_tokens") or 0)
            else:
                write_1h = write_5m = 0
            unsplit = creation_total - write_1h - write_5m
            if unsplit < 0:            # never observed; keep the arithmetic honest
                unsplit = 0

            diagnostics = message.get("diagnostics")
            miss = (diagnostics or {}).get("cache_miss_reason") if isinstance(diagnostics, dict) else None
            miss_type = miss.get("type") if isinstance(miss, dict) else None
            miss_tokens = int((miss or {}).get("cache_missed_input_tokens") or 0) if isinstance(miss, dict) else 0

            details = usage.get("output_tokens_details")
            thinking = int((details or {}).get("thinking_tokens") or 0) if isinstance(details, dict) else 0

            record = {
                "ts": ts,
                "model": message.get("model") or "unknown",
                "sidechain": bool(row.get("isSidechain")),
                "input": int(usage.get("input_tokens") or 0),
                "write_1h": write_1h,
                "write_5m": write_5m,
                "write_unsplit": unsplit,
                "read": int(usage.get("cache_read_input_tokens") or 0),
                "output": int(usage.get("output_tokens") or 0),
                "thinking": thinking,
                "api_error": bool(row.get("isApiErrorMessage")),
                "api_status": row.get("apiErrorStatus"),
                "version": row.get("version"),
                "miss_type": miss_type,
                "miss_tokens": miss_tokens,
            }
            kept = groups.get(message_id)
            if kept is None:
                groups[message_id] = record
            else:
                merged += 1
                kept["output"] = max(kept["output"], record["output"])
                kept["thinking"] = max(kept["thinking"], record["thinking"])
    return groups, {"lines": lines, "usage_lines": usage_lines, "merged": merged}


def classify(record: dict) -> dict:
    read = record["read"]
    creation = record["write_1h"] + record["write_5m"] + record["write_unsplit"]
    if read == 0 and creation == 0:
        outcome = "none"
    elif read >= creation:
        outcome = "hit"
    else:
        outcome = "rewrite"
    if record["write_1h"] > 0 and record["write_5m"] == 0:
        ttl = "1h"
    elif record["write_5m"] > 0 and record["write_1h"] == 0:
        ttl = "5m"
    elif record["write_1h"] > 0 and record["write_5m"] > 0:
        ttl = "mixed"
    elif creation > 0:
        ttl = "unsplit"
    else:
        ttl = "none"
    return {
        "creation": creation,
        "outcome": outcome,
        "ttl": ttl,
        "cold_rewrite": creation > COLD_CREATION_MIN and read < COLD_READ_MAX,
        "synthetic": record["model"] == "<synthetic>",
        "survival": (read / (read + creation)) if (read + creation) else None,
    }


def blank_bucket() -> dict:
    return {
        "calls": 0, "input": 0, "write_1h": 0, "write_5m": 0, "write_unsplit": 0,
        "read": 0, "output": 0, "thinking": 0,
        "hit": 0, "rewrite": 0, "none": 0,
        "cold_rewrite": 0, "synthetic": 0, "api_error": 0,
        "main": 0, "sidechain": 0, "ttl_1h": 0, "ttl_5m": 0, "ttl_mixed": 0, "ttl_unsplit": 0,
        "miss_reasons": defaultdict(int), "miss_reason_tokens": defaultdict(int),
    }


def fold(bucket: dict, record: dict, meta: dict) -> None:
    bucket["calls"] += 1
    for key in ("input", "write_1h", "write_5m", "write_unsplit", "read", "output", "thinking"):
        bucket[key] += record[key]
    bucket[meta["outcome"]] += 1
    bucket["cold_rewrite"] += 1 if meta["cold_rewrite"] else 0
    bucket["synthetic"] += 1 if meta["synthetic"] else 0
    bucket["api_error"] += 1 if record["api_error"] else 0
    bucket["sidechain" if record["sidechain"] else "main"] += 1
    if meta["ttl"] in ("1h", "5m", "mixed", "unsplit"):
        bucket["ttl_" + meta["ttl"]] += 1
    if record["miss_type"]:
        bucket["miss_reasons"][record["miss_type"]] += 1
        bucket["miss_reason_tokens"][record["miss_type"]] += record["miss_tokens"]


def weighted(bucket: dict, weights: dict) -> float:
    return (
        bucket["input"] * weights["input"]
        + (bucket["write_1h"]) * weights["write_1h"]
        + (bucket["write_5m"] + bucket["write_unsplit"]) * weights["write_5m"]
        + bucket["read"] * weights["read"]
        + bucket["output"] * weights["output"]
    )


def human(n: float) -> str:
    n = float(n)
    for unit, scale in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= scale:
            return f"{n / scale:.2f}{unit}"
    return f"{n:.0f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projects-dir", default="~/.claude/projects",
                    help="root that holds <munged-cwd>/<session-id>.jsonl (default: %(default)s)")
    ap.add_argument("--project", default=None,
                    help="restrict to one munged project dir name (default: all)")
    ap.add_argument("--since", default=None, help="inclusive lower bound, e.g. 2026-09-08 or 2026-09-08T13:00")
    ap.add_argument("--until", default=None, help="exclusive upper bound")
    ap.add_argument("--tz", default="local", help="'local' (default), 'utc', or an offset like +09:00")
    ap.add_argument("--by", default="day", choices=("session", "day", "thread", "model", "total"))
    ap.add_argument("--include-subagents", action="store_true",
                    help="also read <sid>/subagents/agent-*.jsonl (5m-TTL sidechain threads)")
    ap.add_argument("--weights", default="quota", choices=tuple(WEIGHTS),
                    help="'quota' = subscription calibration (read 0x), 'api' = dollar weighting")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    ap.add_argument("--top", type=int, default=40, help="max rows in table output")
    args = ap.parse_args()

    tz = parse_tz(args.tz)
    since = parse_bound(args.since, tz) if args.since else None
    until = parse_bound(args.until, tz) if args.until else None
    weights = WEIGHTS[args.weights]

    root = Path(args.projects_dir).expanduser()
    if not root.is_dir():
        raise SystemExit(f"no such projects dir: {root}")

    buckets: dict[str, dict] = defaultdict(blank_bucket)
    totals = blank_bucket()
    stats = {"files": 0, "files_skipped_mtime": 0, "lines": 0, "usage_lines": 0,
             "merged": 0, "calls": 0, "id_collisions_across_files": 0}
    seen_ids: set[str] = set()

    for path, kind in iter_transcripts(root, args.include_subagents):
        if args.project and path.parts[len(root.parts)] != args.project:
            continue
        if since is not None:
            # a file last written before --since cannot hold rows after it
            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if mtime < since:
                stats["files_skipped_mtime"] += 1
                continue
        groups, filestats = scan_file(path, since, until)
        stats["files"] += 1
        stats["lines"] += filestats["lines"]
        stats["usage_lines"] += filestats["usage_lines"]
        stats["merged"] += filestats["merged"]
        if not groups:
            continue
        session_id = path.stem if kind == "main" else path.parent.parent.name
        for message_id, record in groups.items():
            if message_id in seen_ids:
                stats["id_collisions_across_files"] += 1
            else:
                seen_ids.add(message_id)
            meta = classify(record)
            stats["calls"] += 1
            if args.by == "session":
                key = f"{session_id[:8]} [{kind}]" if kind == "subagent" else session_id[:8]
            elif args.by == "day":
                key = record["ts"].astimezone(tz).strftime("%Y-%m-%d")
            elif args.by == "thread":
                key = "sidechain" if record["sidechain"] else "main"
            elif args.by == "model":
                key = record["model"]
            else:
                key = "total"
            fold(buckets[key], record, meta)
            fold(totals, record, meta)

    payload = {
        "window": {"since": since.isoformat() if since else None,
                   "until": until.isoformat() if until else None, "tz": args.tz},
        "weights": args.weights,
        "coverage": {
            **stats,
            "block_inflation": round(stats["usage_lines"] / stats["calls"], 3) if stats["calls"] else None,
        },
        "totals": {**totals,
                   "miss_reasons": dict(totals["miss_reasons"]),
                   "miss_reason_tokens": dict(totals["miss_reason_tokens"]),
                   "quota_units": round(weighted(totals, weights))},
        "buckets": {},
    }
    for key, bucket in buckets.items():
        reads = bucket["read"]
        writes = bucket["write_1h"] + bucket["write_5m"] + bucket["write_unsplit"]
        payload["buckets"][key] = {
            **bucket,
            "miss_reasons": dict(bucket["miss_reasons"]),
            "miss_reason_tokens": dict(bucket["miss_reason_tokens"]),
            "hit_ratio": round(reads / (reads + writes), 4) if (reads + writes) else None,
            "quota_units": round(weighted(bucket, weights)),
        }

    if args.json:
        print(json.dumps(payload, indent=1, sort_keys=True))
        return 0

    cov = payload["coverage"]
    print(f"# cache_census  by={args.by}  weights={args.weights}  tz={args.tz}")
    print(f"# window {payload['window']['since']} .. {payload['window']['until']}")
    print(f"# files={cov['files']} (mtime-skipped {cov['files_skipped_mtime']})  lines={cov['lines']:,}  "
          f"usage-lines={cov['usage_lines']:,}  unique-calls={cov['calls']:,}  "
          f"block-inflation={cov['block_inflation']}x  cross-file-id-collisions={cov['id_collisions_across_files']}")
    print()
    head = (f"{'key':<26} {'calls':>7} {'input':>8} {'write1h':>9} {'write5m':>9} {'read':>9} "
            f"{'output':>8} {'hit%':>6} {'rw':>6} {'cold':>5} {'syn':>5} {'quota':>9}")
    print(head)
    print("-" * len(head))
    rows = sorted(payload["buckets"].items(), key=lambda kv: (-kv[1]["quota_units"], kv[0])) \
        if args.by in ("session", "model") else sorted(payload["buckets"].items())
    for key, bucket in rows[: args.top]:
        hit_ratio = bucket["hit_ratio"]
        print(f"{key[:26]:<26} {bucket['calls']:>7,} {human(bucket['input']):>8} "
              f"{human(bucket['write_1h']):>9} {human(bucket['write_5m'] + bucket['write_unsplit']):>9} "
              f"{human(bucket['read']):>9} {human(bucket['output']):>8} "
              f"{(f'{hit_ratio*100:.2f}' if hit_ratio is not None else '-'):>6} "
              f"{bucket['rewrite']:>6,} {bucket['cold_rewrite']:>5,} {bucket['synthetic']:>5,} "
              f"{human(bucket['quota_units']):>9}")
    if len(rows) > args.top:
        print(f"... {len(rows) - args.top} more rows (use --json or raise --top)")
    tot = payload["totals"]
    tot_reads, tot_writes = tot["read"], tot["write_1h"] + tot["write_5m"] + tot["write_unsplit"]
    print("-" * len(head))
    print(f"{'TOTAL':<26} {tot['calls']:>7,} {human(tot['input']):>8} {human(tot['write_1h']):>9} "
          f"{human(tot['write_5m'] + tot['write_unsplit']):>9} {human(tot['read']):>9} "
          f"{human(tot['output']):>8} "
          f"{(f'{tot_reads/(tot_reads+tot_writes)*100:.2f}' if (tot_reads+tot_writes) else '-'):>6} "
          f"{tot['rewrite']:>6,} {tot['cold_rewrite']:>5,} {tot['synthetic']:>5,} "
          f"{human(weighted(tot, weights)):>9}")
    print()
    print(f"thread split: main {tot['main']:,} calls / sidechain {tot['sidechain']:,} calls")
    print(f"ttl split   : 1h {tot['ttl_1h']:,} / 5m {tot['ttl_5m']:,} / mixed {tot['ttl_mixed']:,} / unsplit {tot['ttl_unsplit']:,}")
    if tot["miss_reasons"]:
        print("miss reason : " + "  ".join(
            f"{name}={count:,}({human(tot['miss_reason_tokens'][name])} tok)"
            for name, count in sorted(tot["miss_reasons"].items(), key=lambda kv: -kv[1])))
    print(f"outcome     : hit {tot['hit']:,} / rewrite {tot['rewrite']:,} / none {tot['none']:,} "
          f"(cold-rewrite {tot['cold_rewrite']:,}, synthetic {tot['synthetic']:,}, api-error {tot['api_error']:,})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
