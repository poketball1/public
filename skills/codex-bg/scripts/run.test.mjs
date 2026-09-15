import assert from "node:assert/strict";
import { once } from "node:events";
import { access, chmod, lstat, mkdtemp, mkdir, readFile, rm, stat, symlink, writeFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test, { after, before } from "node:test";

const runner = fileURLToPath(new URL("./run.mjs", import.meta.url));
let root;
let fixture;
let project;
let prompt;
let sequence = 0;

const FIXTURE = `#!/usr/bin/env node
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";

const args = process.argv.slice(2);
const mode = process.env.FAKE_CODEX_MODE || "success";
const argsFile = process.env.FAKE_CODEX_ARGS;
const outputIndex = args.indexOf("-o");
const outputPath = outputIndex >= 0 ? args[outputIndex + 1] : null;
const resumeIndex = args.indexOf("resume");
const explicitThread = resumeIndex >= 0 ? args[resumeIndex + 1] : null;
const thread = process.env.FAKE_CODEX_THREAD || explicitThread || "11111111-1111-4111-8111-111111111111";

if (argsFile) writeFileSync(argsFile, JSON.stringify({ args, cwd: process.cwd() }));
if (args[0] === "--version") {
  process.stdout.write("codex fixture 9.9.9\\n");
  process.exit(0);
}
if (args[0] === "login" && args[1] === "status") {
  process.stdout.write("fixture secret body must stay hidden\\n");
  process.exit(process.env.FAKE_HEALTH_FAIL === "1" ? 1 : 0);
}

let input = "";
for await (const chunk of process.stdin) input += chunk;
if (process.env.FAKE_CODEX_INPUT_FILE) writeFileSync(process.env.FAKE_CODEX_INPUT_FILE, input);
const emit = (event) => process.stdout.write(JSON.stringify(event) + "\\n");
const complete = () => emit({ type: "turn.completed", status: "completed" });
const writeResult = (value) => { if (outputPath && value !== undefined) writeFileSync(outputPath, value); };

if (mode === "success" || mode === "stderr" || mode === "nonzero" || mode === "resume") {
  emit({ type: "thread.started", thread_id: thread });
  emit({ type: "item.completed", item: { type: "agent_message", text: "fixture" } });
  writeResult(process.env.FAKE_RESULT || "BLOCKED_BY_TASK");
  if (mode === "stderr") process.stderr.write("fixture stderr only\\n");
  complete();
  process.exit(mode === "nonzero" ? 7 : 0);
}
if (mode === "empty_final") {
  emit({ type: "thread.started", thread_id: thread });
  writeResult("");
  complete();
  process.exit(0);
}
if (mode === "missing_final") {
  emit({ type: "thread.started", thread_id: thread });
  complete();
  process.exit(0);
}
if (mode === "missing_completed") {
  emit({ type: "thread.started", thread_id: thread });
  writeResult("non-empty final");
  process.exit(0);
}
if (mode === "turn_failed") {
  emit({ type: "thread.started", thread_id: thread });
  emit({ type: "turn.failed", error: { message: "fixture failure" } });
  writeResult("non-empty final");
  process.exit(0);
}
if (mode === "malformed") {
  process.stdout.write("{not-json\\n");
  writeResult("non-empty final");
  process.exit(0);
}
if (mode === "descendant") {
  const child = spawn(process.execPath, ["-e", "setInterval(() => {}, 1000)"], { stdio: "ignore" });
  if (process.env.FAKE_DESCENDANT_PID) writeFileSync(process.env.FAKE_DESCENDANT_PID, String(child.pid));
  setInterval(() => {}, 1000);
  await new Promise(() => {});
}
if (mode === "graceful_timeout") {
  process.on("SIGTERM", () => process.exit(0));
  setInterval(() => {}, 1000);
  await new Promise(() => {});
}
process.exit(3);
`;

function startCommand(args, env = {}) {
  const child = spawn(process.execPath, [runner, ...args], {
    cwd: root,
    env: { ...process.env, CODEX_BIN: fixture, ...env },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  const done = once(child, "close").then(([code, signal]) => ({ code, signal, stdout, stderr }));
  return { child, done };
}

async function command(args, env = {}) {
  return (await startCommand(args, env)).done;
}

async function statusOf(runDir) {
  return JSON.parse(await readFile(join(runDir, "status.json"), "utf8"));
}

async function waitForFile(path, timeoutMs = 2_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const value = await readFile(path, "utf8");
      if (value.length > 0) return value;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error(`timed out waiting for ${path}`);
}

async function waitForGone(pid, timeoutMs = 2_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      process.kill(pid, 0);
    } catch (error) {
      if (error?.code === "ESRCH") return;
    }
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error(`process ${pid} is still present`);
}

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

before(async () => {
  root = await mkdtemp(join(tmpdir(), "codex-bg-runner-"));
  project = join(root, "project ; $() with spaces");
  await mkdir(project);
  prompt = join(root, "prompt ; $HOME with spaces.md");
  await writeFile(prompt, "PROMPT_FIXTURE_CONTENT\n");
  fixture = join(root, "fake codex; executable.mjs");
  await writeFile(fixture, FIXTURE, { mode: 0o755 });
  await chmod(fixture, 0o755);
});

after(async () => {
  await rm(root, { recursive: true, force: true });
});

test("help and health are self-contained and health does not print login body", async () => {
  const help = await command(["--help"], { CODEX_BIN: "/path/that/is/not/used" });
  assert.equal(help.code, 0);
  assert.match(help.stdout, /run.*Start a new Codex exec turn/s);
  assert.match(help.stdout, /--thread UUID/);

  const health = await command(["health"], { FAKE_CODEX_MODE: "success" });
  assert.equal(health.code, 0);
  const body = JSON.parse(health.stdout);
  assert.equal(body.ok, true);
  assert.equal(body.version, "codex fixture 9.9.9");
  assert.doesNotMatch(health.stdout, /secret body/);

  const healthRejected = await command(["health", "--ignore-user-config"]);
  assert.equal(healthRejected.code, 2);
  assert.match(healthRejected.stderr, /health does not accept run options/);
  const statusRejected = await command([
    "status", "--run-dir", join(root, "not-a-run"), "--ignore-user-config",
  ]);
  assert.equal(statusRejected.code, 2);
  assert.match(statusRejected.stderr, /status accepts only --run-dir ABS/);
});

test("successful transport records thread, preserves blocked final, and isolates stderr", async () => {
  const runDir = join(root, `success-${sequence++}`);
  const argsFile = join(root, `args-${sequence++}.json`);
  const inputFile = join(root, `input-${sequence++}.txt`);
  const result = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", runDir,
  ], { FAKE_CODEX_MODE: "stderr", FAKE_CODEX_ARGS: argsFile, FAKE_CODEX_INPUT_FILE: inputFile });
  assert.equal(result.code, 0);
  const status = await statusOf(runDir);
  assert.equal(status.state, "completed");
  assert.equal(status.thread, "11111111-1111-4111-8111-111111111111");
  assert.equal(status.turn_completed, true);
  assert.equal(status.turn_failed, false);
  assert.equal(await readFile(join(runDir, "result.md"), "utf8"), "BLOCKED_BY_TASK");
  assert.equal(await readFile(join(runDir, "prompt.md"), "utf8"), "PROMPT_FIXTURE_CONTENT\n");
  assert.match(await readFile(join(runDir, "stderr.log"), "utf8"), /fixture stderr only/);
  assert.doesNotMatch(await readFile(join(runDir, "events.jsonl"), "utf8"), /fixture stderr only/);
  assert.equal(await readFile(inputFile, "utf8"), "PROMPT_FIXTURE_CONTENT\n");
  const recorded = JSON.parse(await readFile(argsFile, "utf8"));
  assert.equal(recorded.cwd, project);
  assert.equal(recorded.args.at(-1), "-");
  assert.ok(recorded.args.includes("--sandbox"));
  assert.ok(recorded.args.includes("read-only"));
  assert.equal(recorded.args.includes("--model"), false);
  assert.equal(recorded.args.includes("--ignore-user-config"), false);
  assert.ok(recorded.args.includes('-c') && recorded.args.includes('approval_policy="never"'));
});

test("run forwards explicit --ignore-user-config before output options", async () => {
  const runDir = join(root, `ignore-config-run-${sequence++}`);
  const argsFile = join(root, `ignore-config-run-args-${sequence++}.json`);
  const result = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", runDir,
    "--ignore-user-config",
  ], { FAKE_CODEX_MODE: "success", FAKE_CODEX_ARGS: argsFile });
  assert.equal(result.code, 0);
  const recorded = JSON.parse(await readFile(argsFile, "utf8"));
  const ignoreIndex = recorded.args.indexOf("--ignore-user-config");
  assert.ok(ignoreIndex > 0);
  assert.ok(ignoreIndex < recorded.args.indexOf("-o"));
  assert.equal(recorded.args.filter((arg) => arg === "--ignore-user-config").length, 1);
});

test("resume uses explicit thread and parent permission options before resume, never --last", async () => {
  const runDir = join(root, `resume-seed-${sequence++}`);
  await command(["run", "--workdir", project, "--prompt-file", prompt, "--run-dir", runDir]);
  const seed = await statusOf(runDir);
  const resumeDir = join(root, `resume-${sequence++}`);
  const argsFile = join(root, `resume-args-${sequence++}.json`);
  const result = await command([
    "resume", "--workdir", project, "--prompt-file", prompt, "--run-dir", resumeDir,
    "--sandbox", "workspace-write", "--model", "model/explicit", "--ignore-user-config",
    "--thread", seed.thread,
  ], { FAKE_CODEX_MODE: "resume", FAKE_CODEX_ARGS: argsFile });
  assert.equal(result.code, 0);
  const recorded = JSON.parse(await readFile(argsFile, "utf8"));
  const resumeIndex = recorded.args.indexOf("resume");
  assert.ok(resumeIndex > 0);
  assert.deepEqual(recorded.args.slice(resumeIndex, resumeIndex + 3), ["resume", seed.thread, "-o"]);
  assert.equal(recorded.args.includes("--last"), false);
  assert.ok(recorded.args.indexOf("--cd") < resumeIndex);
  assert.ok(recorded.args.indexOf("--sandbox") < resumeIndex);
  assert.ok(recorded.args.indexOf("-c") < resumeIndex);
  assert.ok(recorded.args.indexOf("--model") < resumeIndex);
  assert.ok(recorded.args.indexOf("--ignore-user-config") < resumeIndex);
  assert.equal(recorded.args.filter((arg) => arg === "--ignore-user-config").length, 1);
  assert.equal((await statusOf(resumeDir)).state, "completed");
});

test("nonzero, missing final, missing completion, failed turn, and malformed stdout preserve evidence", async () => {
  const cases = [
    ["nonzero", "nonzero_exit"],
    ["empty_final", "empty_result"],
    ["missing_final", "empty_result"],
    ["missing_completed", "missing_turn_completed"],
    ["turn_failed", "turn_failed"],
    ["malformed", "malformed_stdout_json"],
  ];
  for (const [mode, reason] of cases) {
    const runDir = join(root, `${mode}-${sequence++}`);
    const result = await command([
      "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", runDir,
    ], { FAKE_CODEX_MODE: mode });
    assert.equal(result.code, 1, mode);
    const status = await statusOf(runDir);
    assert.equal(status.state, "failed", mode);
    assert.equal(status.reason, reason, mode);
    assert.ok((await stat(join(runDir, "events.jsonl"))).isFile());
    assert.ok((await stat(join(runDir, "stderr.log"))).isFile());
    assert.ok((await stat(join(runDir, "result.md"))).isFile());
    assert.ok((await stat(join(runDir, "prompt.md"))).isFile());
  }
});

test("missing Codex binary leaves all artifacts and status", async () => {
  const runDir = join(root, `missing-bin-${sequence++}`);
  const result = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", runDir,
  ], { CODEX_BIN: join(root, "missing codex binary") });
  assert.equal(result.code, 1);
  const status = await statusOf(runDir);
  assert.equal(status.state, "failed");
  assert.equal(status.reason, "codex_not_found");
  for (const name of ["prompt.md", "result.md", "events.jsonl", "stderr.log", "status.json"]) {
    assert.ok((await stat(join(runDir, name))).isFile(), name);
  }
});

test("absolute paths with spaces and shell metacharacters are passed literally", async () => {
  const runDir = join(root, `run ; $(touch SHOULD_NOT_EXIST) ${sequence++}`);
  const argsFile = join(root, `literal args ${sequence++}.json`);
  const result = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", runDir,
  ], { FAKE_CODEX_ARGS: argsFile });
  assert.equal(result.code, 0);
  const recorded = JSON.parse(await readFile(argsFile, "utf8"));
  assert.equal(recorded.cwd, project);
  assert.equal(recorded.args[recorded.args.indexOf("--cd") + 1], project);
  assert.equal(recorded.args[recorded.args.indexOf("-o") + 1], join(runDir, "result.md"));
  assert.equal(await pathExists(join(root, "SHOULD_NOT_EXIST")), false);
});

test("run-dir creation is exclusive, mode 700, and retains existing files; separate invocations stay separate", async () => {
  const existing = join(root, `existing-${sequence++}`);
  await mkdir(existing, { mode: 0o700 });
  const sentinel = join(existing, "sentinel.txt");
  await writeFile(sentinel, "keep");
  const rejected = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", existing,
  ]);
  assert.equal(rejected.code, 2);
  assert.equal(await readFile(sentinel, "utf8"), "keep");
  const linkTarget = join(root, `symlink-target-${sequence++}`);
  await mkdir(linkTarget, { mode: 0o700 });
  const link = join(root, `existing-link-${sequence++}`);
  await symlink(linkTarget, link);
  const linkRejected = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", link,
  ]);
  assert.equal(linkRejected.code, 2);
  assert.equal((await lstat(link)).isSymbolicLink(), true);
  const first = join(root, `separate-a-${sequence++}`);
  const second = join(root, `separate-b-${sequence++}`);
  assert.equal((await command(["run", "--workdir", project, "--prompt-file", prompt, "--run-dir", first])).code, 0);
  assert.equal((await command(["run", "--workdir", project, "--prompt-file", prompt, "--run-dir", second])).code, 0);
  assert.notDeepEqual(await statusOf(first), await statusOf(second));
  const mode = (await stat(first)).mode & 0o777;
  assert.equal(mode, 0o700);
});

test("SIGINT and timeout terminate the child process group and record evidence", async () => {
  const interruptedDir = join(root, `interrupted-${sequence++}`);
  const interruptedPid = join(root, `interrupted-pid-${sequence++}`);
  const interrupted = startCommand([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", interruptedDir,
  ], { FAKE_CODEX_MODE: "descendant", FAKE_DESCENDANT_PID: interruptedPid });
  await waitForFile(interruptedPid);
  const firstPid = Number.parseInt(await waitForFile(interruptedPid), 10);
  assert.ok(firstPid > 0);
  interrupted.child.kill("SIGINT");
  const interruptedResult = await interrupted.done;
  assert.notEqual(interruptedResult.code, 0);
  const interruptedStatus = await statusOf(interruptedDir);
  assert.equal(interruptedStatus.state, "interrupted");
  assert.equal(interruptedStatus.reason, "interrupted");
  await waitForGone(firstPid);
  const timeoutDir = join(root, `timeout-${sequence++}`);
  const timeoutPid = join(root, `timeout-pid-${sequence++}`);
  const timeout = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", timeoutDir,
    "--timeout-seconds", "1",
  ], { FAKE_CODEX_MODE: "descendant", FAKE_DESCENDANT_PID: timeoutPid });
  assert.equal(timeout.code, 1);
  assert.equal((await statusOf(timeoutDir)).state, "timed_out");
  const descendantPid = Number.parseInt(await waitForFile(timeoutPid), 10);
  await waitForGone(descendantPid);
});

test("timed-out child exit code stays separate from group cleanup signal", async () => {
  const runDir = join(root, `graceful-timeout-${sequence++}`);
  const result = await command([
    "run", "--workdir", project, "--prompt-file", prompt, "--run-dir", runDir,
    "--timeout-seconds", "1",
  ], { FAKE_CODEX_MODE: "graceful_timeout" });
  assert.equal(result.code, 1);
  const status = await statusOf(runDir);
  assert.equal(status.state, "timed_out");
  assert.equal(status.exit_code, 0);
  assert.equal(status.signal, null);
  assert.equal(status.termination.kind, "timed_out");
  assert.equal(status.termination.term_signal, "SIGTERM");
  assert.equal(status.termination.kill_signal, "SIGKILL");
});

test("status reports unknown for a recorded running runner that is gone", async () => {
  const runDir = join(root, `dead-status-${sequence++}`);
  await mkdir(runDir, { mode: 0o700 });
  await writeFile(join(runDir, "status.json"), JSON.stringify({
    schema: "codex-bg-runner.v1",
    state: "running",
    runner_pid: 4_000_000,
    thread: "11111111-1111-4111-8111-111111111111",
    paths: { run_dir: runDir },
  }));
  const result = await command(["status", "--run-dir", runDir]);
  assert.equal(result.code, 0);
  const observed = JSON.parse(result.stdout);
  assert.equal(observed.state, "unknown");
  assert.equal(observed.reason, "runner_process_not_found");
});
