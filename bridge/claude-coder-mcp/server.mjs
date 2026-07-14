#!/usr/bin/env node
// Portable Claude Code MCP server.
// Exposes the locally authenticated Claude Code CLI as synchronous MCP tools.
// The MCP tools/call stays open until the Claude child exits; this is not a
// detached/background wake transport.

import { createInterface } from "node:readline";
import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";
import { dirname, resolve, relative, join } from "node:path";
import { appendFile, mkdir } from "node:fs/promises";
import { installLifecycleAudit } from "../lib/lifecycle-audit.mjs";

const execFileAsync = promisify(execFile);

const SERVER_NAME = "claude-coder";
const SERVER_VERSION = "0.1.0";
const SERVER_STARTED_AT = new Date();

const CLAUDE_BIN = process.env.CLAUDE_BIN || "claude";
const DEFAULT_MODEL = process.env.CLAUDE_MCP_MODEL || "sonnet";
const LEGACY_DEFAULT_ALLOWED_MODELS = "sonnet,opus,haiku";
const DEFAULT_ALLOWED_MODELS = "sonnet,opus,haiku";
const MODEL_ALIASES = new Map();
const CONFIGURED_ALLOWED_MODELS = process.env.CLAUDE_MCP_ALLOWED_MODELS;
const RAW_ALLOWED_MODELS = CONFIGURED_ALLOWED_MODELS && CONFIGURED_ALLOWED_MODELS.trim() !== LEGACY_DEFAULT_ALLOWED_MODELS
  ? CONFIGURED_ALLOWED_MODELS
  : DEFAULT_ALLOWED_MODELS;
const ALLOWED_MODELS = RAW_ALLOWED_MODELS
  .split(",").map((s) => s.trim()).filter(Boolean);
const DEFAULT_WORKDIR = resolve(process.env.CLAUDE_MCP_WORKDIR || process.cwd());
const ALLOWED_WORKDIRS = (process.env.CLAUDE_MCP_ALLOWED_WORKDIRS || DEFAULT_WORKDIR)
  .split(",").map((p) => resolve(p.trim())).filter(Boolean);
const DEFAULT_PERMISSION_MODE = process.env.CLAUDE_MCP_DEFAULT_PERMISSION_MODE || "default";
const DEFAULT_WRITE_PERMISSION_MODE = process.env.CLAUDE_MCP_DEFAULT_WRITE_PERMISSION_MODE || "acceptEdits";
const DEFAULT_EFFORT = process.env.CLAUDE_MCP_DEFAULT_EFFORT || "high";
const ALLOW_DANGEROUS = process.env.CLAUDE_MCP_ALLOW_DANGEROUS === "1";
const DEFAULT_BARE = process.env.CLAUDE_MCP_DEFAULT_BARE === "1";
const ALLOW_BARE = process.env.CLAUDE_MCP_ALLOW_BARE === "1";
const STRIP_API_KEY = process.env.CLAUDE_MCP_STRIP_API_KEY === "1";
const MAX_TASKS = Number.parseInt(process.env.CLAUDE_MCP_MAX_TASKS || "50", 10);
const MAX_PROMPT_CHARS = Number.parseInt(process.env.CLAUDE_MCP_MAX_PROMPT_CHARS || "200000", 10);
const MIN_AGENT_TIMEOUT_MS = 1_800_000;
const DEFAULT_WAIT_MS = Math.max(MIN_AGENT_TIMEOUT_MS, readIntEnv("CLAUDE_MCP_DEFAULT_WAIT_MS", MIN_AGENT_TIMEOUT_MS));
const MAX_WAIT_MS = Math.max(DEFAULT_WAIT_MS, readIntEnv("CLAUDE_MCP_MAX_WAIT_MS", MIN_AGENT_TIMEOUT_MS));
const DEFAULT_WRITE_TIMEOUT_MS = Math.max(MIN_AGENT_TIMEOUT_MS, readIntEnv("CLAUDE_MCP_WRITE_TIMEOUT_MS", MIN_AGENT_TIMEOUT_MS));
const MAX_DIFF_BYTES = Number.parseInt(process.env.CLAUDE_MCP_MAX_DIFF_BYTES || "200000", 10);
const MAX_STDIO_BYTES = Number.parseInt(process.env.CLAUDE_MCP_MAX_STDIO_BYTES || "200000", 10);
const RUN_AUDIT_PATH = resolve(
  process.env.CLAUDE_MCP_RUN_AUDIT_PATH || join(DEFAULT_WORKDIR, ".agent-bridge", "claude-mcp-runs.jsonl")
);
const LIFECYCLE_AUDIT_PATH = resolve(
  process.env.CLAUDE_MCP_LIFECYCLE_AUDIT_PATH || join(DEFAULT_WORKDIR, ".agent-bridge", "claude-mcp-lifecycle.jsonl")
);

function readIntEnv(name, fallback) {
  const value = Number.parseInt(process.env[name] || String(fallback), 10);
  return Number.isFinite(value) ? value : fallback;
}

function resolveTimeoutMs(requested, defaultMs, maxMs) {
  const requestedMs = Number.isFinite(requested) ? requested : defaultMs;
  return Math.min(maxMs, Math.max(defaultMs, requestedMs));
}

const lifecycle = installLifecycleAudit({
  name: "claude-mcp",
  logPath: LIFECYCLE_AUDIT_PATH,
  recordUnhandledRejection: true,
});

const VALID_PERMISSION_MODES = new Set(["acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan"]);
const VALID_EFFORTS = new Set(["low", "medium", "high", "xhigh", "max"]);

const tasks = new Map();
let seq = 0;

const BARE_DISABLED_MESSAGE =
  "bare:true is disabled for this claude-coder MCP server. In the current OAuth/Max setup, Claude Code --bare skips OAuth/keychain auth and requires ANTHROPIC_API_KEY or apiKeyHelper via --settings. Retry without bare (omit bare or set bare:false). Set CLAUDE_MCP_ALLOW_BARE=1 only after wiring API-key/apiKeyHelper auth for this MCP process.";

function log(message) {
  process.stderr.write(`[${SERVER_NAME}] ${message}\n`);
}

function makeRunId(prefix = "claude_run") {
  return `${prefix}_${Date.now().toString(36)}_${(++seq).toString(36)}`;
}

async function appendRunAudit(record) {
  try {
    await mkdir(dirname(RUN_AUDIT_PATH), { recursive: true });
    await appendFile(RUN_AUDIT_PATH, `${JSON.stringify(record)}\n`, "utf8");
  } catch (err) {
    log(`run audit write failed: ${err?.message || String(err)}`);
  }
}

function safeEnv() {
  const env = { ...process.env };
  if (STRIP_API_KEY) {
    delete env.ANTHROPIC_API_KEY;
    delete env.ANTHROPIC_AUTH_TOKEN;
    delete env.ANTHROPIC_BASE_URL;
  }
  return env;
}

function normalizeWorkdir(input) {
  const wd = resolve(input || DEFAULT_WORKDIR);
  const ok = ALLOWED_WORKDIRS.some((base) => {
    const rel = relative(base, wd);
    return rel === "" || (!rel.startsWith("..") && !rel.startsWith("/"));
  });
  if (!ok) throw new Error(`workingDirectory is outside allowed roots: ${wd}`);
  return wd;
}

function normalizeAddDirs(input) {
  if (!Array.isArray(input)) return [];
  return input.map((entry) => {
    if (typeof entry !== "string" || !entry.trim()) {
      throw new Error("every addDirs entry must be a non-empty path");
    }
    return normalizeWorkdir(entry);
  });
}

function normalizeFallbackModel(input) {
  if (typeof input !== "string" || !input.trim()) return null;
  const requested = input.trim();
  const model = MODEL_ALIASES.get(requested) || requested;
  if (ALLOWED_MODELS.length && !ALLOWED_MODELS.includes(requested) && !ALLOWED_MODELS.includes(model)) {
    throw new Error(`fallback model not allowed: ${requested}; allowed=${ALLOWED_MODELS.join(",")}`);
  }
  return model;
}

function normalizeOptions(args = {}, { write = false } = {}) {
  const requestedModel = args.model || DEFAULT_MODEL;
  const model = MODEL_ALIASES.get(requestedModel) || requestedModel;
  if (ALLOWED_MODELS.length && !ALLOWED_MODELS.includes(requestedModel) && !ALLOWED_MODELS.includes(model)) {
    throw new Error(`model not allowed: ${requestedModel}; allowed=${ALLOWED_MODELS.join(",")}`);
  }
  const permissionMode = args.permissionMode || (write ? DEFAULT_WRITE_PERMISSION_MODE : DEFAULT_PERMISSION_MODE);
  if (!VALID_PERMISSION_MODES.has(permissionMode)) {
    throw new Error(`Invalid permissionMode: ${permissionMode}`);
  }
  const dangerous = Boolean(args.dangerouslySkipPermissions);
  if (dangerous && !ALLOW_DANGEROUS) {
    throw new Error("dangerouslySkipPermissions is disabled. Set CLAUDE_MCP_ALLOW_DANGEROUS=1 to allow it.");
  }
  const effort = args.effort || DEFAULT_EFFORT;
  if (!VALID_EFFORTS.has(effort)) throw new Error(`Invalid effort: ${effort}`);
  const bare = args.bare ?? DEFAULT_BARE;
  if (bare && !ALLOW_BARE) {
    throw new Error(BARE_DISABLED_MESSAGE);
  }
  return {
    model,
    requestedModel,
    workingDirectory: normalizeWorkdir(args.workingDirectory),
    permissionMode,
    dangerous,
    effort,
    bare,
    addDirs: normalizeAddDirs(args.addDirs),
    allowedTools: Array.isArray(args.allowedTools) ? args.allowedTools : null,
    disallowedTools: Array.isArray(args.disallowedTools) ? args.disallowedTools : null,
    sessionId: typeof args.sessionId === "string" ? args.sessionId : null,
    appendSystemPrompt: typeof args.appendSystemPrompt === "string" ? args.appendSystemPrompt : null,
    maxBudgetUsd: typeof args.maxBudgetUsd === "number" ? args.maxBudgetUsd : null,
    fallbackModel: normalizeFallbackModel(args.fallbackModel),
  };
}

function assertPrompt(prompt) {
  if (typeof prompt !== "string" || !prompt.trim()) throw new Error("prompt is required");
  if (prompt.length > MAX_PROMPT_CHARS) {
    throw new Error(`prompt too large: ${prompt.length} > ${MAX_PROMPT_CHARS}`);
  }
}

function truncateText(text, maxBytes = MAX_STDIO_BYTES) {
  if (typeof text !== "string") return "";
  const buf = Buffer.from(text, "utf8");
  if (buf.length <= maxBytes) return text;
  return `${buf.subarray(0, maxBytes).toString("utf8")}\n...[truncated ${buf.length - maxBytes} bytes]`;
}

function buildClaudeArgs(options, { resumeSessionId = null } = {}) {
  const args = ["-p", "--output-format", "json"];
  args.push("--model", options.model);
  args.push("--effort", options.effort);
  if (options.dangerous) {
    args.push("--dangerously-skip-permissions");
  } else {
    args.push("--permission-mode", options.permissionMode);
  }
  if (options.bare) args.push("--bare");
  if (resumeSessionId) {
    args.push("--resume", resumeSessionId);
  } else if (options.sessionId) {
    args.push("--session-id", options.sessionId);
  }
  for (const d of options.addDirs || []) args.push("--add-dir", d);
  if (options.allowedTools && options.allowedTools.length) {
    args.push("--allowedTools", ...options.allowedTools);
  }
  if (options.disallowedTools && options.disallowedTools.length) {
    args.push("--disallowedTools", ...options.disallowedTools);
  }
  if (options.appendSystemPrompt) {
    args.push("--append-system-prompt", options.appendSystemPrompt);
  }
  if (options.maxBudgetUsd !== null) {
    args.push("--max-budget-usd", String(options.maxBudgetUsd));
  }
  if (options.fallbackModel) {
    args.push("--fallback-model", options.fallbackModel);
  }
  return args;
}

async function gitSnapshot(workdir) {
  const [status, stat, diff] = await Promise.all([
    execFileAsync("git", ["status", "--short"], { cwd: workdir, timeout: 10_000 }).catch((err) => ({ stdout: "", stderr: err.message })),
    execFileAsync("git", ["diff", "--stat"], { cwd: workdir, timeout: 10_000 }).catch((err) => ({ stdout: "", stderr: err.message })),
    execFileAsync("git", ["diff"], { cwd: workdir, timeout: 20_000, maxBuffer: MAX_DIFF_BYTES * 2 }).catch((err) => ({ stdout: "", stderr: err.message })),
  ]);
  const statusText = status.stdout || status.stderr || "";
  return {
    status_short: truncateText(statusText, MAX_STDIO_BYTES),
    diff_stat: truncateText(stat.stdout || stat.stderr || "", MAX_STDIO_BYTES),
    changed_files: parseStatusFiles(statusText),
    untracked_files: parseStatusFiles(statusText, "??"),
    diff: truncateText(diff.stdout || diff.stderr || "", MAX_DIFF_BYTES),
  };
}

function parseStatusFiles(statusText, filterStatus = null) {
  const files = [];
  for (const line of statusText.split("\n")) {
    if (!line.trim()) continue;
    const status = line.slice(0, 2);
    if (filterStatus && status !== filterStatus) continue;
    let file = line.slice(3).trim();
    const renameMarker = " -> ";
    if (file.includes(renameMarker)) file = file.slice(file.indexOf(renameMarker) + renameMarker.length);
    if (file) files.push(file);
  }
  return files;
}

function buildWorkerPrompt(args) {
  const lines = [
    args.prompt.trim(),
    "",
    "Coding worker constraints:",
    "- You are an implementation worker, not the design owner.",
    "- Implement the caller's explicit design/request; do not make product or architecture decisions on your own.",
    "- If the request or design document is ambiguous, stop and explain the missing decision instead of guessing.",
    "- Make only the requested code changes.",
    "- Do not revert or rewrite unrelated user/session changes.",
    "- Keep changes scoped and consistent with existing local patterns.",
    "- Do not commit changes.",
    "- If blocked, stop after explaining the blocker in the final response.",
  ];
  if (Array.isArray(args.changedFilesOnly) && args.changedFilesOnly.length) {
    lines.push(`- Restrict edits to these paths: ${args.changedFilesOnly.join(", ")}`);
  }
  if (args.testCommand) {
    lines.push(`- After editing, run this verification command if feasible: ${args.testCommand}`);
  }
  return lines.join("\n");
}

function spawnClaude({ prompt, options, timeoutMs, resumeSessionId = null }) {
  const args = buildClaudeArgs(options, { resumeSessionId });
  return new Promise((resolveRun) => {
    const child = spawn(CLAUDE_BIN, args, {
      cwd: options.workingDirectory,
      env: safeEnv(),
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const killTimer = setTimeout(() => {
      timedOut = true;
      try { child.kill("SIGTERM"); } catch {}
      const hard = setTimeout(() => { try { child.kill("SIGKILL"); } catch {} }, 5_000);
      if (hard.unref) hard.unref();
    }, timeoutMs);
    if (killTimer.unref) killTimer.unref();
    child.stdout.on("data", (chunk) => {
      const next = stdout + chunk.toString("utf8");
      // Keep room for both the structured JSON and any tail diagnostics.
      stdout = next.length > MAX_STDIO_BYTES * 4
        ? next.slice(next.length - MAX_STDIO_BYTES * 4)
        : next;
    });
    child.stderr.on("data", (chunk) => {
      stderr = truncateText(stderr + chunk.toString("utf8"), MAX_STDIO_BYTES);
    });
    child.on("error", (err) => {
      clearTimeout(killTimer);
      resolveRun({ exitCode: null, timedOut, stdout, stderr: `${stderr}\n${err.message}`.trim(), parsed: null });
    });
    child.on("close", (code) => {
      clearTimeout(killTimer);
      let parsed = null;
      // Claude --output-format json prints a single JSON object. If extra logs leak in,
      // try to find the last well-formed JSON object on the stream.
      try { parsed = JSON.parse(stdout); } catch {
        const trimmed = stdout.trim();
        const lastBrace = trimmed.lastIndexOf("\n{");
        if (lastBrace >= 0) {
          try { parsed = JSON.parse(trimmed.slice(lastBrace + 1)); } catch {}
        }
      }
      resolveRun({ exitCode: code, timedOut, stdout, stderr, parsed });
    });
    child.stdin.end(prompt);
  });
}

function summarizeRun(run, options, runId) {
  const status = run.exitCode === 0 && !run.timedOut && run.parsed && !run.parsed.is_error
    ? "completed"
    : "failed";
  return {
    status,
    run_id: runId,
    model: options.model,
    requested_model: options.requestedModel,
    workingDirectory: options.workingDirectory,
    permissionMode: options.dangerous ? "(dangerouslySkipPermissions)" : options.permissionMode,
    effort: options.effort,
    bare: Boolean(options.bare),
    exit_code: run.exitCode,
    timed_out: run.timedOut,
    session_id: run.parsed?.session_id || null,
    final_response: truncateText(run.parsed?.result || "", MAX_STDIO_BYTES),
    usage: run.parsed?.usage || null,
    total_cost_usd: run.parsed?.total_cost_usd ?? null,
    duration_ms: run.parsed?.duration_ms ?? null,
    num_turns: run.parsed?.num_turns ?? null,
    stop_reason: run.parsed?.stop_reason ?? null,
    permission_denials: run.parsed?.permission_denials ?? null,
    parse_failed: run.parsed === null,
    stdout_tail: run.parsed === null ? truncateText(run.stdout, MAX_STDIO_BYTES) : undefined,
    stderr_tail: truncateText(run.stderr, MAX_STDIO_BYTES),
  };
}

async function runReadTask(args = {}) {
  assertPrompt(args.prompt);
  const options = normalizeOptions(args, { write: false });
  const runId = makeRunId("claude_read");
  const startedAt = new Date().toISOString();
  const timeoutMs = resolveTimeoutMs(args.timeout_ms, DEFAULT_WAIT_MS, MAX_WAIT_MS);
  const run = await spawnClaude({ prompt: args.prompt, options, timeoutMs });
  const result = {
    ...summarizeRun(run, options, runId),
    audit_log: RUN_AUDIT_PATH,
  };
  await appendRunAudit({
    schema: "claude_mcp_run.v1",
    run_id: runId,
    tool: "claude_run_task",
    started_at: startedAt,
    ended_at: new Date().toISOString(),
    timeout_ms: timeoutMs,
    ...result,
    final_response_tail: truncateText(result.final_response, 20_000),
    stderr_tail: truncateText(run.stderr, 20_000),
  });
  return result;
}

async function runWriteTask(args = {}) {
  assertPrompt(args.prompt);
  const options = normalizeOptions(args, { write: true });
  const writeOkModes = new Set(["acceptEdits", "bypassPermissions"]);
  if (!writeOkModes.has(options.permissionMode) && !options.dangerous) {
    throw new Error(`claude_run_write_task requires permissionMode in {acceptEdits, bypassPermissions} or dangerouslySkipPermissions=true; got ${options.permissionMode}`);
  }
  const runId = makeRunId("claude_write");
  const startedAt = new Date().toISOString();
  const timeoutMs = resolveTimeoutMs(args.timeout_ms, DEFAULT_WRITE_TIMEOUT_MS, 7_200_000);
  const before = await gitSnapshot(options.workingDirectory);
  const workerPrompt = buildWorkerPrompt(args);
  const run = await spawnClaude({ prompt: workerPrompt, options, timeoutMs });
  const after = await gitSnapshot(options.workingDirectory);
  const beforeSet = new Set(before.changed_files);
  const newChangedFiles = after.changed_files.filter((f) => !beforeSet.has(f));
  const summary = summarizeRun(run, options, runId);
  const result = {
    ...summary,
    dirty_before: before.status_short,
    dirty_after: after.status_short,
    changed_files: after.changed_files,
    new_changed_files: newChangedFiles,
    untracked_files: after.untracked_files,
    diff_stat: after.diff_stat,
    diff: args.include_diff ? after.diff : undefined,
    audit_log: RUN_AUDIT_PATH,
    note: before.changed_files.length
      ? "Worktree was already dirty before Claude ran. Review dirty_before before attributing all changes to this task."
      : "",
  };
  await appendRunAudit({
    schema: "claude_mcp_run.v1",
    run_id: runId,
    tool: "claude_run_write_task",
    started_at: startedAt,
    ended_at: new Date().toISOString(),
    timeout_ms: timeoutMs,
    ...summary,
    dirty_before: result.dirty_before,
    dirty_after: result.dirty_after,
    changed_files: result.changed_files,
    new_changed_files: newChangedFiles,
    untracked_files: result.untracked_files,
    diff_stat: result.diff_stat,
    final_response_tail: truncateText(summary.final_response, 20_000),
    stderr_tail: truncateText(run.stderr, 20_000),
  });
  return result;
}

async function continueThread(args = {}) {
  assertPrompt(args.prompt);
  if (!args.session_id && !args.task_id) throw new Error("session_id or task_id is required");
  const write = args.write !== false;
  const options = normalizeOptions(args, { write });
  let resumeSessionId = args.session_id || null;
  if (!resumeSessionId && args.task_id) {
    const prior = tasks.get(args.task_id);
    if (!prior) throw new Error(`Unknown task_id: ${args.task_id}`);
    resumeSessionId = prior.session_id || null;
    if (!resumeSessionId) throw new Error(`Task has no session_id: ${args.task_id}`);
  }
  const runId = makeRunId("claude_cont");
  const startedAt = new Date().toISOString();
  const timeoutMs = resolveTimeoutMs(args.timeout_ms, DEFAULT_WRITE_TIMEOUT_MS, 7_200_000);
  const before = write ? await gitSnapshot(options.workingDirectory) : null;
  const run = await spawnClaude({ prompt: args.prompt, options, timeoutMs, resumeSessionId });
  const after = write ? await gitSnapshot(options.workingDirectory) : null;
  const beforeSet = before ? new Set(before.changed_files) : null;
  const newChangedFiles = after && beforeSet ? after.changed_files.filter((f) => !beforeSet.has(f)) : [];
  const summary = summarizeRun(run, options, runId);
  const result = {
    ...summary,
    parent_session_id: resumeSessionId,
    dirty_before: before?.status_short,
    dirty_after: after?.status_short,
    changed_files: after?.changed_files,
    new_changed_files: newChangedFiles,
    untracked_files: after?.untracked_files,
    diff_stat: after?.diff_stat,
    audit_log: RUN_AUDIT_PATH,
  };
  await appendRunAudit({
    schema: "claude_mcp_run.v1",
    run_id: runId,
    tool: "claude_continue_thread",
    parent_session_id: resumeSessionId,
    started_at: startedAt,
    ended_at: new Date().toISOString(),
    timeout_ms: timeoutMs,
    ...summary,
    changed_files: result.changed_files,
    final_response_tail: truncateText(summary.final_response, 20_000),
    stderr_tail: truncateText(run.stderr, 20_000),
  });
  return result;
}

async function checkClaudeHealth() {
  try {
    const { stdout, stderr } = await execFileAsync(CLAUDE_BIN, ["--version"], {
      env: safeEnv(),
      timeout: 10_000,
    });
    return { ok: true, version: (stdout || stderr || "").trim() };
  } catch (err) {
    return { ok: false, version: "", error: err?.message || String(err) };
  }
}

const tools = [
  {
    name: "claude_health",
    description: "Check that local Claude Code CLI is available and report its version + this MCP server's defaults.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "claude_run_task",
    description: "Run a Claude Code session in --print/json mode without write permission. Best for analysis, design review, code reading, or read-only tool work.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string" },
        workingDirectory: { type: "string" },
        model: { type: "string", description: `Claude model alias or full model id. Allowed: ${ALLOWED_MODELS.join(",")}` },
        effort: { type: "string", enum: ["low", "medium", "high", "xhigh", "max"] },
        permissionMode: { type: "string", enum: ["acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan"] },
        bare: { type: "boolean", description: "Disabled by default for this OAuth/Max setup. Do not set bare:true unless CLAUDE_MCP_ALLOW_BARE=1 and API-key/apiKeyHelper auth is wired; omit it or set false." },
        addDirs: { type: "array", items: { type: "string" } },
        allowedTools: { type: "array", items: { type: "string" } },
        disallowedTools: { type: "array", items: { type: "string" } },
        appendSystemPrompt: { type: "string" },
        sessionId: { type: "string", description: "Optional UUID to bind this run to. Used for later resume." },
        timeout_ms: { type: "number", description: "Wait timeout. Values below the 30 minute default are raised to the default; capped by CLAUDE_MCP_MAX_WAIT_MS." },
        maxBudgetUsd: { type: "number" },
        fallbackModel: { type: "string" },
      },
      required: ["prompt"],
      additionalProperties: false,
    },
  },
  {
    name: "claude_run_write_task",
    description: "Run Claude Code as an implementation worker with write permission. Captures git diff before/after and changed files. Default permissionMode=acceptEdits.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string" },
        workingDirectory: { type: "string" },
        model: { type: "string", description: `Allowed: ${ALLOWED_MODELS.join(",")}` },
        effort: { type: "string", enum: ["low", "medium", "high", "xhigh", "max"] },
        permissionMode: { type: "string", enum: ["acceptEdits", "bypassPermissions"], description: "Defaults to acceptEdits for write tasks." },
        dangerouslySkipPermissions: { type: "boolean", description: "Bypass ALL permission checks via --dangerously-skip-permissions. Requires CLAUDE_MCP_ALLOW_DANGEROUS=1." },
        bare: { type: "boolean", description: "Disabled by default for this OAuth/Max setup. Omit it or set false unless CLAUDE_MCP_ALLOW_BARE=1 and API-key/apiKeyHelper auth is wired." },
        addDirs: { type: "array", items: { type: "string" } },
        allowedTools: { type: "array", items: { type: "string" } },
        disallowedTools: { type: "array", items: { type: "string" } },
        appendSystemPrompt: { type: "string" },
        sessionId: { type: "string" },
        timeout_ms: { type: "number", description: "Execution timeout. Values below the 30 minute default are raised to the default." },
        testCommand: { type: "string", description: "Verification command Claude should run after editing if feasible." },
        changedFilesOnly: { type: "array", items: { type: "string" }, description: "Restrict edits to these paths." },
        include_diff: { type: "boolean" },
        maxBudgetUsd: { type: "number" },
        fallbackModel: { type: "string" },
      },
      required: ["prompt"],
      additionalProperties: false,
    },
  },
  {
    name: "claude_continue_thread",
    description: "Resume a previous Claude session by session_id (or by task_id from this server) and run another turn. Defaults to write mode (captures diff).",
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string" },
        session_id: { type: "string" },
        task_id: { type: "string" },
        workingDirectory: { type: "string" },
        model: { type: "string" },
        effort: { type: "string", enum: ["low", "medium", "high", "xhigh", "max"] },
        permissionMode: { type: "string", enum: ["acceptEdits", "auto", "bypassPermissions", "default", "dontAsk", "plan"] },
        dangerouslySkipPermissions: { type: "boolean" },
        bare: { type: "boolean", description: "Disabled by default for this OAuth/Max setup. Omit it or set false unless CLAUDE_MCP_ALLOW_BARE=1 and API-key/apiKeyHelper auth is wired." },
        write: { type: "boolean", description: "Whether this continuation is a write turn (capture diff). Default true." },
        timeout_ms: { type: "number", description: "Execution timeout. Values below the 30 minute default are raised to the default." },
        maxBudgetUsd: { type: "number" },
      },
      required: ["prompt"],
      additionalProperties: false,
    },
  },
  {
    name: "claude_list_runs",
    description: "List recent Claude runs tracked by this MCP server process.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
];

function evictOldTasks() {
  while (tasks.size > MAX_TASKS) {
    const first = tasks.keys().next().value;
    if (!first) return;
    tasks.delete(first);
  }
}

async function callTool(name, args = {}) {
  switch (name) {
    case "claude_health": {
      const h = await checkClaudeHealth();
      return {
        ok: h.ok,
        server_pid: process.pid,
        server_started_at: SERVER_STARTED_AT.toISOString(),
        server_uptime_ms: Date.now() - SERVER_STARTED_AT.getTime(),
        supervised_by: process.env.MCP_SUPERVISOR_PID || null,
        supervised_name: process.env.MCP_SUPERVISED_SERVER_NAME || null,
        claude_bin: CLAUDE_BIN,
        version: h.version,
        error: h.error || null,
        default_model: DEFAULT_MODEL,
        allowed_models: ALLOWED_MODELS,
        model_aliases: Object.fromEntries(MODEL_ALIASES),
        allowed_workdirs: ALLOWED_WORKDIRS,
        default_workdir: DEFAULT_WORKDIR,
        default_permission_mode: DEFAULT_PERMISSION_MODE,
        default_write_permission_mode: DEFAULT_WRITE_PERMISSION_MODE,
        default_effort: DEFAULT_EFFORT,
        default_bare: DEFAULT_BARE,
        allow_bare: ALLOW_BARE,
        bare_supported: ALLOW_BARE,
        bare_note: ALLOW_BARE
          ? "bare:true is allowed by CLAUDE_MCP_ALLOW_BARE=1; caller must ensure API-key/apiKeyHelper auth works."
          : BARE_DISABLED_MESSAGE,
        allow_dangerous: ALLOW_DANGEROUS,
        strip_api_key: STRIP_API_KEY,
        audit_log: RUN_AUDIT_PATH,
      };
    }
    case "claude_run_task": {
      const result = await runReadTask(args);
      tasks.set(result.run_id, {
        run_id: result.run_id,
        tool: "claude_run_task",
        session_id: result.session_id,
        status: result.status,
        model: result.model,
        created_at: new Date().toISOString(),
      });
      evictOldTasks();
      return result;
    }
    case "claude_run_write_task": {
      const result = await runWriteTask(args);
      tasks.set(result.run_id, {
        run_id: result.run_id,
        tool: "claude_run_write_task",
        session_id: result.session_id,
        status: result.status,
        model: result.model,
        changed_files: result.new_changed_files,
        created_at: new Date().toISOString(),
      });
      evictOldTasks();
      return result;
    }
    case "claude_continue_thread": {
      const result = await continueThread(args);
      tasks.set(result.run_id, {
        run_id: result.run_id,
        tool: "claude_continue_thread",
        session_id: result.session_id,
        parent_session_id: result.parent_session_id,
        status: result.status,
        model: result.model,
        created_at: new Date().toISOString(),
      });
      evictOldTasks();
      return result;
    }
    case "claude_list_runs":
      return [...tasks.values()];
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

function resultContent(value) {
  return {
    content: [
      { type: "text", text: typeof value === "string" ? value : JSON.stringify(value, null, 2) },
    ],
  };
}

async function handle(msg) {
  const { id, method, params = {} } = msg;
  if (method === "initialize") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
      },
    };
  }
  if (method === "notifications/initialized") return null;
  if (method === "tools/list") return { jsonrpc: "2.0", id, result: { tools } };
  if (method === "tools/call") {
    try {
      const value = await callTool(params.name, params.arguments || {});
      return { jsonrpc: "2.0", id, result: resultContent(value) };
    } catch (err) {
      return {
        jsonrpc: "2.0",
        id,
        result: { isError: true, content: [{ type: "text", text: err?.message || String(err) }] },
      };
    }
  }
  if (id !== undefined) {
    return { jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${method}` } };
  }
  return null;
}

const rl = createInterface({ input: process.stdin, terminal: false });

let stdoutLock = Promise.resolve();
function writeOutput(resp) {
  stdoutLock = stdoutLock.then(() => {
    process.stdout.write(`${JSON.stringify(resp)}\n`);
  });
  return stdoutLock;
}

let inflight = 0;
rl.on("line", (line) => {
  if (!line.trim()) return;
  inflight++;
  (async () => {
    try {
      const msg = JSON.parse(line);
      const resp = await handle(msg);
      if (resp) await writeOutput(resp);
    } catch (err) {
      log(`parse/handle error: ${err?.message || String(err)}`);
    } finally {
      inflight--;
    }
  })();
});

rl.on("close", () => {
  lifecycle.recordEvent("stdin_close", { inflight });
  const drain = () => {
    if (inflight === 0) {
      stdoutLock.finally(() => process.exit(0));
    } else {
      setTimeout(drain, 100);
    }
  };
  drain();
});

process.on("uncaughtException", (err) => {
  log(`uncaught exception kept server alive: ${err?.stack || err?.message || String(err)}`);
});
process.on("unhandledRejection", (reason) => {
  log(`unhandled rejection kept server alive: ${reason?.stack || reason?.message || String(reason)}`);
});
process.on("SIGTERM", () => process.exit(0));
process.on("SIGINT", () => process.exit(0));
