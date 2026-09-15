// extension.js — a minimal VS Code relay for keep-warm request files.
//
// WHAT IT IS
// ----------
// It watches ~/.claude/wake-request/ for <sid>.json files, finds the VS Code
// terminal that belongs to that session id, and types the message into it.
// That is the whole job.
//
// THE ONE RULE: THIS IS A DUMB PIPE.
// It does not confirm, does not retry, does not keep a ledger, does not decide
// whether a message *should* be sent. Every one of those belongs to the sender,
// which owns the message and can read the target session's transcript. Putting
// a confirm here would (a) change the contract for every other sender that uses
// the same relay, (b) put the decision somewhere with no ledger, and (c) die
// with the relay. We measured the difference the hard way: this layer reporting
// "injected" 10 times out of 10 while only 8 messages actually reached the
// transcript.
//
// SESSION-STRICT
// --------------
// If the target session's terminal is not in THIS window, the file is left
// alone for the window that owns it — never injected into "the active
// terminal" or "the only terminal". A keep-warm turn in the wrong session is
// worse than a missed one.
//
// Install: see README.md.

const vscode = require('vscode');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const WAKE_DIR = path.join(os.homedir(), '.claude', 'wake-request');
const SESSIONS_DIR = path.join(os.homedir(), '.claude', 'sessions');

// Wait for VS Code to finish restoring terminals before the first scan.
// Scanning at activation finds an empty terminal list and leaves every pending
// request behind.
const STARTUP_DELAY_MS = 3000;

// A request nobody could deliver is dropped after this. It is NOT a guarantee:
// see README "known gap".
const WAKE_REQUEST_TTL_MS = 10 * 60 * 1000;

// The terminal input has a practical limit. We normalize FIRST and cut second,
// matching what the sender's confirm predicate assumes — if the two normalize
// differently, every confirm fails and every send is retried.
const MAX_MESSAGE_CHARS = 500;

// How to type. Two separate writes: body without a newline, then a bare CR.
// One fused `sendText(text, true)` has been observed to drop input.
const DEFAULT_SUBMIT_PLAN = ['body', 'cr'];
const SUBMIT_PLAN_MAX_STEPS = 8;
const SUBMIT_PLAN_MAX_DELAY_MS = 2000;

let channel;
const inFlight = new Set();

function log(level, message) {
  const line = `[${new Date().toISOString()}] ${level} ${message}`;
  if (channel) channel.appendLine(line);
}

// --- session id <-> terminal -----------------------------------------------

/**
 * Read the session registry and return the session id owned by a claude
 * process that is a descendant of `shellPid`.
 *
 * The registry is one JSON file per session process:
 *   ~/.claude/sessions/<claude-pid>.json  ->  { "sessionId": "...", "cwd": ... }
 * VS Code gives us the SHELL pid of a terminal, and claude runs as its child,
 * so we walk down from the shell rather than guessing.
 */
function sessionIdForShellPid(shellPid) {
  let entries;
  try {
    entries = fs.readdirSync(SESSIONS_DIR).filter((f) => f.endsWith('.json'));
  } catch {
    return null;
  }
  const descendants = descendantPids(shellPid);
  for (const file of entries) {
    const pid = Number(path.basename(file, '.json'));
    if (!descendants.has(pid)) continue;
    try {
      const data = JSON.parse(fs.readFileSync(path.join(SESSIONS_DIR, file), 'utf8'));
      if (data && typeof data.sessionId === 'string') return data.sessionId;
    } catch { /* a half-written registry row is not an error */ }
  }
  return null;
}

/** Bounded descendant walk via /proc. Two levels is enough for shell -> claude. */
function descendantPids(rootPid, depth = 2) {
  const found = new Set([rootPid]);
  let frontier = [rootPid];
  for (let level = 0; level < depth; level += 1) {
    const next = [];
    for (const pid of frontier) {
      let children = '';
      try {
        children = fs.readFileSync(`/proc/${pid}/task/${pid}/children`, 'utf8');
      } catch { continue; }
      for (const raw of children.trim().split(/\s+/)) {
        const child = Number(raw);
        if (child && !found.has(child)) { found.add(child); next.push(child); }
      }
    }
    frontier = next;
  }
  return found;
}

async function findTerminal(targetSid) {
  for (const terminal of vscode.window.terminals) {
    const pid = await terminal.processId;
    if (!pid) continue;
    if (sessionIdForShellPid(pid) === targetSid) return terminal;
  }
  return null;
}

// --- typing ----------------------------------------------------------------

function normalizeRelayText(text) {
  // Order matters: "a\rb" must become "a b", not "ab".
  return String(text)
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/[\x00-\x08\x0b-\x1f\x7f]/g, '');
}

function sanitizeSubmitPlan(plan) {
  if (!Array.isArray(plan) || plan.length === 0 || plan.length > SUBMIT_PLAN_MAX_STEPS) return null;
  const out = [];
  for (const token of plan) {
    if (typeof token !== 'string') return null;
    if (token === 'body' || token === 'cr' || token === 'body+cr' || token === 'newline-submit') {
      out.push(token); continue;
    }
    const delay = /^delay:(\d{1,4})$/.exec(token);
    if (delay && Number(delay[1]) <= SUBMIT_PLAN_MAX_DELAY_MS) { out.push(token); continue; }
    return null;
  }
  // Exactly one body write, or the message would be typed twice.
  const bodyWrites = out.filter((t) => t === 'body' || t === 'body+cr' || t === 'newline-submit').length;
  if (bodyWrites !== 1) return null;
  return out;
}

async function executeSubmitPlan(terminal, message, plan) {
  for (const token of plan) {
    if (token === 'body') terminal.sendText(message, false);
    else if (token === 'cr') terminal.sendText('\r', false);
    else if (token === 'body+cr') terminal.sendText(message + '\r', false);
    else if (token === 'newline-submit') terminal.sendText(message, true);
    else if (token.startsWith('delay:')) {
      await new Promise((resolve) => setTimeout(resolve, Number(token.slice(6))));
    }
  }
}

// --- request processing ----------------------------------------------------

function removeRequest(requestPath) {
  try { fs.unlinkSync(requestPath); } catch { /* already gone */ }
}

function isStale(requestPath) {
  try { return Date.now() - fs.statSync(requestPath).mtimeMs > WAKE_REQUEST_TTL_MS; }
  catch { return false; }
}

async function processRequest(requestPath) {
  let request;
  try {
    request = JSON.parse(fs.readFileSync(requestPath, 'utf8'));
  } catch (err) {
    log('WARN', `unparseable request ${path.basename(requestPath)}: ${err.message}`);
    removeRequest(requestPath);
    return;
  }
  if (!request || typeof request.sid !== 'string' || typeof request.message !== 'string') {
    log('WARN', `invalid request ${path.basename(requestPath)}`);
    removeRequest(requestPath);
    return;
  }

  // `sid` in the payload is authoritative, not the filename.
  const sid = request.sid;
  const dedupeKey = `${sid}:${request.message.slice(0, 64)}`;
  if (inFlight.has(dedupeKey)) { removeRequest(requestPath); return; }
  inFlight.add(dedupeKey);

  try {
    const terminal = await findTerminal(sid);
    if (!terminal) {
      // SESSION-STRICT. Another VS Code window may own this session; leave the
      // file for it. Only give up when the request has outlived its TTL.
      if (isStale(requestPath)) {
        log('WARN', `stale request expired sid=${sid.slice(0, 8)}`);
        removeRequest(requestPath);
      } else {
        log('WARN', `terminal not in this window — leaving for owner sid=${sid.slice(0, 8)}`);
      }
      return;
    }

    const message = normalizeRelayText(request.message).slice(0, MAX_MESSAGE_CHARS);
    const plan = sanitizeSubmitPlan(request.submit_plan) || DEFAULT_SUBMIT_PLAN;
    await executeSubmitPlan(terminal, message, plan);
    log('INFO', `injected sid=${sid.slice(0, 8)} source=${request.source || 'unknown'} plan=${plan.join(',')}`);
    removeRequest(requestPath);
  } catch (err) {
    log('ERROR', `injection failed: ${err.message}`);
    // Remove it anyway: a request that threw mid-typing may have been partially
    // delivered, and re-typing it would double-inject. The sender's confirm is
    // what decides whether to try again — that is its job, not ours.
    removeRequest(requestPath);
  } finally {
    inFlight.delete(dedupeKey);
  }
}

function scanAll() {
  let files;
  try { files = fs.readdirSync(WAKE_DIR).filter((f) => f.endsWith('.json')); }
  catch { return; }
  for (const file of files) processRequest(path.join(WAKE_DIR, file));
}

// --- activation ------------------------------------------------------------

function activate(context) {
  channel = vscode.window.createOutputChannel('keep-warm injector');
  context.subscriptions.push(channel);
  log('INFO', `watching ${WAKE_DIR}`);

  try { fs.mkdirSync(WAKE_DIR, { recursive: true }); } catch { /* ok */ }

  setTimeout(() => {
    scanAll();      // bootstrap: catch requests written before we woke up
    const watcher = fs.watch(WAKE_DIR, (_event, filename) => {
      if (!filename || !filename.endsWith('.json')) return;
      processRequest(path.join(WAKE_DIR, filename));
    });
    context.subscriptions.push({ dispose: () => watcher.close() });
  }, STARTUP_DELAY_MS);

  context.subscriptions.push(
    vscode.commands.registerCommand('keepwarmInjector.scanNow', () => {
      log('INFO', 'manual scan');
      scanAll();
    }),
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
