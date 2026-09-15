import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const TEST_FILE = fileURLToPath(import.meta.url);
const REPO_ROOT = path.resolve(path.dirname(TEST_FILE), "..");

function shellQuote(value) {
  return "'" + value.replaceAll("'", "'\\''") + "'";
}

function writeExecutable(file, body) {
  fs.writeFileSync(file, body, { mode: 0o755 });
  fs.chmodSync(file, 0o755);
}

function copyFixture(t, label) {
  const outer = fs.mkdtempSync(path.join(os.tmpdir(), "public-installer-" + label + "-"));
  const root = path.join(outer, 'source #$ "quoted"');
  fs.mkdirSync(root, { recursive: true });
  for (const entry of ["install.sh", "skills", "bridge"]) {
    fs.cpSync(path.join(REPO_ROOT, entry), path.join(root, entry), { recursive: true });
  }
  t.after(() => fs.rmSync(outer, { recursive: true, force: true }));
  return { outer, root };
}

let tomllibPython;

function resolveExecutable(candidate) {
  if (path.isAbsolute(candidate)) return candidate;
  for (const directory of (process.env.PATH || "").split(path.delimiter)) {
    const resolved = path.join(directory || ".", candidate);
    try {
      fs.accessSync(resolved, fs.constants.X_OK);
      return resolved;
    } catch {
      // Try the next PATH entry.
    }
  }
  return candidate;
}

function findTomllibPython() {
  if (tomllibPython) return tomllibPython;
  const candidates = [
    process.env.PYTHON3,
    process.env.PYTHON,
    "python3.14",
    "python3.13",
    "python3.12",
    "python3.11",
    "python3",
  ].filter(Boolean);
  for (const candidate of candidates) {
    const resolved = resolveExecutable(candidate);
    const probe = spawnSync(
      resolved,
      ["-c", "import tomllib; print('ok')"],
      { encoding: "utf8" },
    );
    if (probe.status === 0 && probe.stdout.trim() === "ok") {
      tomllibPython = resolved;
      return resolved;
    }
  }
  throw new Error("Python 3.11+ with stdlib tomllib is required for installer tests");
}

function makeBins(outer, { claude = false, nodeDelay = 0, pythonDelay = 0 } = {}) {
  const bin = path.join(outer, 'bin #$ "quoted"');
  fs.mkdirSync(bin, { recursive: true });
  writeExecutable(
    path.join(bin, "node"),
    "#!/bin/sh\n" +
      (nodeDelay ? "sleep " + shellQuote(String(nodeDelay)) + "\n" : "") +
      "exec " + shellQuote(process.execPath) + ' "$@"\n',
  );
  writeExecutable(path.join(bin, "codex"), "#!/bin/sh\nexit 0\n");
  if (claude) {
    writeExecutable(path.join(bin, "claude"), "#!/bin/sh\nexit 0\n");
  }
  const python = findTomllibPython();
  writeExecutable(
    path.join(bin, "python3"),
    "#!/bin/sh\n" +
      (pythonDelay ? "sleep " + shellQuote(String(pythonDelay)) + "\n" : "") +
      "exec " + shellQuote(python) + ' "$@"\n',
  );
  return {
    bin,
    python: path.join(bin, "python3"),
    path: bin + ":/usr/bin:/bin",
  };
}

function prepare(t, label, options = {}) {
  const fixture = copyFixture(t, label);
  const project = path.join(fixture.outer, 'project with #$ "quotes" [x]');
  const home = path.join(fixture.outer, "home");
  const config = path.join(fixture.outer, 'config #$ "quoted"', "config.toml");
  const runtime = path.join(fixture.outer, "runtime");
  fs.mkdirSync(project, { recursive: true });
  fs.mkdirSync(home, { recursive: true });
  fs.mkdirSync(runtime, { recursive: true });
  const bins = makeBins(fixture.outer, options);
  return { ...fixture, project, home, config, runtime, bins };
}

function runInstaller(fixture, args, options = {}) {
  const env = {
    ...process.env,
    HOME: options.home,
    PATH: options.bins.path,
    XDG_RUNTIME_DIR: options.runtime || fixture.runtime,
  };
  delete env.CODEX_HOME;
  if (options.env) Object.assign(env, options.env);
  return spawnSync(
    "bash",
    [path.join(fixture.root, "install.sh"), ...args],
    { cwd: fixture.root, env, encoding: "utf8" },
  );
}

function spawnInstaller(fixture, args, options = {}) {
  const env = {
    ...process.env,
    HOME: options.home,
    PATH: options.bins.path,
    XDG_RUNTIME_DIR: options.runtime || fixture.runtime,
  };
  delete env.CODEX_HOME;
  if (options.env) Object.assign(env, options.env);
  const child = spawn(
    "bash",
    [path.join(fixture.root, "install.sh"), ...args],
    { cwd: fixture.root, env },
  );
  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  return new Promise((resolve) => {
    child.on("close", (status, signal) => resolve({ status, signal, stdout, stderr }));
  });
}

function runOnly(fixture, options, extra = []) {
  return runInstaller(
    fixture,
    [
      "--project", options.project,
      "--codex-config", options.config,
      "--only", "codex-bg",
      ...extra,
    ],
    options,
  );
}

function runBoth(fixture, options, extra = []) {
  return runInstaller(
    fixture,
    ["--project", options.project, "--codex-config", options.config, ...extra],
    options,
  );
}

function resultText(result) {
  return "status=" + result.status + "\nstdout:\n" + result.stdout + "\nstderr:\n" + result.stderr;
}

function read(file) {
  return fs.readFileSync(file, "utf8");
}

function listFiles(directory) {
  if (!fs.existsSync(directory)) return [];
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...listFiles(full));
    else files.push(full);
  }
  return files;
}

function tomlEscape(value) {
  return value.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

function skillDestination(options) {
  return path.join(options.project, ".claude", "skills", "codex-bg");
}

function coordinationDirectory() {
  return path.join("/tmp", "claude-codex-install-" + process.getuid());
}

function uniqueTmpFile(prefix, contents) {
  const file = path.join(
    "/tmp",
    prefix + process.pid + "-" + Date.now() + "-" + Math.random().toString(16).slice(2) + ".toml",
  );
  fs.writeFileSync(file, contents, { flag: "wx" });
  return file;
}

function parseToml(file, options) {
  const result = spawnSync(
    options.bins.python,
    [
      "-c",
      "import pathlib,sys,tomllib; tomllib.loads(pathlib.Path(sys.argv[1]).read_bytes().decode('utf-8'))",
      file,
    ],
    { env: { ...process.env, PATH: options.bins.path }, encoding: "utf8" },
  );
  assert.equal(result.status, 0, resultText(result));
}

test("only mode installs the full runtime, excludes tests, preserves unrelated files, and is repeat-safe", (t) => {
  const options = prepare(t, "only-upgrade");
  const sourceSkill = path.join(options.root, "skills", "codex-bg", "SKILL.md");
  const sourceRun = path.join(options.root, "skills", "codex-bg", "scripts", "run.mjs");
  assert.ok(fs.existsSync(sourceRun), "runtime entry is required by the installer contract");

  const destination = skillDestination(options);
  fs.mkdirSync(path.join(destination, "scripts"), { recursive: true });
  fs.writeFileSync(path.join(destination, "SKILL.md"), "user's previous managed copy\n");
  fs.writeFileSync(path.join(destination, "user-unrelated.txt"), "keep this file\n");
  fs.writeFileSync(path.join(destination, "scripts", "user-unrelated.mjs"), "keep this runtime neighbor\n");
  const configBefore = "user-config = true\n";
  fs.mkdirSync(path.dirname(options.config), { recursive: true });
  fs.writeFileSync(options.config, configBefore);

  let result = runOnly(options, options);
  assert.equal(result.status, 0, resultText(result));
  assert.equal(read(path.join(destination, "SKILL.md")), read(sourceSkill));
  assert.equal(read(path.join(destination, "scripts", "run.mjs")), read(sourceRun));
  assert.equal(read(path.join(destination, "user-unrelated.txt")), "keep this file\n");
  assert.equal(read(path.join(destination, "scripts", "user-unrelated.mjs")), "keep this runtime neighbor\n");
  assert.equal(read(options.config), configBefore);
  assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
  assert.deepEqual(
    listFiles(destination).filter((file) => /\.(test|spec)\./.test(path.basename(file))),
    [],
  );

  let backups = fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak."));
  assert.equal(backups.length, 1);
  const firstBackup = backups[0];
  assert.equal(read(path.join(destination, firstBackup)), "user's previous managed copy\n");

  fs.writeFileSync(sourceSkill, read(sourceSkill) + "\nupdate-one\n");
  result = runOnly(options, options);
  assert.equal(result.status, 0, resultText(result));
  backups = fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")).sort();
  assert.equal(backups.length, 2);
  assert.equal(read(path.join(destination, firstBackup)), "user's previous managed copy\n");

  result = runOnly(options, options);
  assert.equal(result.status, 0, resultText(result));
  assert.equal(
    fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")).length,
    2,
  );
});

test("only dry-run does not create destination, state, backup, or config paths", (t) => {
  const options = prepare(t, "dry-run");
  const destination = skillDestination(options);
  const configParent = path.dirname(options.config);
  const lockDir = coordinationDirectory();
  const lockDirBefore = fs.existsSync(lockDir);
  const lockEntriesBefore = lockDirBefore ? fs.readdirSync(lockDir).sort() : [];

  const result = runOnly(options, options, ["--dry-run"]);
  assert.equal(result.status, 0, resultText(result));
  assert.match(result.stdout, /Codex MCP config remains unchanged/);
  assert.equal(fs.existsSync(path.join(options.project, ".claude")), false);
  assert.equal(fs.existsSync(configParent), false);
  assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
  assert.equal(fs.existsSync(lockDir), lockDirBefore);
  if (lockDirBefore) assert.deepEqual(fs.readdirSync(lockDir).sort(), lockEntriesBefore);
});

test("only mode leaves an existing Codex MCP config byte-identical and does not need claude", (t) => {
  const options = prepare(t, "only-config");
  fs.unlinkSync(options.bins.python);
  const before = "[mcp_servers.other]\ncommand = \"keep\"\n";
  fs.mkdirSync(path.dirname(options.config), { recursive: true });
  fs.writeFileSync(options.config, before);

  const result = runOnly(options, options);
  assert.equal(result.status, 0, resultText(result));
  assert.equal(read(options.config), before);
  assert.equal(fs.existsSync(path.join(options.home, ".local", "state")), false);
});

test("only mode accepts a unique /tmp config with CODEX_HOME=/tmp in dry-run and write modes", (t) => {
  const options = prepare(t, "only-tmp-config");
  const config = uniqueTmpFile("public-installer-only-", "existing = true\n");
  t.after(() => fs.rmSync(config, { force: true }));
  fs.unlinkSync(options.bins.python);
  const onlyOptions = { ...options, config, env: { CODEX_HOME: "/tmp" } };
  const before = read(config);

  let result = runOnly(options, onlyOptions, ["--dry-run"]);
  assert.equal(result.status, 0, resultText(result));
  assert.equal(read(config), before);
  assert.equal(fs.existsSync(path.join(options.project, ".claude")), false);

  result = runOnly(options, onlyOptions);
  assert.equal(result.status, 0, resultText(result));
  assert.equal(read(config), before);
  assert.equal(fs.existsSync(path.join(options.project, ".claude", "skills", "codex-bg", "SKILL.md")), true);
});

test("BOTH mode accepts a unique config directly under /tmp and writes valid TOML", (t) => {
  const options = prepare(t, "both-tmp-config", { claude: true });
  const config = uniqueTmpFile("public-installer-both-", "existing = true\n");
  t.after(() => {
    fs.rmSync(config, { force: true });
    for (const entry of fs.readdirSync("/tmp")) {
      if (entry.startsWith(path.basename(config) + ".bak.")) fs.rmSync(path.join("/tmp", entry), { force: true });
    }
  });
  const bothOptions = { ...options, config };

  const result = runBoth(options, bothOptions);
  assert.equal(result.status, 0, resultText(result));
  parseToml(config, bothOptions);
  assert.match(read(config), /\[mcp_servers\.claude-coder\]/);
  assert.equal(fs.existsSync(path.join(options.project, ".claude", "skills", "codex-bg", "SKILL.md")), true);
});

test("only mode ignores missing reverse bridge sources", (t) => {
  const options = prepare(t, "only-no-bridge");
  fs.rmSync(path.join(options.root, "bridge"), { recursive: true, force: true });

  const result = runOnly(options, options);
  assert.equal(result.status, 0, resultText(result));
  assert.equal(result.stderr, "");
  assert.equal(read(path.join(options.project, ".claude", "skills", "codex-bg", "SKILL.md")),
    read(path.join(options.root, "skills", "codex-bg", "SKILL.md")));
  assert.equal(read(path.join(options.project, ".claude", "skills", "codex-bg", "scripts", "run.mjs")),
    read(path.join(options.root, "skills", "codex-bg", "scripts", "run.mjs")));
});

test("BOTH mode rejects config paths overlapping skill runtime directories before writes", (t) => {
  const cases = ["skill-file", "runner", "scripts-dir"];
  for (const kind of cases) {
    const options = prepare(t, "target-overlap-" + kind, { claude: true });
    const destination = skillDestination(options);
    fs.mkdirSync(destination, { recursive: true });
    let config;
    const configBefore = "existing = true\n";
    if (kind === "skill-file") {
      config = path.join(destination, "SKILL.md");
      fs.writeFileSync(config, configBefore);
    } else if (kind === "runner") {
      config = path.join(destination, "scripts", "run.mjs");
      fs.mkdirSync(path.dirname(config), { recursive: true });
      fs.writeFileSync(config, configBefore);
    } else {
      config = path.join(destination, "scripts");
    }
    const destinationBefore = listFiles(destination)
      .sort()
      .map((file) => [file, read(file)]);
    const lockDir = coordinationDirectory();
    const lockEntriesBefore = fs.existsSync(lockDir) ? fs.readdirSync(lockDir).sort() : null;

    const result = runBoth(options, { ...options, config });
    assert.equal(result.status, 73, resultText(result));
    assert.match(result.stderr, /overlaps installer-owned runtime directory/);
    assert.deepEqual(
      listFiles(destination).sort().map((file) => [file, read(file)]),
      destinationBefore,
    );
    assert.equal(fs.existsSync(config), kind !== "scripts-dir");
    if (kind !== "scripts-dir") assert.equal(read(config), configBefore);
    assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
    if (lockEntriesBefore === null) {
      assert.equal(fs.existsSync(lockDir), false);
    } else {
      assert.deepEqual(fs.readdirSync(lockDir).sort(), lockEntriesBefore);
    }
  }
});

test("BOTH mode rejects config under an unlisted state audit path before writes", (t) => {
  const options = prepare(t, "state-audit-overlap", { claude: true });
  const destination = skillDestination(options);
  fs.mkdirSync(destination, { recursive: true });
  const oldSkill = "preserve this managed copy\n";
  fs.writeFileSync(path.join(destination, "SKILL.md"), oldSkill);
  const config = path.join(
    options.home,
    ".local",
    "state",
    "claude-codex-bridge",
    "future-rotation-audit.jsonl",
  );
  const destinationBefore = listFiles(destination).sort().map((file) => [file, read(file)]);
  const result = runBoth(options, { ...options, config });

  assert.equal(result.status, 73, resultText(result));
  assert.match(result.stderr, /overlaps installer-owned runtime directory/);
  assert.deepEqual(
    listFiles(destination).sort().map((file) => [file, read(file)]),
    destinationBefore,
  );
  assert.equal(fs.existsSync(config), false);
  assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
});

test("default mode detects direct, quoted, child, and array claude-coder tables before any write", (t) => {
  const forms = [
    '[mcp_servers."claude-coder"] # inline comment',
    "[mcp_servers.'claude-coder'] # literal quoted key",
    '[mcp_servers.claude-coder.env] # child table',
    '["mcp_servers"."claude-coder".env] # quoted child table',
    '[[mcp_servers."claude-coder"]] # array table',
  ];

  for (let index = 0; index < forms.length; index += 1) {
    const options = prepare(t, "duplicate-" + index, { claude: true });
    const destination = skillDestination(options);
    fs.mkdirSync(destination, { recursive: true });
    const oldSkill = "must remain untouched\n";
    fs.writeFileSync(path.join(destination, "SKILL.md"), oldSkill);
    const configBefore = forms[index] + "\nexisting = true\n";
    fs.mkdirSync(path.dirname(options.config), { recursive: true });
    fs.writeFileSync(options.config, configBefore);

    const result = runBoth(options, options);
    assert.equal(result.status, 73, resultText(result));
    assert.match(result.stderr, /--only codex-bg/);
    assert.equal(read(path.join(destination, "SKILL.md")), oldSkill);
    assert.deepEqual(
      fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")),
      [],
    );
    assert.equal(read(options.config), configBefore);
    assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
  }
});

test("default mode escapes special paths while keeping permission defaults unchanged", (t) => {
  const options = prepare(t, "special-paths", { claude: true });
  const result = runBoth(options, options);
  assert.equal(result.status, 0, resultText(result));

  const config = read(options.config);
  const wrapper = path.join(options.root, "bridge", "claude-coder-mcp", "run.sh");
  const node = path.join(options.bins.bin, "node");
  const claude = path.join(options.bins.bin, "claude");
  assert.ok(config.includes('command = "' + tomlEscape(wrapper) + '"'));
  assert.ok(config.includes('NODE_BIN = "' + tomlEscape(node) + '"'));
  assert.ok(config.includes('CLAUDE_BIN = "' + tomlEscape(claude) + '"'));
  assert.ok(config.includes('CLAUDE_MCP_WORKDIR = "' + tomlEscape(options.project) + '"'));
  assert.ok(config.includes('CLAUDE_MCP_DEFAULT_PERMISSION_MODE = "default"'));
  assert.ok(config.includes('CLAUDE_MCP_DEFAULT_WRITE_PERMISSION_MODE = "acceptEdits"'));
  assert.equal(fs.statSync(options.config).mode & 0o777, 0o600);
});

test("default config follows CODEX_HOME without changing the parent process environment", (t) => {
  const options = prepare(t, "codex-home", { claude: true });
  const codexHome = path.join(options.outer, "codex-home #$");
  const parentCodexHome = process.env.CODEX_HOME;
  const result = runInstaller(
    options,
    ["--project", options.project],
    { home: options.home, bins: options.bins, env: { CODEX_HOME: codexHome } },
  );
  assert.equal(result.status, 0, resultText(result));
  assert.ok(fs.existsSync(path.join(codexHome, "config.toml")));
  assert.equal(fs.existsSync(path.join(options.home, ".codex", "config.toml")), false);
  assert.equal(process.env.CODEX_HOME, parentCodexHome);
});

test("missing option values fail clearly before creating a target", (t) => {
  const options = prepare(t, "bad-input");
  const result = runInstaller(
    options,
    ["--project", options.project, "--only"],
    options,
  );
  assert.equal(result.status, 64, resultText(result));
  assert.match(result.stderr, /--only requires a value/);
  assert.equal(fs.existsSync(path.join(options.project, ".claude")), false);
  assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
});

test("invalid skill source syntax fails before any target write", (t) => {
  const options = prepare(t, "bad-source");
  const sourceRun = path.join(options.root, "skills", "codex-bg", "scripts", "run.mjs");
  fs.writeFileSync(sourceRun, "export const = ;\n");

  const result = runOnly(options, options);
  assert.notEqual(result.status, 0, resultText(result));
  assert.match(result.stderr, /source syntax check failed|SyntaxError/);
  assert.equal(fs.existsSync(path.join(options.project, ".claude")), false);
  assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
});

test("TOML control characters in a project path are rejected before writes", (t) => {
  const options = prepare(t, "control-path", { claude: true });
  const projectWithTab = path.join(options.outer, "project\twith-tab");
  fs.mkdirSync(projectWithTab, { recursive: true });
  const result = runBoth(
    options,
    { ...options, project: projectWithTab, bins: options.bins },
  );
  assert.equal(result.status, 64, resultText(result));
  assert.match(result.stderr, /newline, carriage return, or tab/);
  assert.equal(fs.existsSync(path.join(projectWithTab, ".claude")), false);
  assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
  assert.equal(fs.existsSync(options.config), false);
});

test("default mode parses every claude-coder assignment form before any skill write", (t) => {
  const forms = [
    'mcp_servers = { "claude-coder" = { command = "existing" } }\n',
    'mcp_servers.claude-coder.command = "existing"\n',
    '[mcp_servers]\nclaude-coder = { command = "existing" }\n',
    'mcp_servers."claude\\u002dcoder".command = "existing"\n',
  ];

  for (let index = 0; index < forms.length; index += 1) {
    const options = prepare(t, "toml-duplicate-form-" + index, { claude: true });
    const destination = skillDestination(options);
    fs.mkdirSync(destination, { recursive: true });
    const oldSkill = "preserve this managed copy\n";
    fs.writeFileSync(path.join(destination, "SKILL.md"), oldSkill);
    const configBefore = forms[index] + "existing = true\n";
    fs.mkdirSync(path.dirname(options.config), { recursive: true });
    fs.writeFileSync(options.config, configBefore);

    const result = runBoth(options, options);
    assert.equal(result.status, 73, resultText(result));
    assert.match(result.stderr, /existing claude-coder MCP config found/);
    assert.equal(read(path.join(destination, "SKILL.md")), oldSkill);
    assert.deepEqual(
      fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")),
      [],
    );
    assert.equal(read(options.config), configBefore);
  }
});

test("default mode rejects invalid or non-extendable TOML before skill writes", (t) => {
  const cases = [
    {
      name: "invalid",
      config: "[mcp_servers\n",
      status: 65,
      message: /existing Codex config is invalid TOML/,
    },
    {
      name: "inline-root",
      config: 'mcp_servers = { other = { command = "keep" } }\n',
      status: 65,
      message: /cannot be extended with claude-coder MCP settings/,
    },
  ];

  for (const testCase of cases) {
    const options = prepare(t, "toml-reject-" + testCase.name, { claude: true });
    const destination = skillDestination(options);
    fs.mkdirSync(destination, { recursive: true });
    const oldSkill = "must remain byte-identical\n";
    fs.writeFileSync(path.join(destination, "SKILL.md"), oldSkill);
    fs.mkdirSync(path.dirname(options.config), { recursive: true });
    fs.writeFileSync(options.config, testCase.config);

    const result = runBoth(options, options);
    assert.equal(result.status, testCase.status, resultText(result));
    assert.match(result.stderr, testCase.message);
    assert.equal(read(path.join(destination, "SKILL.md")), oldSkill);
    assert.deepEqual(
      fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")),
      [],
    );
    assert.equal(read(options.config), testCase.config);
  }
});

test("skill target symlinks are rejected without touching outside bytes", (t) => {
  const cases = ["root", "scripts", "file"];
  for (const kind of cases) {
    const options = prepare(t, "symlink-" + kind);
    const destination = skillDestination(options);
    const outside = path.join(options.outer, "outside-" + kind);
    const outsideSkill = kind === "root" ? path.join(outside, "SKILL.md") : outside;
    fs.mkdirSync(kind === "root" ? outside : path.dirname(outside), { recursive: true });
    if (kind === "root") {
      fs.writeFileSync(outsideSkill, "outside root skill\n");
      fs.writeFileSync(path.join(outside, "run.mjs"), "outside root runtime\n");
      fs.mkdirSync(path.dirname(destination), { recursive: true });
      fs.symlinkSync(outside, destination, "dir");
    } else if (kind === "scripts") {
      fs.mkdirSync(outside, { recursive: true });
      fs.writeFileSync(path.join(outside, "run.mjs"), "outside scripts runtime\n");
      fs.mkdirSync(destination, { recursive: true });
      fs.symlinkSync(outside, path.join(destination, "scripts"), "dir");
    } else {
      fs.writeFileSync(outside, "outside skill file\n");
      fs.mkdirSync(destination, { recursive: true });
      fs.symlinkSync(outside, path.join(destination, "SKILL.md"), "file");
    }
    const outsideFiles = kind === "file" ? [outside] : listFiles(outside);
    const outsideBefore = outsideFiles.map((file) => [file, read(file)]);

    const result = runOnly(options, options);
    assert.equal(result.status, 73, resultText(result));
    assert.match(result.stderr, /symbolic link/);
    for (const [file, contents] of outsideBefore) assert.equal(read(file), contents);
    assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
    assert.equal(fs.existsSync(options.config), false);
  }
});

test("Codex config ancestor symlinks are rejected without touching outside bytes", (t) => {
  const options = prepare(t, "config-parent-symlink", { claude: true });
  const destination = skillDestination(options);
  fs.mkdirSync(destination, { recursive: true });
  const oldSkill = "preserve this managed copy\n";
  fs.writeFileSync(path.join(destination, "SKILL.md"), oldSkill);

  const outsideConfigDir = path.join(options.outer, "outside-config");
  const outsideConfig = path.join(outsideConfigDir, "config.toml");
  fs.mkdirSync(outsideConfigDir, { recursive: true });
  const configBefore = "existing = true\n";
  fs.writeFileSync(outsideConfig, configBefore);
  const linkedConfigDir = path.join(options.outer, "config-link");
  fs.symlinkSync(outsideConfigDir, linkedConfigDir, "dir");
  const linkedConfig = path.join(linkedConfigDir, "config.toml");

  const result = runBoth(options, { ...options, config: linkedConfig });
  assert.equal(result.status, 73, resultText(result));
  assert.match(result.stderr, /symbolic link/);
  assert.equal(read(outsideConfig), configBefore);
  assert.equal(read(path.join(destination, "SKILL.md")), oldSkill);
  assert.deepEqual(
    fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")),
    [],
  );
  assert.equal(fs.existsSync(path.join(options.home, ".local")), false);
});

test("BOTH mode rejects state directory leaf and ancestor symlinks without touching outside state", (t) => {
  const cases = ["leaf", "ancestor"];
  for (const kind of cases) {
    const options = prepare(t, "state-symlink-" + kind, { claude: true });
    const destination = skillDestination(options);
    fs.mkdirSync(destination, { recursive: true });
    const oldSkill = "preserve this managed copy\n";
    fs.writeFileSync(path.join(destination, "SKILL.md"), oldSkill);

    const outside = path.join(options.outer, "outside-state-" + kind);
    const sentinel = path.join(outside, "sentinel.txt");
    fs.mkdirSync(outside, { recursive: true, mode: 0o755 });
    fs.chmodSync(outside, 0o755);
    fs.writeFileSync(sentinel, "outside state sentinel\n");
    const stateDir = path.join(options.home, ".local", "state", "claude-codex-bridge");
    if (kind === "leaf") {
      fs.mkdirSync(path.dirname(stateDir), { recursive: true });
      fs.symlinkSync(outside, stateDir, "dir");
    } else {
      fs.symlinkSync(outside, path.join(options.home, ".local"), "dir");
    }
    const outsideMode = fs.statSync(outside).mode & 0o777;
    const outsideSentinel = read(sentinel);

    const result = runBoth(options, options);
    assert.equal(result.status, 73, resultText(result));
    assert.match(result.stderr, /symbolic link/);
    assert.equal(read(sentinel), outsideSentinel);
    assert.equal(fs.statSync(outside).mode & 0o777, outsideMode);
    assert.equal(read(path.join(destination, "SKILL.md")), oldSkill);
    assert.deepEqual(
      fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")),
      [],
    );
    assert.equal(fs.existsSync(options.config), false);
  }
});

test("concurrent default installers serialize config validation and append one MCP table", async (t) => {
  const options = prepare(t, "concurrent-both", { claude: true, pythonDelay: 0.2 });
  fs.mkdirSync(path.dirname(options.config), { recursive: true });
  fs.writeFileSync(options.config, "existing = true\n");
  const args = ["--project", options.project, "--codex-config", options.config];
  const [first, second] = await Promise.all([
    spawnInstaller(options, args, options),
    spawnInstaller(options, args, options),
  ]);
  const results = [first, second];
  assert.deepEqual(results.map((result) => result.status).sort((a, b) => a - b), [0, 73],
    results.map(resultText).join("\n---\n"));
  const config = read(options.config);
  assert.equal((config.match(/\[mcp_servers\.claude-coder\]/g) || []).length, 1);
  parseToml(options.config, options);
  assert.equal(fs.existsSync(path.join(options.project, ".claude", "skills", "codex-bg", "SKILL.md")), true);
});

test("concurrent default installers share the fixed lock across XDG runtime directories", async (t) => {
  const options = prepare(t, "concurrent-cross-xdg", { claude: true, pythonDelay: 0.2 });
  const otherRuntime = path.join(options.outer, "other-runtime");
  fs.mkdirSync(otherRuntime, { recursive: true });
  fs.mkdirSync(path.dirname(options.config), { recursive: true });
  fs.writeFileSync(options.config, "existing = true\n");
  const args = ["--project", options.project, "--codex-config", options.config];
  const [first, second] = await Promise.all([
    spawnInstaller(options, args, { ...options, runtime: options.runtime }),
    spawnInstaller(options, args, { ...options, runtime: otherRuntime }),
  ]);
  const results = [first, second];
  assert.deepEqual(results.map((result) => result.status).sort((a, b) => a - b), [0, 73],
    results.map(resultText).join("\n---\n"));
  const config = read(options.config);
  assert.equal((config.match(/\[mcp_servers\.claude-coder\]/g) || []).length, 1);
  parseToml(options.config, options);
});

test("concurrent only installers preserve one backup and unrelated files", async (t) => {
  const options = prepare(t, "concurrent-only", { nodeDelay: 0.2 });
  const destination = skillDestination(options);
  fs.mkdirSync(destination, { recursive: true });
  fs.writeFileSync(path.join(destination, "SKILL.md"), "old managed skill\n");
  fs.writeFileSync(path.join(destination, "unrelated.txt"), "keep this\n");
  const configBefore = "mcp_servers = { other = { command = \"keep\" } }\n";
  fs.mkdirSync(path.dirname(options.config), { recursive: true });
  fs.writeFileSync(options.config, configBefore);
  const args = [
    "--project", options.project,
    "--codex-config", options.config,
    "--only", "codex-bg",
  ];
  const [first, second] = await Promise.all([
    spawnInstaller(options, args, options),
    spawnInstaller(options, args, options),
  ]);
  const results = [first, second];
  assert.deepEqual(results.map((result) => result.status).sort((a, b) => a - b), [0, 0],
    results.map(resultText).join("\n---\n"));
  assert.equal(read(path.join(destination, "SKILL.md")), read(path.join(options.root, "skills", "codex-bg", "SKILL.md")));
  assert.equal(read(path.join(destination, "unrelated.txt")), "keep this\n");
  assert.equal(read(options.config), configBefore);
  assert.equal(fs.readdirSync(destination).filter((name) => name.startsWith("SKILL.md.bak.")).length, 1);
  const lockDir = coordinationDirectory();
  assert.equal(fs.statSync(lockDir).mode & 0o777, 0o700);
});
