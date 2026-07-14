#!/usr/bin/env node
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const wrapper = resolve(here, "run.sh");
const live = process.argv.includes("--live");
const modelIndex = process.argv.indexOf("--model");
const model = modelIndex >= 0 && process.argv[modelIndex + 1]
  ? process.argv[modelIndex + 1]
  : (process.env.CLAUDE_MCP_SMOKE_MODEL || "haiku");
const workdir = resolve(process.env.CLAUDE_MCP_SMOKE_WORKDIR || process.cwd());

const child = spawn(wrapper, [], {
  cwd: workdir,
  env: {
    ...process.env,
    CLAUDE_MCP_WORKDIR: workdir,
    CLAUDE_MCP_ALLOWED_WORKDIRS: workdir,
    CLAUDE_MCP_DEFAULT_PERMISSION_MODE: "default",
    CLAUDE_MCP_DEFAULT_WRITE_PERMISSION_MODE: "acceptEdits",
    CLAUDE_MCP_ALLOW_DANGEROUS: "0",
    CLAUDE_MCP_ALLOW_BARE: "0",
  },
  stdio: ["pipe", "pipe", "pipe"],
});

let nextId = 1;
let stderr = "";
let finished = false;
const pending = new Map();

function send(method, params = {}) {
  const id = nextId++;
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  return new Promise((resolvePromise, rejectPromise) => {
    pending.set(id, { resolve: resolvePromise, reject: rejectPromise });
  });
}

function notify(method, params = {}) {
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n");
}

function stop(code, payload) {
  if (finished) return;
  finished = true;
  clearTimeout(timeout);
  process.stdout.write(JSON.stringify(payload, null, 2) + "\n");
  try { child.stdin.end(); } catch {}
  try { child.kill("SIGTERM"); } catch {}
  setTimeout(() => {
    try { child.kill("SIGKILL"); } catch {}
    process.exit(code);
  }, 300).unref();
}

child.stderr.on("data", (chunk) => {
  stderr = (stderr + chunk.toString("utf8")).slice(-12000);
});

const rl = createInterface({ input: child.stdout, terminal: false });
rl.on("line", (line) => {
  if (!line.trim()) return;
  let message;
  try {
    message = JSON.parse(line);
  } catch {
    return;
  }
  if (message.id === undefined || !pending.has(message.id)) return;
  const waiter = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
  else waiter.resolve(message.result);
});

child.on("error", (error) => {
  stop(1, { ok: false, stage: "spawn", error: error.message, stderr });
});
child.on("exit", (code, signal) => {
  if (!finished) stop(1, { ok: false, stage: "early-exit", code, signal, stderr });
});

const timeout = setTimeout(() => {
  stop(1, { ok: false, stage: "timeout", stderr });
}, live ? 1_900_000 : 30_000);

try {
  await send("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "claude-coder-smoke", version: "0.1.0" },
  });
  notify("notifications/initialized");

  const listed = await send("tools/list");
  const names = (listed.tools || []).map((tool) => tool.name);
  const required = [
    "claude_health",
    "claude_run_task",
    "claude_run_write_task",
    "claude_continue_thread",
    "claude_list_runs",
  ];
  const missing = required.filter((name) => !names.includes(name));
  if (missing.length) throw new Error("missing tools: " + missing.join(", "));

  const healthResult = await send("tools/call", {
    name: "claude_health",
    arguments: {},
  });
  const health = JSON.parse(healthResult.content?.[0]?.text || "{}");
  if (!health.ok) throw new Error("claude_health failed: " + JSON.stringify(health));

  if (!live) {
    stop(0, { ok: true, mode: "health", tools: names, health });
  } else {
    const taskResult = await send("tools/call", {
      name: "claude_run_task",
      arguments: {
        prompt: "Reply exactly CLAUDE_CODER_MCP_OK. Do not use tools.",
        workingDirectory: workdir,
        model,
        effort: "low",
        permissionMode: "default",
        bare: false,
      },
    });
    const task = JSON.parse(taskResult.content?.[0]?.text || "{}");
    const ok = task.status === "completed" &&
      String(task.final_response || "").includes("CLAUDE_CODER_MCP_OK");
    stop(ok ? 0 : 1, { ok, mode: "live", model, health, task, stderr });
  }
} catch (error) {
  stop(1, { ok: false, stage: "protocol", error: error.message, stderr });
}
