#!/usr/bin/env node
// MCP stdio child supervisor.
//
// Keeps the MCP client-side stdio connection open while supervising a child MCP
// server process. If the child exits after MCP initialization, the supervisor
// restarts it, replays initialize/initialized to the new child, and forwards
// later client requests to the restarted process.

import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { join, resolve as resolvePath } from "node:path";
import { homedir } from "node:os";
import { installLifecycleAudit } from "./lib/lifecycle-audit.mjs";

const args = process.argv.slice(2);
const sep = args.indexOf("--");

if (sep === -1 || sep === args.length - 1) {
  process.stderr.write(
    "usage: mcp-stdio-supervisor.mjs [--name NAME] -- COMMAND [ARGS...]\n",
  );
  process.exit(64);
}

let serverName = "mcp-child";
for (let i = 0; i < sep; i++) {
  if (args[i] === "--name" && args[i + 1]) {
    serverName = args[i + 1];
    i++;
  }
}

const childCommand = args[sep + 1];
const childArgs = args.slice(sep + 2);
const restartDelayMs = Number.parseInt(process.env.MCP_SUPERVISOR_RESTART_DELAY_MS || "500", 10);
const maxRestartDelayMs = Number.parseInt(process.env.MCP_SUPERVISOR_MAX_RESTART_DELAY_MS || "5000", 10);
const restartGraceMs = Number.parseInt(process.env.MCP_SUPERVISOR_RESTART_GRACE_MS || "15000", 10);

const LIFECYCLE_AUDIT_PATH = resolvePath(
  process.env.MCP_SUPERVISOR_LIFECYCLE_AUDIT_PATH ||
    join(homedir(), ".local", "state", "claude-codex-bridge", `mcp-supervisor-${serverName}-lifecycle.jsonl`),
);
const lifecycle = installLifecycleAudit({
  name: `mcp-supervisor:${serverName}`,
  logPath: LIFECYCLE_AUDIT_PATH,
  // Existing process.on handlers below keep supervisor alive on uncaught/rejection.
  recordUnhandledRejection: true,
});

let child = null;
let childAcceptingClientMessages = false;
let childLineBuffer = "";
let childEpoch = 0;
let restartTimer = null;
let restartFailures = 0;
let clientClosing = false;
let replayInitId = null;
let initializeRequest = null;
let initializedNotification = null;
let clientInitialized = false;
let stdoutClosed = false;
let stderrClosed = false;

const pending = new Map();
const queuedClientMessages = [];

function streamErrorDetails(err) {
  return {
    code: err?.code || null,
    message: err?.message || String(err),
  };
}

function isClosedPipeError(err) {
  return err?.code === "EPIPE" || err?.code === "ERR_STREAM_DESTROYED";
}

function markStreamClosed(streamName, err) {
  if (streamName === "stdout") {
    stdoutClosed = true;
  } else if (streamName === "stderr") {
    stderrClosed = true;
  }
  lifecycle.recordEvent(`${streamName}_closed`, streamErrorDetails(err));
}

function recordStreamError(streamName, err) {
  if (isClosedPipeError(err)) {
    markStreamClosed(streamName, err);
    return;
  }
  lifecycle.recordEvent(`${streamName}_error`, streamErrorDetails(err));
}

function writeStderr(chunk) {
  if (stderrClosed || process.stderr.destroyed || process.stderr.writableEnded) return false;
  try {
    process.stderr.write(chunk);
    return true;
  } catch (err) {
    recordStreamError("stderr", err);
    return false;
  }
}

function log(message) {
  writeStderr(`[mcp-supervisor:${serverName}] ${message}\n`);
}

function idKey(id) {
  return JSON.stringify(id);
}

function writeClient(message) {
  if (stdoutClosed || process.stdout.destroyed || process.stdout.writableEnded) {
    lifecycle.recordEvent("client_stdout_unavailable");
    shutdown();
    return false;
  }
  try {
    process.stdout.write(`${JSON.stringify(message)}\n`);
    return true;
  } catch (err) {
    recordStreamError("stdout", err);
    shutdown();
    return false;
  }
}

function protocolErrorResponse(id, message) {
  return {
    jsonrpc: "2.0",
    id,
    error: {
      code: -32000,
      message,
    },
  };
}

function rememberClientMessage(message) {
  if (message?.method === "initialize" && message.id !== undefined) {
    initializeRequest = structuredClone(message);
  } else if (message?.method === "notifications/initialized") {
    initializedNotification = structuredClone(message);
    clientInitialized = true;
  }
}

function sendRawToChild(message) {
  if (!child || !child.stdin || child.stdin.destroyed) return false;
  try {
    child.stdin.write(`${JSON.stringify(message)}\n`);
    return true;
  } catch (err) {
    log(`child stdin write failed: ${err?.message || String(err)}`);
    return false;
  }
}

function queueClientMessage(message) {
  queuedClientMessages.push({
    message,
    queuedAt: Date.now(),
  });
  ensureChild();
}

function flushQueuedClientMessages() {
  if (!childAcceptingClientMessages) return;
  while (queuedClientMessages.length) {
    const entry = queuedClientMessages.shift();
    if (Date.now() - entry.queuedAt > restartGraceMs) {
      if (entry.message.id !== undefined) {
        writeClient(protocolErrorResponse(entry.message.id, `${serverName} MCP child did not recover in time`));
      }
      continue;
    }
    forwardClientMessage(entry.message);
  }
}

function forwardClientMessage(message) {
  rememberClientMessage(message);
  if (!childAcceptingClientMessages) {
    queueClientMessage(message);
    return;
  }
  if (message.id !== undefined) {
    pending.set(idKey(message.id), { id: message.id, method: message.method });
  }
  if (!sendRawToChild(message) && message.id !== undefined) {
    pending.delete(idKey(message.id));
    writeClient(protocolErrorResponse(message.id, `${serverName} MCP child is unavailable`));
  }
}

function failPending(reason) {
  for (const { id, method } of pending.values()) {
    writeClient(protocolErrorResponse(id, `${serverName} MCP child exited while handling ${method || "request"}: ${reason}`));
  }
  pending.clear();
}

function handleChildMessage(message) {
  if (message?.id !== undefined && replayInitId !== null && message.id === replayInitId) {
    replayInitId = null;
    if (initializedNotification) {
      sendRawToChild(initializedNotification);
    }
    childAcceptingClientMessages = true;
    restartFailures = 0;
    log("child initialized after restart");
    lifecycle.recordEvent("replay_initialized", { epoch: childEpoch });
    flushQueuedClientMessages();
    return;
  }

  if (message?.id !== undefined) {
    pending.delete(idKey(message.id));
  }
  writeClient(message);
}

function consumeChildStdout(chunk) {
  childLineBuffer += chunk.toString("utf8");
  for (;;) {
    const newline = childLineBuffer.indexOf("\n");
    if (newline === -1) break;
    const line = childLineBuffer.slice(0, newline);
    childLineBuffer = childLineBuffer.slice(newline + 1);
    if (!line.trim()) continue;
    try {
      handleChildMessage(JSON.parse(line));
    } catch (err) {
      log(`dropping malformed child stdout line: ${err?.message || String(err)}`);
    }
  }
}

function replayInitialization() {
  if (!clientInitialized || !initializeRequest) {
    childAcceptingClientMessages = true;
    flushQueuedClientMessages();
    return;
  }

  replayInitId = `__mcp_supervisor_init_${childEpoch}`;
  const replay = structuredClone(initializeRequest);
  replay.id = replayInitId;
  if (!sendRawToChild(replay)) {
    scheduleRestart();
  }
}

function startChild() {
  if (clientClosing || child) return;
  childEpoch++;
  childLineBuffer = "";
  childAcceptingClientMessages = false;

  log(`starting child: ${childCommand} ${childArgs.join(" ")}`);
  child = spawn(childCommand, childArgs, {
    env: {
      ...process.env,
      MCP_SUPERVISED_SERVER_NAME: serverName,
      MCP_SUPERVISOR_PID: String(process.pid),
    },
    stdio: ["pipe", "pipe", "pipe"],
  });

  lifecycle.recordEvent("child_start", { epoch: childEpoch, child_pid: child.pid ?? null });

  child.stdout.on("data", consumeChildStdout);
  child.stderr.on("data", (chunk) => {
    writeStderr(chunk);
  });
  child.on("error", (err) => {
    log(`child process error: ${err?.message || String(err)}`);
    lifecycle.recordEvent("child_error", {
      epoch: childEpoch,
      message: err?.message || String(err),
    });
  });
  child.on("close", (code, signal) => {
    const reason = `exit=${code ?? "null"} signal=${signal ?? "null"}`;
    log(`child closed: ${reason}`);
    lifecycle.recordEvent("child_close", {
      epoch: childEpoch,
      exit_code: code,
      signal,
      pending: pending.size,
      queued: queuedClientMessages.length,
    });
    child = null;
    childAcceptingClientMessages = false;
    replayInitId = null;
    failPending(reason);
    if (!clientClosing) {
      restartFailures++;
      scheduleRestart();
    }
  });

  replayInitialization();
}

function scheduleRestart() {
  if (clientClosing || restartTimer || child) return;
  const delay = Math.min(maxRestartDelayMs, restartDelayMs * Math.max(1, restartFailures));
  lifecycle.recordEvent("restart_scheduled", {
    delay_ms: delay,
    failures: restartFailures,
  });
  restartTimer = setTimeout(() => {
    restartTimer = null;
    startChild();
  }, delay);
  if (restartTimer.unref) restartTimer.unref();
}

function ensureChild() {
  if (child || restartTimer || clientClosing) return;
  startChild();
}

function shutdown() {
  if (clientClosing) return;
  clientClosing = true;
  lifecycle.recordEvent("supervisor_shutdown", {
    child_alive: Boolean(child),
    pending: pending.size,
    queued: queuedClientMessages.length,
  });
  if (restartTimer) {
    clearTimeout(restartTimer);
    restartTimer = null;
  }
  if (child) {
    try {
      child.stdin.end();
    } catch {}
    try {
      child.kill("SIGTERM");
    } catch {}
  }
  const timer = setTimeout(() => process.exit(0), 500);
  if (timer.unref) timer.unref();
}

process.on("uncaughtException", (err) => {
  log(`uncaught exception kept supervisor alive: ${err?.stack || err?.message || String(err)}`);
});

process.on("unhandledRejection", (reason) => {
  log(`unhandled rejection kept supervisor alive: ${reason?.stack || reason?.message || String(reason)}`);
});

process.stdout.on("error", (err) => {
  recordStreamError("stdout", err);
  if (isClosedPipeError(err)) {
    shutdown();
  }
});

process.stderr.on("error", (err) => {
  recordStreamError("stderr", err);
});

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

const rl = createInterface({ input: process.stdin, terminal: false });
rl.on("line", (line) => {
  if (!line.trim()) return;
  let message = null;
  try {
    message = JSON.parse(line);
  } catch (err) {
    log(`dropping malformed client line: ${err?.message || String(err)}`);
    return;
  }
  forwardClientMessage(message);
});

rl.on("close", () => {
  lifecycle.recordEvent("stdin_close");
  shutdown();
});

startChild();
