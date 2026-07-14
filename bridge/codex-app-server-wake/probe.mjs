#!/usr/bin/env node
import { spawn } from "node:child_process";
import { parseArgs } from "node:util";
import { resolve } from "node:path";

const { values } = parseArgs({
  options: {
    mode: { type: "string", default: "idle" },
    workdir: { type: "string", default: process.cwd() },
    "codex-bin": { type: "string", default: process.env.CODEX_BIN || "codex" },
    "claude-bin": { type: "string", default: process.env.CLAUDE_BIN || "claude" },
    "codex-model": { type: "string" },
    "claude-model": { type: "string", default: "haiku" },
    "timeout-ms": { type: "string", default: "180000" },
  },
  strict: true,
});

const mode = values.mode;
if (mode !== "idle" && mode !== "busy") {
  throw new Error("--mode must be idle or busy");
}

const workdir = resolve(values.workdir);
const overallTimeoutMs = Number.parseInt(values["timeout-ms"], 10);
if (!Number.isFinite(overallTimeoutMs) || overallTimeoutMs < 30_000) {
  throw new Error("--timeout-ms must be an integer >= 30000");
}

const app = spawn(values["codex-bin"], ["app-server", "--listen", "stdio://"], {
  cwd: workdir,
  env: process.env,
  stdio: ["pipe", "pipe", "pipe"],
});

let nextId = 1;
let buffer = "";
let stderr = "";
const pendingRequests = new Map();
let threadId = null;
let claudeResult = "";
let codexMessage = "";
let firstTurnMessage = "";
let activeTurnId = null;
let queuedClaude = false;
let claudeArrivedWhileActive = false;
let phase = "setup";
let finishing = false;

function request(method, params) {
  const id = nextId++;
  app.stdin.write(JSON.stringify({ method, id, params }) + "\n");
  return new Promise((resolvePromise, rejectPromise) => {
    pendingRequests.set(id, { resolve: resolvePromise, reject: rejectPromise });
  });
}

function notify(method, params = {}) {
  app.stdin.write(JSON.stringify({ method, params }) + "\n");
}

function parseClaudeOutput(stdout) {
  try {
    const parsed = JSON.parse(stdout);
    return String(parsed.result || "");
  } catch {
    return String(stdout || "");
  }
}

function deliveryInput(prefix) {
  return [{
    type: "text",
    text: prefix + " CLAUDE_BG_BRIDGE_OK. Reply exactly CODEX_EVENT_WAKE_OK. Do not use tools.",
  }];
}

function startDeliveryTurn(prefix) {
  phase = "delivery";
  return request("turn/start", {
    threadId,
    input: deliveryInput(prefix),
  });
}

function finish(ok, extra = {}) {
  if (finishing) return;
  finishing = true;
  clearTimeout(timeout);
  const payload = {
    ok,
    mode,
    threadId,
    claudeResult,
    firstTurnMessage,
    codexMessage,
    claudeArrivedWhileActive,
    queuedClaude,
    stderr,
    ...extra,
  };
  process.stdout.write(JSON.stringify(payload, null, 2) + "\n");
  try { app.stdin.end(); } catch {}
  try { app.kill("SIGTERM"); } catch {}
  setTimeout(() => {
    try { app.kill("SIGKILL"); } catch {}
    process.exit(ok ? 0 : 1);
  }, 500).unref();
}

app.stderr.on("data", (chunk) => {
  stderr = (stderr + chunk.toString("utf8")).slice(-12000);
});

app.stdout.on("data", (chunk) => {
  buffer += chunk.toString("utf8");
  while (buffer.includes("\n")) {
    const index = buffer.indexOf("\n");
    const line = buffer.slice(0, index).trim();
    buffer = buffer.slice(index + 1);
    if (!line) continue;

    let message;
    try {
      message = JSON.parse(line);
    } catch {
      continue;
    }

    if (message.id !== undefined && pendingRequests.has(message.id)) {
      const waiter = pendingRequests.get(message.id);
      pendingRequests.delete(message.id);
      if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
      else waiter.resolve(message.result);
      continue;
    }

    if (message.method === "process/exited" &&
        message.params?.processHandle === "claude-wake-probe") {
      claudeResult = parseClaudeOutput(message.params.stdout);
      if (message.params.exitCode !== 0 ||
          !claudeResult.includes("CLAUDE_BG_BRIDGE_OK")) {
        finish(false, { stage: "claude-exit", notification: message });
        return;
      }

      if (activeTurnId) {
        queuedClaude = true;
        claudeArrivedWhileActive = true;
      } else {
        startDeliveryTurn("A background Claude process completed and returned")
          .catch((error) => finish(false, { stage: "delivery-start", error: error.message }));
      }
      continue;
    }

    if (message.method === "turn/started") {
      activeTurnId = message.params?.turn?.id || activeTurnId;
      continue;
    }

    if (message.method === "item/completed" &&
        message.params?.item?.type === "agentMessage") {
      const text = message.params.item.text || "";
      if (phase === "first") firstTurnMessage = text;
      else codexMessage = text;
      continue;
    }

    if (message.method === "turn/completed") {
      activeTurnId = null;

      if (phase === "first") {
        if (!queuedClaude) {
          finish(false, {
            stage: "first-turn-completed-before-claude",
            turnStatus: message.params?.turn?.status,
          });
          return;
        }
        queuedClaude = false;
        startDeliveryTurn("The queued background Claude result is")
          .catch((error) => finish(false, { stage: "queued-delivery-start", error: error.message }));
        continue;
      }

      const ok = codexMessage.includes("CODEX_EVENT_WAKE_OK") &&
        (mode === "idle" || claudeArrivedWhileActive);
      finish(ok, {
        stage: "complete",
        turnStatus: message.params?.turn?.status,
      });
    }
  }
});

app.on("error", (error) => {
  finish(false, { stage: "spawn-app-server", error: error.message });
});

app.on("exit", (code, signal) => {
  if (!finishing) {
    finish(false, { stage: "app-server-exit", code, signal });
  }
});

const timeout = setTimeout(() => {
  finish(false, { stage: "timeout" });
}, overallTimeoutMs);

try {
  await request("initialize", {
    clientInfo: {
      name: "claude_codex_wake_probe",
      title: "Claude Codex Wake Probe",
      version: "0.1.0",
    },
    capabilities: { experimentalApi: true },
  });
  notify("initialized");

  const threadParams = {
    cwd: workdir,
    approvalPolicy: "never",
    sandbox: "read-only",
    ephemeral: true,
    serviceName: "claude_codex_wake_probe",
  };
  if (values["codex-model"]) threadParams.model = values["codex-model"];

  const started = await request("thread/start", threadParams);
  threadId = started.thread.id;

  if (mode === "busy") {
    phase = "first";
    await request("turn/start", {
      threadId,
      input: [{
        type: "text",
        text: "Use the shell to run `sleep 12`. After it completes, reply exactly FIRST_TURN_DONE.",
      }],
    });
  }

  const claudeCommand = [
    values["claude-bin"],
    "-p",
    "Return exactly CLAUDE_BG_BRIDGE_OK. Do not use tools.",
    "--output-format",
    "json",
    "--model",
    values["claude-model"],
    "--effort",
    "low",
    "--permission-mode",
    "default",
  ];

  await request("process/spawn", {
    processHandle: "claude-wake-probe",
    command: claudeCommand,
    cwd: workdir,
    streamStdin: false,
    streamStdoutStderr: false,
    timeoutMs: Math.min(120_000, overallTimeoutMs - 5_000),
    tty: false,
  });
} catch (error) {
  finish(false, { stage: "setup", error: error.message });
}
