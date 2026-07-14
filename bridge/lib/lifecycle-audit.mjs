// Lifecycle audit logger for local MCP/proxy processes.
//
// Captures startup, signals, exceptions, beforeExit, and exit as JSONL rows.
// Size-bounded with generation rotation. Best-effort: any failure is swallowed
// after a single stderr breadcrumb so the host server is never destabilized.
//
// Design boundaries:
//   - record-only by default: uses `uncaughtExceptionMonitor` so Node's default
//     crash behavior is preserved on hosts without a keep-alive policy.
//   - `unhandledRejection` recording is opt-in; registering a listener changes
//     Node's default fatal behavior, so callers must declare intent.
//   - signal handlers are `prependListener`-registered for deterministic
//     ordering relative to caller-installed exit handlers.
//   - no payload data (prompts/responses/HTTP bodies) is recorded — only
//     state/situation/timing fields.

import { appendFileSync, statSync, renameSync, unlinkSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import process from "node:process";

const SCHEMA = "lifecycle.v1";
const installed = new Set();
let seq = 0;

export function installLifecycleAudit({
  name,
  logPath,
  maxBytes = 1_000_000,
  generations = 3,
  recordUnhandledRejection = false,
}) {
  if (!name) throw new Error("installLifecycleAudit: name is required");
  if (!logPath) throw new Error("installLifecycleAudit: logPath is required");

  if (installed.has(name)) {
    try {
      process.stderr.write(`[lifecycle-audit] duplicate install ignored: ${name}\n`);
    } catch {}
    return { recordEvent: () => {} };
  }
  installed.add(name);

  try {
    mkdirSync(dirname(logPath), { recursive: true });
  } catch {}

  const startedAt = Date.now();
  const supervisedName = process.env.MCP_SUPERVISED_SERVER_NAME || null;

  function rotateIfNeeded() {
    let size = 0;
    try {
      size = statSync(logPath).size;
    } catch {
      return;
    }
    if (size < maxBytes) return;
    try { unlinkSync(`${logPath}.${generations}`); } catch {}
    for (let i = generations - 1; i >= 1; i--) {
      try { renameSync(`${logPath}.${i}`, `${logPath}.${i + 1}`); } catch {}
    }
    try { renameSync(logPath, `${logPath}.1`); } catch {}
  }

  function recordEvent(event, extra = {}) {
    try {
      rotateIfNeeded();
      const row = {
        schema: SCHEMA,
        ts: new Date().toISOString(),
        name,
        pid: process.pid,
        ppid: process.ppid,
        seq: ++seq,
        event,
        uptime_ms: Date.now() - startedAt,
        ...(supervisedName ? { supervised_name: supervisedName } : {}),
        ...extra,
      };
      appendFileSync(logPath, `${JSON.stringify(row)}\n`, "utf8");
    } catch (err) {
      try {
        process.stderr.write(
          `[lifecycle-audit:${name}] write failed: ${err?.message || String(err)}\n`,
        );
      } catch {}
    }
  }

  recordEvent("startup", {
    node: process.version,
    cwd: process.cwd(),
  });

  // Signals: prepend so audit row lands before caller-installed handlers call
  // process.exit. Only SIGTERM/SIGINT — these are universally handled by
  // every host server, so registering does not alter default behavior.
  process.prependListener("SIGTERM", () => recordEvent("sigterm"));
  process.prependListener("SIGINT", () => recordEvent("sigint"));

  // Record-only exception monitor. Does NOT prevent default crash behavior.
  process.on("uncaughtExceptionMonitor", (err) => {
    const stack = err?.stack ? String(err.stack).slice(0, 2048) : undefined;
    recordEvent("uncaught_exception", {
      message: err?.message || String(err),
      stack,
    });
  });

  // Opt-in: registering this listener would change Node's default fatal
  // behavior on hosts that do not already keep-alive on rejection.
  if (recordUnhandledRejection) {
    process.on("unhandledRejection", (reason) => {
      const stack = reason?.stack ? String(reason.stack).slice(0, 2048) : undefined;
      recordEvent("unhandled_rejection", {
        message: reason?.message || String(reason),
        stack,
      });
    });
  }

  process.on("beforeExit", (code) => {
    recordEvent("before_exit", { exit_code: code });
  });

  process.on("exit", (code) => {
    recordEvent("exit", { exit_code: code });
  });

  return { recordEvent };
}
