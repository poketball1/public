# AIR Codex Subagents

Project-local Codex custom agents live in this directory. Codex loads each
`*.toml` file as a standalone custom agent when the project is trusted.

Injection paths (ADR-570 D7): a codex-native subagent spawn auto-injects the
role's `developer_instructions`. The `/codex-bg` wrapper does NOT load these
tomls — a parent packet that wants a roster role must open with: "Read
`.codex/agents/<role>.toml` and bind its `developer_instructions` as your role
contract." The toml is each role's single SoT; the briefs below only shape the
parent's work-context packet and must not restate contract content.

Review-role spawn discipline (ADR-570 D3/D5): a falsifier or closure spawn
must be fresh — independent of every thread that produced the work under
review (no same-thread self-review). A falsifier's radius is defined by its
packet; the role never self-escalates. A scope/frame audit is commissioned
claim-shaped ("claim: our scope line is right — refute it"), never
list-shaped — the frame under attack is the review object, not the worker's
operating envelope.

## Roster

Live roles = the black list (the seats Luna is not used for, each with a
Sol/xhigh toml pin) plus `luna_worker`. There are no separate Luna seats:
everything outside the black list is a `luna_worker` packet (ADR-872 추기 (8)
정정 2026-09-09).

- `luna_worker`: leaf volume worker pinned to Luna/max under `@AGENTS.md`
  §Worker Principles; takes a scoped task whose completion evidence is named in
  advance and spawns nothing. Its return shape includes `Requirements:`: one
  line per explicit packet requirement → location, or `not done: <reason>`; an
  unmet requirement is a Blocker — never a Risk, never "historical residue".
  Observation inbox: `@docs/ops/luna-observation-log.md`; the hirer appends
  fact-only rows for badly performing Luna hires per that file's header.
- `falsifier`: pre/post falsification reviewer. Black-list role, Sol/xhigh pin.
- `closure`: closing-readiness auditor and bounded closing-legwork worker for
  SoT, docs, map, dead-code, worktree, and verification surfaces. Black-list
  role, Sol/xhigh pin.
- `air_analyst`: AIR evidence analyst. One role for four surfaces — runtime
  prompt input, model response, request flow, authored instruction text; the
  packet names which ones. Returns coordinates and candidate readings, not
  verdicts. Black-list role, Sol/xhigh pin.
- `learning_distiller`: occasional learning agent that turns repeated patterns,
  overrides, and rework into reusable next-action rules. Black-list role,
  Sol/xhigh pin.
- `open_cognition_partner`: open-thinking design partner for fragile
  assumptions, latent constraints, decisive unasked questions, and — absorbed
  from `vp_router` — whether a bounded subagent probe is worth making now.
  Black-list role, Sol/xhigh pin; Codex-led lanes only.

Retired roles whose aliases are still on disk are listed in §Invocation Policy.

## Invocation Policy

This is a v0 skeleton. It is intentionally a routing reflex rather than a
mandatory pipeline.

Owning surfaces:

- `@AGENTS.md`: durable Codex behavior contract and task-mutation boundary.
- This README: Codex subagent routing, role selection, and prompt packet shapes.
- `*.toml`: one agent's own behavior, output contract, and stop condition.
- `@docs/user-agent-communication/goal-mode.md`: `/goal` state custody,
  approval parking, and context-custody runbook.
- `@docs/user-agent-communication/boss-mode.md`: compact Boss Mode operating map.
- `@docs/user-agent-communication/goal-boss-mode.md`: legacy compatibility
  pointer only; do not add new rules there.
- Lesson/report docs: historical evidence. Distill only repeated failures into
  the owning surface above.

- Boss Mode, saturation, completion/falsifier, and capability/mutation boundaries
  live in `@AGENTS.md`; this README only helps route subagents and shape packets.
- In Codex-led Boss Mode, this roster is the Codex employee/specialist pool and
  the VP/design-review lane is Codex-only. Do not route VP or worker work to
  Claude/Opus in a delegation chain — detached/background Claude completion has
  no Codex wake, direct `claude-coder` is synchronous rather than an autonomous
  background carrier, and Claude background sub-agents have no auto-wake. Those
  lifecycle constraints make the chain unreliable (user decision 2026-07-05).
  Cross-model Claude review is a separate `@AGENTS.md` Design Review Channel
  decision (explicit user request or material Codex-led Boss Mode review), not a
  worker-chain recommendation.
- `사장모드` / `사장 모드` or explicit subagent-backed orchestration: main
  orchestrates. A standalone VP/cross-model review request follows `@AGENTS.md`
  role defaults and does not by itself activate full Boss Mode.
- Audience gate for this "Use X for Y" list: it describes Codex-led routing.
  A Claude-main session delegating into this roster follows
  `.claude/rules/delegation.md` (design authority stays with main; user
  decision 2026-06-12/2026-07-25). The bullets below are not an instruction to
  Claude main. In particular, a Claude-main hire excludes
  `open_cognition_partner` — design partnership is a Codex-led lane only,
  because design authority stays with main (same user decision).
- Retired 2026-09-09 (7 aliases on disk, no model pin — spawning an old name
  runs the old body on the `[agents]` default): prompt_input_analyst,
  agent_response_analyst, agent_flow_observer, workflow_rationalist →
  air_analyst; vp_router → open_cognition_partner; evidence_scout,
  implementation_mechanic → luna_worker (ADR-872 추기 (8) 정정).
- Use `luna_worker` for volume and mechanical work: the leaf role under
  `@AGENTS.md` §Worker Principles. It spawns nothing, and its packet names the
  completion evidence in advance. Investigation, SoT lookup, bounded
  implementation, census — anything outside the black list — is a `luna_worker`
  packet; the packet names the completion evidence, and authority
  classification and conflicting-source disposition come back under
  `Open Meaning` for the parent to rule on.
- Use `air_analyst` for live AIR evidence — DB operational logs, request
  diagnostics, recordings — and for instruction-surface review. It is one role
  covering four surfaces; the packet names which of prompt input, model
  response, request flow, and authored instruction text to cover, and which are
  intentionally excluded. Spawn it more than once when two surfaces need
  independent eyes. It is judgment-grade live analysis and instruction review —
  a specialist evidence input, not a gate. Sol/xhigh pin.
- Use `falsifier` for the pre-implementation attack on design assumptions and
  for the pre-handoff attack on a completion claim. Review method and triggers
  live in `@AGENTS.md`; the spawn must be fresh (see Review-role spawn
  discipline above). Sol/xhigh pin.
- Use `closure` near handoff when derivative closing work matters across
  document/SoT, map/dead-surface, worktree/stale-wording, or verification
  surfaces — Codex-main self-audit only; a Claude-main lane uses `/closure`. Its
  detailed validation checklist lives in `.codex/agents/closure.toml`; this
  README only selects the role and shapes the parent packet. `closure` may do
  in-scope doc/map legwork, but main owns the close and risk acceptance.
  Sol/xhigh pin.
- Use `learning_distiller` after repeated patterns or large-round closure —
  repeated failures, overrides, or rework distilled into reusable next-action
  rules. Sol/xhigh pin.
- Use `open_cognition_partner` for fragile assumptions, latent constraints,
  decisive unasked questions, reality-anchor review, and — absorbed from
  `vp_router` — whether a bounded sub-agent probe is worth making now.
  Sol/xhigh pin. Codex-led lanes only.
- Lesson/report absorption should end in a small owning-surface edit or an
  explicit park decision. Do not make every lesson report a new mandatory input
  queue.

## 사장 모드

When the user asks for `사장모드` or `사장 모드`, explicit subagent-backed
orchestration, or a subagent-backed task list, Boss Mode authority and edit
boundaries are defined in `@AGENTS.md` §사장 모드. This README only adds
subagent routing and packet-shape guidance.

Operational reminder (full model: `@AGENTS.md` §사장 모드): subagent output is
evidence for main judgment — not completion, authorization, approval, veto, or
closure.

For `/goal` work in 사장 모드, use the docs-based communication channel:

- @docs/user-agent-communication/goal-mode.md
- @docs/user-agent-communication/boss-mode.md
- @docs/user-agent-communication/comments.md
- @docs/user-agent-communication/goal-state.md

Open user `Comment:` entries need plain-language `Reply:` entries before the
main agent crosses a decision-sensitive boundary.

For ordinary one-turn Boss Mode, do not touch `comments.md` or `goal-state.md`
unless the user asks for durable state, the work is a `/goal`, or the task is
decision-sensitive, multi-agent, long-running, or compaction-sensitive.

Assume subagents are context-blind. Main should package the relevant goal,
comment snapshot, goal-state snapshot, scope, constraints, and stop condition in
each subagent prompt. Subagents should disclose `Basis Used`, missing context,
assumptions, and staleness risk.

Output-shape precedence is: parent-requested shape, then the agent TOML's exact
shape, then any `/goal` context-custody suffix. Do not request the full shape
when a compact shape is enough. Every agent-specific output shape should include
these common fields when applicable:

- `Recommendation`
- `Decision Diff`
- `Confidence`
- `Stop Condition`
- `Main-Agent Check`

For `/goal` 사장모드 work that uses the context-custody contract, the main
agent should request the fuller output shape from the task packet:

- `Basis Used`
- `Evidence`
- `Assumptions`
- `Not Seen / Missing Context`
- `Staleness Risk`

The main agent remains responsible for integration, judgment, and final user
communication.

## Advisor Discipline

The roster is decision leverage, not volume delegation. Before hiring an advisor
role, main asks:

> Could local routing advice change the next action, approval boundary, worker packet,
> verification gate, or task list?

Default: no-call. Hire an advisor role only when:

- Ownership, source-of-truth, approval boundary, or verification scope is
  unclear.
- The task list changed after new evidence, interruption, or scope shift.
- The user asks for VP/routing and the answer could affect more than
  reassurance.
- Product-code implementation is in scope but the worker packet boundary is not
  clear enough to dispatch.

Skip VP when the next action is local evidence gathering, a bounded worker
dispatch, obvious verification, or an approval-ready user ask. After VP answers,
main records accept/override in one line and proceeds with main decision, user
ask, worker packet, verification gate, or park.

Each project subagent TOML owns its live model and reasoning configuration (a
TOML without a `model` line takes the project default in `.codex/config.toml`
`[agents]`, Luna/max since 2026-09-07 per `@AGENTS.md` §Worker Principles —
`implementation_mechanic` does; judgment roles such as `falsifier` pin
Sol/xhigh, ADR-872 추기 2026-09-07 (4)).
Inspect those fields instead of copying their values into prose. Treat a
judgment-role call (the Sol/xhigh pins) as expensive decision leverage, not volume
delegation; `implementation_mechanic` on the Luna default is the volume lane per
`@AGENTS.md` §Worker Principles and is priced accordingly.

- Every call needs an expected `Decision Diff`: what would the main agent do
  differently after this answer?
- Prefer one agent at a time unless scopes are independent.
- Give each agent a bounded prompt, owned scope, and stop condition.
- Reuse an existing agent thread with `send_input` when the follow-up depends on
  its prior context.
- Close agents when their role in the current task is done.
- `Decision Diff: none` is a useful result; do not force a change.

Skip expensive agents when the next action is already clear, local, reversible,
cheap to verify directly, already specified by the user, or mainly a
reassurance call. This skip rule is for routing/advisor calls; Boss Mode code
patch boundaries still follow `@AGENTS.md`.

Live prompt/response/flow specialists are separate evidence surfaces, not a
committee: prompt input, model response, and request flow. For a broad live
anomaly, main may dispatch all three with distinct questions. For a narrow
anomaly, dispatch only the relevant surface and record the reason.
After two advisory answers on the same decision, the next action is main
decision, user ask, worker packet, verification gate, or park unless new runtime
evidence changes the question.

## Prompt Briefs

Common packet-authoring rules (apply to every brief you write for a worker):

- Never put a time budget, a deadline, or a "check whether you can finish
  inside the limit" instruction into a worker packet. A worker cannot sense
  wall-clock time, so the instruction only burns reasoning tokens. Narrow by
  scope instead; the wrapper cuts a timeout anyway and main recovers losslessly
  by resuming the same thread against the worker's externalized state file.
- Keep the packet's report artifacts on paths separate from the wrapper
  `--output` path. On completion the bg-runner rewrites that file with its own
  envelope schema (`final_response` plus invocation metadata), so custom
  structured fields the packet asked for are lost. Ask for
  `<slug>-report.md` / `<slug>-report.json` and let the run output carry only a
  pointer plus the summary.
- Frame falsification and boundary work in QA vocabulary. Attack-framed English
  ("attack", "break", "bypass", "construct a value that breaks X") combined with
  low-level boundary probes trips the provider content filter and kills the turn
  mid-run (`turn.failed`, empty `final_response`). Same technical substance,
  neutral framing: "boundary/edge-case QA", "verify the predicate rejects X",
  "completeness review". If a run is killed this way, do not resume that thread
  — rewrite the packet and start a fresh run.

Common advisor follow-up rule:

```text
Do not recommend another advisor by default. Return one of: main decision,
user ask, narrower worker packet, verification gate, or park. Recommend another
advisor only when new evidence creates a different decision question.
```

Local routing brief:

```text
You are the local Codex-roster router for this task.
Context:
- Objective:
- Current task list:
- Next decision:
- Constraints / source of truth:
- Known risks:

Please recommend no-call, call-one, or call-two.
Include a task-list delta, expected decision diff, and exact next-agent prompt
briefs if you recommend a call.
```

Open cognition brief:

```text
Use the smallest useful probe set. Focus on fragile assumptions, missing
constraints, and decisive unasked questions. Reality-anchor each finding as
adopt, park, monitor, or reject.
```

Workflow rationalist brief:

```text
Treat this workflow, prompt, or instruction set as an executable behavior
contract. Act as an advisor, not a veto gate. Preserve essential behavior, but
reduce ceremony, duplicated control flow, unclear ownership, overconstraint, and
weak invocation boundaries. Classify rules as Core, Risk-triggered, or Parked.
Return only minimal behavior-changing edits with exact file/section anchors.
Propose deletion or merge before adding new process. If recommending a stop,
name the smaller executable next action in the same answer.
```

Evidence scout decision-history brief:

```text
Find decision-changing evidence for this claim, including past decisions if
they matter.

Decision question:
Affected domain/files/IDs:
Known terms and legacy names:
Current suspected SoT:

Search current authority first, then past-decision surfaces:
AGENTS import map, docs/architecture/README.md decision order, owning
architecture docs, accepted ADRs, code/schema/live evidence, docs/big_plan,
docs/report, docs/checkpoint/INDEX.md plus selected checkpoints only, and
docs/user-agent-communication goal-state/comments for active approvals.

Do not optimize for saving tokens inside this assigned question. Do 2-3
self-check passes: likely evidence, contradictory/superseding evidence, then
alternate keywords/legacy names/index references. If nothing changes, say
`Decision Diff: none` and name what was rechecked.

For retire / graduation / SoT-consolidation claims, judge liveness by
reachability from an accepted live entry point of the surface (CLI/job/admin/
migration/route all count), not by mere reference existence — at symbol level (a
dead symbol inside a live module is dead; a retired path's tests/benchmarks are
not callers). "A reference exists" is not "reachable". When the parent frames a
fresh audit, do not inject preservation assumptions into the prompt — they anchor
the conclusion. (Absorbed from Claude boss-mode review lens; a dead legacy path
once passed 13 audit rounds on "references exist". ADR-340 D7.)

Classify each row as current SoT, accepted ADR, code/schema/live evidence,
active approval/comment, historical evidence, proposal, or contradiction. Return
coordinates and the decision diff; do not summarize broad history.

The stored code-map layer is retired (ADR-459): remaining `# Owner:` annotations
and old vocab/ledger surfaces are historical text, not ownership facts — never
cite them as truth (a stale header reports itself as truth, BP-069 F1/F2). For
backend ownership/routing questions use the owning architecture contract
(`docs/architecture/README.md` Directory Ownership), accepted ADRs, and
live-tree derive tools (`report_reachability.py`, `rg`); treat BP-067 as
historical launch/graduation context only.
```

Falsifier brief:

```text
You are the Falsifier for this claim. First read `.codex/agents/falsifier.toml`
and bind its developer_instructions as your role contract — the /codex-bg
wrapper does not auto-inject it.
Mode: pre | post
Claim Under Test:
Owned scope / surfaces:
Known decisions and SoT anchors:
Additional attack axes (optional — round-0 remains yours):
Constraints: findings-only; ignore peer dirty files outside scope.
```

Closure brief:

```text
You are Closure for this lane. First read `.codex/agents/closure.toml` and
bind its developer_instructions as your role contract — the /codex-bg wrapper
does not auto-inject it.
Work context:
- Objective / lane:
- Decided design and worker partition to respect:
- What changed / what workers did:
- Files changed or expected dirty surfaces:
- Decisions already made by main:
- Known concerns or suspicious surfaces, as hints:
- Allowed write scope for bounded doc/map legwork:
- Forbidden scope:
- Verification already run:

Audit closure readiness and do bounded closing legwork inside the allowed write
scope. The validation checklist lives in your agent contract; use this prompt as
work evidence and boundary context, not as the checklist or exhaustive audit
boundary. Do not redesign the work or own the close. If docs/ADR/SoT/map updates
are required and the decision context plus write scope are sufficient, do the
legwork instead of punting to main. For product code/test changes, return a
bounded packet for the owning workflow/worker.
```

Live prompt/response/flow analyst briefs:

```text
The exact evidence contract and output shape live in the specialist TOMLs, not
in this README:
- `.codex/agents/prompt-input-analyst.toml`
- `.codex/agents/agent-response-analyst.toml`
- `.codex/agents/agent-flow-observer.toml`

Parent packet should pass the run coordinates and one distinct question per
surface:
- conversation_id / request_id / entry_id when known
- expected product behavior
- suspected divergence
- which DB/log/timeline rows are already known
- fallback-only status if DB evidence is missing

Prompt analysis normally requires the matching `air_operational_logs`
`[LLM+Tools 입력 텍스트]` DB row. Response and flow analysis likewise start from
actual DB/runtime evidence, not code-path inference.
```

Implementation mechanic brief:

```text
Implement this already-decided code/test/tooling patch scope. You are not alone
in the worktree; inspect current files and never revert unrelated changes.

Objective:
Design decision already made:
Owned files / modules:
Expected behavior:
Excluded scope:
Verification to run:
Stop-on-design-drift:

If any required boundary is missing or code reality contradicts the design,
return blocked-missing-implementation-boundary or blocked-by-design-drift
instead of widening scope.
Treat Owned files / modules as the write boundary. Read outside files only for
context; report any required outside-scope edit instead of making it.
```
