#!/usr/bin/env node

import {
  closeSync,
  copyFileSync,
  createReadStream,
  fsyncSync,
  mkdirSync,
  openSync,
  readSync,
  readFileSync,
  realpathSync,
  renameSync,
  statSync,
  unlinkSync,
  writeFileSync,
  writeSync,
} from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { isAbsolute, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const DEFAULT_TIMEOUT_SECONDS = 21_600;
const TERMINATION_GRACE_MS = 1_000;
const MAX_EVENT_LINE_BYTES = 4 * 1024 * 1024;
function codexBin() {
  return process.env.CODEX_BIN || "codex";
}

const HELP = `Usage: run.mjs <command> [options]

Commands:
  run       Start a new Codex exec turn.
  resume    Resume an explicit Codex thread.
  status    Read run metadata without starting Codex.
  health    Check Codex version and login status.

Run/resume options:
  --workdir ABS              Project directory used as Codex cwd (required).
  --prompt-file ABS          Prompt file sent on stdin (required).
  --run-dir ABS              New exclusive artifact directory (required).
  --sandbox MODE             read-only (default), workspace-write, or danger-full-access.
  --model ID                 Override the model; otherwise Codex config is inherited.
  --ignore-user-config       Skip user Codex config for this invocation (run/resume only).
  --timeout-seconds N        Timeout in seconds (default: ${DEFAULT_TIMEOUT_SECONDS}).

Resume-only option:
  --thread UUID              Explicit thread/session UUID; --last is unsupported.

Other:
  -h, --help                 Show this help.

Artifacts in --run-dir:
  prompt.md, result.md, events.jsonl, stderr.log, status.json
`;

class CliError extends Error {}

function now() {
  return new Date().toISOString();
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeEventType(value) {
  if (typeof value !== "string") return "";
  return value.replaceAll("/", ".");
}

function eventType(message) {
  return normalizeEventType(message.type ?? message.method ?? message.event);
}

function threadFromEvent(message) {
  if (eventType(message) !== "thread.started") return null;
  const params = isObject(message.params) ? message.params : null;
  const thread = isObject(message.thread) ? message.thread : null;
  const paramsThread = params && isObject(params.thread) ? params.thread : null;
  const candidate =
    message.thread_id ??
    message.threadId ??
    thread?.id ??
    params?.thread_id ??
    params?.threadId ??
    paramsThread?.id;
  return typeof candidate === "string" && candidate.length > 0 ? candidate : null;
}

function writeAll(fd, data) {
  let offset = 0;
  while (offset < data.length) {
    offset += writeSync(fd, data, offset, data.length - offset);
  }
}

function writeJsonAtomic(path, value) {
  const tempPath = `${path}.tmp-${process.pid}-${randomBytes(8).toString("hex")}`;
  let fd;
  try {
    fd = openSync(tempPath, "wx", 0o600);
    const body = `${JSON.stringify(value, null, 2)}\n`;
    writeFileSync(fd, body, "utf8");
    fsyncSync(fd);
    closeSync(fd);
    fd = undefined;
    renameSync(tempPath, path);
  } catch (error) {
    if (fd !== undefined) {
      try { closeSync(fd); } catch {}
    }
    try { unlinkSync(tempPath); } catch {}
    throw error;
  }
}

function requireAbsolute(value, option) {
  if (typeof value !== "string" || value.length === 0 || !isAbsolute(value)) {
    throw new CliError(`${option} must be an absolute path`);
  }
  return resolve(value);
}

function requireExistingDirectory(value, option) {
  const path = requireAbsolute(value, option);
  let real;
  try {
    real = realpathSync(path);
    if (!statSync(real).isDirectory()) throw new Error("not a directory");
  } catch {
    throw new CliError(`${option} must name an existing directory`);
  }
  return real;
}

function requireExistingFile(value, option) {
  const path = requireAbsolute(value, option);
  let real;
  try {
    real = realpathSync(path);
    if (!statSync(real).isFile()) throw new Error("not a file");
  } catch {
    throw new CliError(`${option} must name an existing file`);
  }
  return real;
}

function createExclusiveRunDir(value) {
  const path = requireAbsolute(value, "--run-dir");
  try {
    // A non-recursive mkdir is intentional: EEXIST leaves an existing directory,
    // regular file, or symlink entirely untouched.
    mkdirSync(path, { mode: 0o700 });
  } catch {
    throw new CliError("--run-dir must be a new path; existing paths are rejected");
  }
  return path;
}

function parseTimeout(value) {
  if (typeof value !== "string" || !/^\d+$/.test(value)) {
    throw new CliError("--timeout-seconds must be a positive integer");
  }
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0 || parsed > 2_147_483) {
    throw new CliError("--timeout-seconds must be a positive integer <= 2147483");
  }
  return parsed;
}

function optionValue(argv, index, option, inlineValue) {
  if (inlineValue !== undefined) {
    if (inlineValue.length === 0) throw new CliError(`${option} needs a value`);
    return { value: inlineValue, next: index + 1 };
  }
  const value = argv[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new CliError(`${option} needs a value`);
  }
  return { value, next: index + 2 };
}

function parseCli(argv) {
  if (argv.length === 0 || argv.includes("--help") || argv.includes("-h")) {
    return { command: "help" };
  }

  const command = argv[0];
  if (!["run", "resume", "status", "health"].includes(command)) {
    throw new CliError(`unknown command: ${command}`);
  }

  const values = {
    command,
    sandbox: "read-only",
    timeoutSeconds: DEFAULT_TIMEOUT_SECONDS,
  };
  let index = 1;
  while (index < argv.length) {
    const token = argv[index];
    if (!token.startsWith("--")) throw new CliError(`unexpected argument: ${token}`);
    const equals = token.indexOf("=");
    const option = equals === -1 ? token : token.slice(0, equals);
    const inlineValue = equals === -1 ? undefined : token.slice(equals + 1);

    if (token === "--ignore-user-config") {
      values.ignoreUserConfig = true;
      index += 1;
      continue;
    }
    if (option === "--ignore-user-config") {
      throw new CliError("--ignore-user-config does not take a value");
    }

    if (option === "--last") {
      throw new CliError("--last is unsupported; resume requires --thread UUID");
    }

    const optionNames = {
      "--workdir": "workdir",
      "--prompt-file": "promptFile",
      "--run-dir": "runDir",
      "--sandbox": "sandbox",
      "--model": "model",
      "--timeout-seconds": "timeoutSeconds",
      "--thread": "thread",
    };
    const key = optionNames[option];
    if (!key) throw new CliError(`unknown option: ${option}`);
    const parsed = optionValue(argv, index, option, inlineValue);
    values[key] = parsed.value;
    index = parsed.next;
  }

  if (command === "health") {
    if (Object.keys(values).some((key) => !["command"].includes(key) && values[key] !== undefined &&
        !(key === "sandbox" && values[key] === "read-only") &&
        !(key === "timeoutSeconds" && values[key] === DEFAULT_TIMEOUT_SECONDS))) {
      throw new CliError("health does not accept run options");
    }
    return values;
  }
  if (command === "status") {
    if (values.runDir === undefined) throw new CliError("status requires --run-dir ABS");
    if (values.workdir !== undefined || values.promptFile !== undefined || values.model !== undefined ||
        values.thread !== undefined || values.ignoreUserConfig !== undefined || values.sandbox !== "read-only" ||
        values.timeoutSeconds !== DEFAULT_TIMEOUT_SECONDS) {
      throw new CliError("status accepts only --run-dir ABS");
    }
    return values;
  }

  for (const [key, option] of [["workdir", "--workdir"], ["promptFile", "--prompt-file"], ["runDir", "--run-dir"]]) {
    if (values[key] === undefined) throw new CliError(`${command} requires ${option} ABS`);
  }
  if (command === "run" && values.thread !== undefined) {
    throw new CliError("run does not accept --thread; use resume");
  }
  if (command === "resume" && (typeof values.thread !== "string" || values.thread.length === 0 || values.thread === "--last")) {
    throw new CliError("resume requires --thread UUID");
  }
  if (!Object.hasOwn({ "read-only": true, "workspace-write": true, "danger-full-access": true }, values.sandbox)) {
    throw new CliError("--sandbox must be read-only, workspace-write, or danger-full-access");
  }
  values.timeoutSeconds = parseTimeout(String(values.timeoutSeconds));
  if (values.model !== undefined && values.model.length === 0) throw new CliError("--model needs a value");
  return values;
}

function makePaths(runDir) {
  return {
    run_dir: runDir,
    prompt: join(runDir, "prompt.md"),
    result: join(runDir, "result.md"),
    events: join(runDir, "events.jsonl"),
    stderr: join(runDir, "stderr.log"),
    status: join(runDir, "status.json"),
  };
}

function createEmptyArtifact(path) {
  const fd = openSync(path, "wx", 0o600);
  closeSync(fd);
}

function hasResultContent(path) {
  let fd;
  try {
    fd = openSync(path, "r");
    const chunk = Buffer.allocUnsafe(64 * 1024);
    while (true) {
      const count = readSync(fd, chunk, 0, chunk.length, null);
      if (count === 0) return false;
      for (let index = 0; index < count; index += 1) {
        const byte = chunk[index];
        if (byte !== 0x09 && byte !== 0x0a && byte !== 0x0d && byte !== 0x20) return true;
      }
    }
  } catch {
    return false;
  } finally {
    if (fd !== undefined) {
      try { closeSync(fd); } catch {}
    }
  }
}

function processExists(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

function signalGroup(child, signal) {
  if (!child?.pid) return false;
  try {
    if (process.platform === "win32") child.kill(signal);
    else process.kill(-child.pid, signal);
    return true;
  } catch (error) {
    if (error?.code === "ESRCH") return false;
    return false;
  }
}

class EventTracker {
  constructor(onThread) {
    this.pending = Buffer.alloc(0);
    this.discarding = false;
    this.malformed = null;
    this.completed = false;
    this.failed = false;
    this.thread = null;
    this.onThread = onThread;
  }

  markMalformed(reason) {
    if (!this.malformed) this.malformed = reason;
  }

  consumeLine(line) {
    const text = line.toString("utf8");
    if (text.trim().length === 0) return;
    let message;
    try {
      message = JSON.parse(text);
    } catch {
      this.markMalformed("malformed_stdout_json");
      return;
    }
    if (!isObject(message)) {
      this.markMalformed("malformed_stdout_event");
      return;
    }
    const type = eventType(message);
    if (type === "thread.started") {
      const thread = threadFromEvent(message);
      if (thread && !this.thread) {
        this.thread = thread;
        this.onThread(thread);
      }
    } else if (type === "turn.completed") {
      this.completed = true;
    } else if (type === "turn.failed") {
      this.failed = true;
    }
  }

  push(chunk) {
    let offset = 0;
    while (offset < chunk.length) {
      if (this.discarding) {
        const newline = chunk.indexOf(0x0a, offset);
        if (newline === -1) return;
        this.discarding = false;
        this.pending = Buffer.alloc(0);
        offset = newline + 1;
        continue;
      }

      const newline = chunk.indexOf(0x0a, offset);
      if (newline === -1) {
        const tail = chunk.subarray(offset);
        if (this.pending.length + tail.length > MAX_EVENT_LINE_BYTES) {
          this.markMalformed("stdout_line_too_large");
          this.pending = Buffer.alloc(0);
          this.discarding = true;
          return;
        }
        this.pending = this.pending.length === 0 ? Buffer.from(tail) : Buffer.concat([this.pending, tail]);
        return;
      }

      const segment = chunk.subarray(offset, newline);
      const lineLength = this.pending.length + segment.length;
      if (lineLength > MAX_EVENT_LINE_BYTES) {
        this.markMalformed("stdout_line_too_large");
        this.pending = Buffer.alloc(0);
      } else {
        const line = this.pending.length === 0 ? segment : Buffer.concat([this.pending, segment]);
        this.pending = Buffer.alloc(0);
        this.consumeLine(line);
      }
      offset = newline + 1;
    }
  }

  finish() {
    if (this.discarding) return;
    if (this.pending.length > 0) {
      this.consumeLine(this.pending);
      this.pending = Buffer.alloc(0);
    }
  }
}

function baseStatus({ command, paths, startedAt }) {
  return {
    schema: "codex-bg-runner.v1",
    command,
    state: "running",
    started_at: startedAt,
    updated_at: startedAt,
    finished_at: null,
    runner_pid: process.pid,
    thread: null,
    exit_code: null,
    signal: null,
    reason: null,
    turn_completed: false,
    turn_failed: false,
    paths,
  };
}

function terminalStatus(status, tracker, closeResult, termination, reason, extra = {}) {
  const finishedAt = now();
  let state = "failed";
  if (termination?.kind === "timed_out") state = "timed_out";
  else if (termination?.kind === "interrupted") state = "interrupted";
  else if (!reason) state = "completed";
  return {
    ...status,
    state,
    updated_at: finishedAt,
    finished_at: finishedAt,
    thread: tracker.thread ?? status.thread ?? null,
    exit_code: closeResult?.code ?? null,
    signal: closeResult?.signal ?? null,
    reason: reason ?? null,
    turn_completed: tracker.completed,
    turn_failed: tracker.failed,
    ...(termination ? { termination } : {}),
    ...extra,
  };
}

function transportReason(tracker, resultHasContent, artifactWriteError) {
  if (artifactWriteError) return "artifact_write_failed";
  if (tracker.malformed) return tracker.malformed;
  if (tracker.failed) return "turn_failed";
  if (!tracker.completed) return "missing_turn_completed";
  if (!resultHasContent) return "empty_result";
  return null;
}

async function execute(parsed) {
  const workdir = requireExistingDirectory(parsed.workdir, "--workdir");
  const promptFile = requireExistingFile(parsed.promptFile, "--prompt-file");
  const runDir = createExclusiveRunDir(parsed.runDir);
  const paths = makePaths(runDir);
  const startedAt = now();
  const status = baseStatus({ command: parsed.command, paths, startedAt });
  let eventsFd;
  let stderrFd;

  try {
    copyFileSync(promptFile, paths.prompt);
    createEmptyArtifact(paths.result);
    eventsFd = openSync(paths.events, "wx", 0o600);
    stderrFd = openSync(paths.stderr, "wx", 0o600);
    writeJsonAtomic(paths.status, status);
  } catch (error) {
    if (eventsFd !== undefined) {
      try { closeSync(eventsFd); } catch {}
      eventsFd = undefined;
    }
    if (stderrFd !== undefined) {
      try { closeSync(stderrFd); } catch {}
      stderrFd = undefined;
    }
    const failed = terminalStatus(status, new EventTracker(() => {}), { code: null, signal: null }, null, "artifact_setup_failed", {
      detail: error?.code || "artifact_setup_error",
    });
    writeJsonAtomic(paths.status, failed);
    return 1;
  }

  const childArgs = [
    "exec",
    "--json",
    "--cd", workdir,
    "--sandbox", parsed.sandbox,
    "-c", 'approval_policy="never"',
  ];
  if (parsed.model !== undefined) childArgs.push("--model", parsed.model);
  if (parsed.ignoreUserConfig) childArgs.push("--ignore-user-config");
  // The wrapper accepts --thread; Codex exec resume consumes that UUID as its
  // explicit positional session argument (there is no Codex --thread option).
  if (parsed.command === "resume") childArgs.push("resume", parsed.thread);
  childArgs.push("-o", paths.result, "-");

  const tracker = new EventTracker((thread) => {
    status.thread = thread;
    status.updated_at = now();
    try {
      writeJsonAtomic(paths.status, status);
    } catch {
      // The terminal write below remains the authoritative failure surface.
    }
  });
  let artifactWriteError = null;
  let child;
  try {
    child = spawn(codexBin(), childArgs, {
      cwd: workdir,
      env: process.env,
      shell: false,
      detached: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
  } catch (error) {
    try { closeSync(eventsFd); } catch {}
    try { closeSync(stderrFd); } catch {}
    const failed = terminalStatus(status, tracker, { code: null, signal: null }, null, "spawn_error", {
      detail: error?.code || "spawn_error",
    });
    writeJsonAtomic(paths.status, failed);
    return 1;
  }

  let spawnError = null;
  let termination = null;
  let killTimer = null;
  let killResolve;
  let terminationKillPromise = Promise.resolve();
  const requestTermination = (kind) => {
    if (termination) return;
    termination = { kind, requested_at: now(), term_signal: "SIGTERM" };
    signalGroup(child, "SIGTERM");
    terminationKillPromise = new Promise((resolvePromise) => {
      killResolve = resolvePromise;
      killTimer = setTimeout(() => {
        termination.kill_signal = "SIGKILL";
        signalGroup(child, "SIGKILL");
        killResolve?.();
        killResolve = undefined;
      }, TERMINATION_GRACE_MS);
    });
  };

  const onSignal = (signal) => {
    if (!termination) {
      termination = {
        kind: "interrupted",
        requested_at: now(),
        parent_signal: signal,
        term_signal: "SIGTERM",
      };
      signalGroup(child, "SIGTERM");
      terminationKillPromise = new Promise((resolvePromise) => {
        killResolve = resolvePromise;
        killTimer = setTimeout(() => {
          termination.kill_signal = "SIGKILL";
          signalGroup(child, "SIGKILL");
          killResolve?.();
          killResolve = undefined;
        }, TERMINATION_GRACE_MS);
      });
    }
  };
  const onSigterm = () => onSignal("SIGTERM");
  const onSigint = () => onSignal("SIGINT");
  process.on("SIGTERM", onSigterm);
  process.on("SIGINT", onSigint);

  const timeout = setTimeout(() => requestTermination("timed_out"), parsed.timeoutSeconds * 1000);
  timeout.unref?.();

  child.on("error", (error) => {
    spawnError = error;
  });
  child.stdout.on("data", (chunk) => {
    try { writeAll(eventsFd, chunk); } catch (error) { artifactWriteError ||= error; }
    tracker.push(chunk);
  });
  child.stderr.on("data", (chunk) => {
    try { writeAll(stderrFd, chunk); } catch (error) { artifactWriteError ||= error; }
  });
  child.stdin.on("error", (error) => {
    // An early Codex exit can close stdin while the prompt stream is still
    // draining. It is evidence only when no terminal child result exists.
    if (!spawnError && error?.code !== "EPIPE") spawnError = error;
  });

  const promptStream = createReadStream(paths.prompt);
  promptStream.on("error", (error) => {
    if (!spawnError) spawnError = error;
    try { child.stdin.destroy(error); } catch {}
  });
  promptStream.pipe(child.stdin);

  const closeResult = await new Promise((resolvePromise) => {
    child.once("close", (code, signal) => resolvePromise({ code, signal }));
  });
  clearTimeout(timeout);
  tracker.finish();
  await terminationKillPromise;
  if (killTimer) clearTimeout(killTimer);
  process.removeListener("SIGTERM", onSigterm);
  process.removeListener("SIGINT", onSigint);
  try { closeSync(eventsFd); } catch {}
  try { closeSync(stderrFd); } catch {}

  const resultHasContent = hasResultContent(paths.result);
  let reason = null;
  if (termination?.kind === "timed_out") reason = "timeout";
  else if (termination?.kind === "interrupted") reason = "interrupted";
  else if (spawnError) reason = spawnError.code === "ENOENT" ? "codex_not_found" : "spawn_error";
  else if (closeResult.code !== 0 || closeResult.signal) reason = "nonzero_exit";
  else reason = transportReason(tracker, resultHasContent, artifactWriteError);

  const final = terminalStatus(status, tracker, closeResult, termination, reason, {
    ...(spawnError ? { detail: spawnError.code || "spawn_error" } : {}),
    ...(artifactWriteError ? { detail: artifactWriteError.code || "artifact_write_failed" } : {}),
  });
  writeJsonAtomic(paths.status, final);
  return final.state === "completed" ? 0 : 1;
}

function runHealth() {
  const bin = codexBin();
  const version = spawnSync(bin, ["--version"], {
    env: process.env,
    shell: false,
    stdio: ["ignore", "pipe", "ignore"],
    encoding: "utf8",
    maxBuffer: 64 * 1024,
  });
  const login = spawnSync(bin, ["login", "status"], {
    env: process.env,
    shell: false,
    stdio: ["ignore", "ignore", "ignore"],
  });
  const versionLine = typeof version.stdout === "string" ? version.stdout.split(/\r?\n/, 1)[0].slice(0, 200) : "";
  const versionOk = version.status === 0;
  const loginOk = login.status === 0;
  process.stdout.write(`${JSON.stringify({
    ok: versionOk && loginOk,
    codex_bin: bin,
    version: versionOk ? versionLine : null,
    login: {
      ok: loginOk,
      exit_code: login.status,
      signal: login.signal,
    },
  }, null, 2)}\n`);
  return versionOk && loginOk ? 0 : 1;
}

function readStatus(runDirValue) {
  const runDir = requireAbsolute(runDirValue, "--run-dir");
  const statusPath = join(runDir, "status.json");
  let status;
  try {
    status = JSON.parse(readFileSync(statusPath, "utf8"));
  } catch {
    throw new CliError("status.json is missing or invalid");
  }
  if (status.state === "running" && !processExists(status.runner_pid)) {
    status = {
      ...status,
      state: "unknown",
      observed_state: "unknown",
      observed_at: now(),
      reason: "runner_process_not_found",
    };
  }
  process.stdout.write(`${JSON.stringify(status, null, 2)}\n`);
  return 0;
}

async function main(argv = process.argv.slice(2)) {
  try {
    const parsed = parseCli(argv);
    if (parsed.command === "help") {
      process.stdout.write(HELP);
      return 0;
    }
    if (parsed.command === "health") return runHealth();
    if (parsed.command === "status") return readStatus(parsed.runDir);
    return await execute(parsed);
  } catch (error) {
    if (error instanceof CliError) {
      process.stderr.write(`error: ${error.message}\n`);
      return 2;
    }
    process.stderr.write(`error: ${error?.message || "runner failed"}\n`);
    return 1;
  }
}

const entryUrl = process.argv[1] ? pathToFileURL(process.argv[1]).href : null;
if (entryUrl && import.meta.url === entryUrl) {
  main().then((code) => { process.exitCode = code; });
}

export { main, parseCli };
