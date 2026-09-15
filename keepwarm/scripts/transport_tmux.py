#!/usr/bin/env python3
"""transport_tmux.py — inject a line into a Claude Code session running in tmux.

WHY A TRANSPORT AT ALL
----------------------
A keep-warm turn has to arrive the way a human's turn arrives: as text typed
into the CLI's input box, followed by Enter. There is no API for "send this
session a message" — the session is an interactive process attached to a
terminal, and the only writable surface is that terminal's input stream.

So we need a relay: something that already holds the terminal and can type into
it. Under tmux that is `tmux send-keys`. Inside VS Code it is the extension in
`vscode-injector/`. On both, the rule is the same and it is the load-bearing
design decision of the whole lane:

    THE RELAY IS A DUMB PIPE. It types, and that is all.

It does not confirm, does not retry, does not write a ledger. Everything that
decides whether the message actually arrived stays with the sender, because:
  - the truth about arrival lives in the session's transcript, which the sender
    can read and the relay has no business parsing;
  - a confirm/retry policy is a property of the MESSAGE (keep-warm wants a fast
    ladder, a notification wants a patient one), not of the pipe;
  - if the relay dies, a sender-owned confirm still notices. A relay-owned
    confirm dies with it.
We measured the cost of the naive assumption directly: the relay reported
"injected" 10 times out of 10 while only 8 of those actually reached the
session's transcript.

TWO SEPARATE WRITES
-------------------
    tmux send-keys -t <pane> -l "<message>"     # -l = literal, no key parsing
    tmux send-keys -t <pane> Enter

Not one combined write. The CLI's input handling has been observed to drop
input when body and newline arrive fused; sending the body first and a bare
Enter second is the form that survives. It is also what makes the retry work:
if the Enter is swallowed, the body is still sitting in the input box, so the
retry text appends to it and a single later Enter submits the merged line —
which is exactly why the nonce is accepted from either copy.

FINDING THE PANE
----------------
`--pane` takes any tmux target: `session:window.pane`, `%12`, or `mysess:0.0`.
To discover it:

    tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command}'

Then match the pane whose process tree contains the `claude` process for your
session id. A portable way to do that, given the session registry:

    # registry: ~/.claude/sessions/<claude-pid>.json  -> {"sessionId": "..."}
    pid=$(grep -l '"sessionId": *"<sid>"' ~/.claude/sessions/*.json \\
          | head -1 | xargs -r basename | sed 's/\\.json$//')
    # walk up from $pid to find an ancestor that is a tmux pane_pid
    while [ "$pid" != 1 ]; do
      tmux list-panes -a -F '#{pane_pid} #{session_name}:#{window_index}.#{pane_index}' \\
        | awk -v p="$pid" '$1==p {print $2; exit}' | grep . && break
      pid=$(awk '{print $4}' /proc/$pid/stat)
    done

`resolve_pane_for_pid()` below does that walk in Python.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

#: The relay truncates long input; keep-warm never approaches this, but a
#: transport should refuse rather than silently cut a message in half — a cut
#: tail takes the nonce with it and makes confirm impossible.
MAX_MESSAGE_CHARS = 500


class TmuxTransport:
    """Type a message into a tmux pane and press Enter."""

    name = "tmux"

    def __init__(self, pane: Optional[str] = None, tmux_bin: str = "tmux"):
        if not pane:
            raise ValueError("tmux transport needs --tmux-pane (see module docstring)")
        self.pane = pane
        self.tmux_bin = tmux_bin

    def deliver(self, sid: str, message: str) -> None:
        if len(message) > MAX_MESSAGE_CHARS:
            raise ValueError(
                f"message is {len(message)} chars, over the {MAX_MESSAGE_CHARS} relay budget; "
                "spill the body to a file and inject head + pointer + nonce instead"
            )
        if "\n" in message or "\r" in message:
            raise ValueError("message must be a single line: a newline submits early")
        self._send(["-l", "--", message])   # -l: literal. `--` guards a leading dash.
        self._send(["Enter"])               # a separate write, deliberately

    def _send(self, args: list[str]) -> None:
        cmd = [self.tmux_bin, "send-keys", "-t", self.pane, *args]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"tmux send-keys failed (rc={result.returncode}): "
                f"{result.stderr.strip() or 'no stderr'}"
            )


def resolve_pane_for_pid(pid: int, tmux_bin: str = "tmux") -> Optional[str]:
    """Walk up the process tree until an ancestor is a tmux pane's pid."""
    panes: dict[int, str] = {}
    result = subprocess.run(
        [tmux_bin, "list-panes", "-a", "-F",
         "#{pane_pid} #{session_name}:#{window_index}.#{pane_index}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            panes[int(parts[0])] = parts[1]

    current = pid
    for _ in range(32):          # bounded: never walk forever on a cycle
        if current in panes:
            return panes[current]
        try:
            stat = Path("/proc", str(current), "stat").read_text()
        except OSError:
            return None
        # field 4 is ppid; the comm field can contain spaces/parens, so split
        # after the last ')'.
        try:
            current = int(stat[stat.rindex(")") + 1:].split()[1])
        except (ValueError, IndexError):
            return None
        if current <= 1:
            return None
    return None


def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="tmux injection transport (manual test)")
    p.add_argument("--pane", required=True)
    p.add_argument("--sid", default="manual-test")
    p.add_argument("--message", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.dry_run:
        print(f"[dry-run] tmux send-keys -t {args.pane} -l -- {args.message!r}")
        print(f"[dry-run] tmux send-keys -t {args.pane} Enter")
        return 0
    TmuxTransport(pane=args.pane).deliver(args.sid, args.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
