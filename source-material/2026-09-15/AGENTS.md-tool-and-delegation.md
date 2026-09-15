<!-- excerpt of /config/work AGENTS.md, 2026-09-15: section ## Tool And Delegation -->

## Tool And Delegation

Before design review or implementation, make a quick delegation-shape judgment.
This is judgment, not forced delegation: keep main-session attention on framing,
boundaries, integration, and risk, and delegate only where it materially improves
speed or design quality.

### Worker Principles

PC1 main sessions run on Fable by default and also on Opus (user decision
2026-07-27). Fable remains the permanent top judgment authority (user-confirmed;
there is no retirement premise). Behavior and operating lanes are model-identical:
an Opus main fully owns design and judgment, up to and including overturning accepted
decisions and owning contracts. A Fable-judgment-needed signal fires only above
that — redesigning project-wide principles or the instruction system itself;
forks where reasonable designs diverge and either choice binds long-term; one's
own design failing to converge across repeated rounds — mark the spot with
evidence, options, and a recommendation, and do not block progress. The
division of labor is fixed:

- Design judgment, design-material specs, brief/instruction review, and risk
  acceptance are main-owned (Fable or Opus main alike). Tier-1 routine legwork
  (investigation, implementation, verification) defaults to a Claude Opus
  employee sub-agent Fable spawns directly — a Claude-only mechanism. Codex's
  default lane is the tier-2 carrier below. (**VP seat, ADR-872 D4 trial**: the
  VP runs on the wrapper's `vp-*` role model — a fresh Codex one-shot in QA
  wording, called only when the user explicitly asks for a VP on that decision
  (user ruling 2026-09-06); it judges in its own thread and may hire one or two
  sol/luna workers only to collect material (census, sweeps, coordinates — never
  design or implementation); two round-trips per decision; its packet carries
  intent, hard walls, and the contention plus file pointers, and the VP reads
  those files itself. The Opus VP that held the seat before this trial is the
  comparison baseline, not a guaranteed floor. Codex falsifier work remains in
  two places: the built-in saturation pass inside a tier-2 deputy campaign, and
  Codex-main sessions auditing their own lane. If a one-off design-attack packet
  still lands on you, the old rules hold: re-derive the target enumeration from
  the authority source before attacking details; design authority and completion
  judgment stay with Fable — your factual corrections are adopted because they
  are facts, your added design opinions are ruled on point by point, and a
  wholesale reversal is as unwelcome as deference.)
  - **Tier-2 campaign carrier — the only one.** Codex is the sole tier-2
    deputy-boss carrier for every campaign kind; Opus is tier-1 one-shot only
    (user decision 2026-09-02): an Opus deputy multiplies employee fan-out ×
    rounds × built-in falsification, all in Claude tokens. This is the current
    dial, not a permanent ruling — the user re-adjusts it by watching Fable vs
    Opus burn; agents report burn, they do not re-open the lane (dial history =
    `docs/ops/token-dial-ledger.md`). The one surviving Claude-side deputy is the
    journey-round-boss, ADR-698 D1, pending user disposition. Act as a deputy
    boss: employ your own Codex
    sub-agents for higher-volume investigation, implementation, verification, and
    bug-class excavation (hidden consumers, patch-paths, latent branches, fact
    cross-checks), and run a built-in falsifier saturation pass before reporting
    back once. **Call-count discipline**: the seat's cost is calls × ~130k
    tokens, and the 130k is structural — codex auto-compacts at ~90% of the
    window, so per-call context is the sawtooth midpoint whatever you put in it.
    The two biggest avoidable call classes are short polling and re-reading files
    already read. So: wait with the long `wait_agent` cadence required below
    (30–60 min; the hook floor is 10 min) and never poll at 20–60 s; do not
    re-open a file read in the same cycle (keep coordinates in `state.md`,
    re-read changed ranges only); take worker output as files with a 3-line
    return — finished workers' full reports are re-attached to every later
    `wait_agent`/`list_agents` result. Measurement:
    `docs/report/codex-run-failure-resume-cache-2026-09-08/context-composition.md`.
  - **Tier-1 ↔ tier-2 dividing line** (user ruling 2026-09-09 — pressure points
    to Opus; ADR-872 addendum (6)): tier-1 employees are **Opus by default** —
    investigation, census, close reading, cross-checks, audit (closure·front-closure),
    cross-family falsification, and coordinate-fixed small implementation are
    tier-1 Opus one-shots. **Codex holds two seats — the tier-2 deputy boss and
    the VP** — it is not a tier-1 employee. Investigation or implementation goes
    to a Codex deputy only when it is medium-or-larger enough to deserve a deputy
    seat (rounds that keep turning — the three tier-2 shapes below). When in doubt,
    start at tier-1 Opus and promote to a Codex deputy once tier-2 need shows.
    Why: investigation quality feeds design-judgment quality; the rise in the Opus
    employee share is accepted and is what this ruling trades against the cost
    case for Codex volume — read the burn with `claude_usage.py --by agent`
    (evidence: `docs/report/claude-usage-opus-vs-fable-2026-09-07.md`; dial
    history: `docs/ops/token-dial-ledger.md`). A Codex deputy's workers default to
    Luna/max (Sol workers only for judgment roles and slices whose Luna draft
    missed the bar — below). Three
    shapes where tier 2 pays: five-plus workers whose results must be merged and
    re-dispatched; work granted write access to shared state; an unattended
    multi-hour campaign — because those are where a main session would otherwise
    absorb the merge/re-dispatch judgment itself.
  - **Fable-grade deputy judgment envelope (ADR-872).** The
    wrapper assigns the deputy-boss model to any run whose `--output` basename
    starts with `deputy-` (current value: `codex-bg.sh health | jq .role_models`).
    When you run as that Fable-grade deputy, judgment authority moves from
    reasoning altitude to **context ownership**: decisions that fit inside the
    packet are yours; only decisions that need the user's intent, the session
    dialogue, or a prior ruling return to main. Vocabulary: falsifier finding
    grades ①/② are defect grades, not authority classes — a ① defect inside your
    scope you fix and re-falsify, you do not STOP. **Discretionary decisions**:
    implementation design knobs — module-internal structure, test shape, error
    *wording*, naming within conventions, worker fan-out and per-worker model,
    round count, local boundaries the packet left open — decide, then log one
    row. Failure *semantics* (sentinel vs exception, retry, rollback placement,
    verification oracle) are not discretionary. **STOP reasons, four**: ⑴
    user-owned classes and hard walls (names and base-surface copy, external
    inputs, reopening a user ruling, blocking/approval/prod/data-loss/secrets)
    ⑵ conflict with a standing decision — evidence that would overturn a prepaid
    ruling, an accepted ADR, an owning contract, or a user ruling: return the
    evidence and the conflict coordinate, never overturn; undecidable cases (no
    grounds, two valid instructions in conflict) belong here too ⑶ a decision
    that meets the ADR rubric (`docs/CLAUDE.md` §ADR 판단 기준) ⑷ convergence
    failure (round N not fresh-0 — the existing rule). The packet owes you a
    **list of standing rulings** (prepaid rulings plus the area's ADR/contract
    coordinates); without it you cannot judge ⑵ and the packet is incomplete.
    **Decision log**: one row per discretionary decision — decision · rejected
    alternatives · why · which ADR/contract it agrees with · reversal cost — as a
    `## 판정 로그` table in your final report; a return without it is
    incomplete. Your built-in falsifier attacks the decision log as well as the
    code; its model is the `falsifier` role pin (Sol/xhigh — a judgment role);
    volume workers take the project config default (`.codex/config.toml`
    `[agents]`, Luna/max), and any other model is explicit at spawn as a
    model + effort pair with a one-line reason. On return, main reads the whole log (keep it short — length is a
    signal), keeps its decisive-evidence spot-check, and sends one fresh Opus
    falsifier over log plus real effects. **Three self-handled classes (D7),
    all workers**: stale coordinates/facts — re-derive from the authority source
    and record the correction (a changed frame is ⑵); local packet gaps (no
    shared state touched) — decide and log; non-base copy (error/refusal
    reasons, hints, tool results, UI copy) — draft per the rubric and tag
    `문안 초안`. Shared undecided choices (registry classes — a missing row does
    not make something local; writers, readers, or effects crossing a
    file/process/session boundary make it shared) STOP for Opus/Sol workers and
    are discretionary only for the Fable-grade deputy; base prompts, agent
    instructions, function descriptions, and names always STOP. Executing an
    existing contract (calling a permitted primitive, mechanically repairing a
    contract violation) is outside this table. Scope: in-session deputy bosses
    and tier-1 workers; goal packets keep their current contract (D8). Claude-side
    SoT: `.claude/rules/delegation.md` §작은 사장.
  - **직원 기본 = Luna/max — 최대 활용 강도, Sol 직원은 관측된 예외** (SoT = ADR-872 추기 (4)(5); 기존 위임 지침의
    보수적 기본값을 초과해도 된다). 기본값은 `.codex/config.toml` `[agents]` 가 쥐고
    (우선순위 = 스폰 명시값 > 역할 toml pin > 기본값), 정규 호출은 `agent_type="luna_worker"` + `fork_turns="none"`(생략 =
    `all` = 부모 이력 통째 fork; 272K 초과 입력은 요청 전체 요금 2배·출력 1.5배). builtin 역할(default·worker·explorer)도
    Luna 로 뜨지만 `luna_worker` 의 반환 계약은 자동 주입되지 않으므로 아래 부모 의무는 어떤 Luna 스폰에도 같다. 추론은
    모델별 고정(Luna `max`·Sol `xhigh` — 사용자 2026-09-06).
    **Luna 가 맡는 단위 = 계약 하나**: 같은 계약·같은 완료 기준 안의 구현·테스트·형제 수정·회귀·문서 갱신·조사·대조·재계산·
    보고 초안을 한 직원의 소유 범위로 준다 — 파일 수로 쪼개지 않고, 값이 여러 파일을 건너면 전달 끝까지 한 묶음이며 연결
    확인의 소유자는 부모가 지정한다. 새 계약의 첫 조각은 효과를 확인한 뒤 같은 기준의 형제로 넓힌다. **판정이 섞인 조각도
    Luna 초안 먼저** — 원인 탐색·경계 불명 다파일 변경·집합 정당성 반증도 Luna 가 원문·분모·후보를 갖춘 초안을 내고
    부모/Sol 이 판정한다.
    **기본은 Luna 다. Luna 를 쓰면 안 될 자리(black) 빼고 다 Luna 를 쓴다.** (사용자 결정 2026-09-09, idea 179.) black =
    **(a)** 판정 역할 — 감리(falsifier·closure) · live 분석(air_analyst) · 학습(learning_distiller) · 설계 동업
    (open_cognition_partner; Claude main 은 기용 안 함) — Sol/xhigh pin 은 이 다섯뿐 **(b)** Luna 초안이 완료 기준을 못 넘긴
    조각의 재작업 **(c)** 문서함(`docs/ops/luna-observation-log.md`)이 같은 조건→실패를 보여 옮긴 조건(현재 0건). 목록은 (c) 로만 늘고, 구체 피드백 뒤 Luna 가 처리한 조건은 뺀다 — 업무
    종류(테스트·문서·다파일·JSONL)로 적지 않는다. Sol 스폰은 `model="gpt-5.6-sol", reasoning_effort="xhigh"` **쌍** 명시(model
    만 쓰면 effort 가 기본 max) + 판정 로그에 목록 항(a/b/c) 한 단어 — 별도 "왜 Luna 로 안 되는가" 산문은 두지 않는다(사유의
    집은 이 목록과 문서함 `Sol 회수` 행). **black 이 packet 을 이긴다** — packet 이 감리 라운드를 Luna 로 쓰라고 해도 falsifier 는 `agent_type="falsifier"` (실측 2026-09-10: Luna 로 돈 감리 7 라운드가 fresh-0 근거가 됐다). Sol 이 가진 문맥으로 몇 분이면 끝나는 일은 직접 한다.
    **회수 단위 = 판정, 물량은 되돌린다**: Sol·부모가 의미를 정하면 그 의미의 형제 적용·회귀·확정 수리는 같은 Luna 로
    돌아간다 — Sol 이 조각을 쥐는 것은 가정·판정 기준이 라운드마다 바뀌는 동안뿐이다.
    **Luna 에 주는 부모의 의무**: 완료를 기계로 확인할 기준(테스트 명령·diff 모양·건수·스키마)을 packet 에 적는다 —
    검증 oracle 을 Luna 가 고르지 않는다. 테스트 저작은 bind 대상·fixture 출처·**정상 경로와 분리한** 예상 실패를 정한
    조각만(한 코드에 섞으면 중간 marker 로 통과하는 false-green). packet 에는 알고 있는 미결 축·쓰기 경로·읽을 입력 범위를
    적는다(모든 축의 선견 의무는 아니다; 시간 예산은 적지 않는다). **Luna 산출은 초안이다**: 기준이 정하지 않은 해석·
    분류는 결론짓지 않고 원문·분모·후보를 `Open Meaning` 으로 돌려주고(완료 증거·결정이 없으면 `blocked-missing-*`), 명시
    요구는 `Requirements:` 항목별 처분(착지 좌표 또는 `not done: 사유`)으로 돌려주며 미소진 요구는 Blocker 지 잔여·Risk 가
    아니다. 부모는 채택 전 **원문·분모·실제 효과·요구 목록 소진**을 확인한다 — 완료 증거는 "통과" 문장이 아니라 원문
    명령(공식 wrapper 포함)·실행 scope·반환값이고, Sol·falsifier 의 정정도 같은 대조를 거친다. Luna 검토는 초안 검토라
    falsifier·closure 를 대체하지 않는다. 끝난 직원은 `send_message` 로 재개되지 않는다 — 후속은 `followup_task`. 고용자는
    Luna 발주 원문을 자기 산출물에 보존한다(rollout 은 암호화).
    **관찰 문서함** (사용자 결정 2026-09-08): 잘 안 된 Luna 고용 — **Luna 조각이 완료 기준을 한 번에 못 넘긴 것**(falsifier ①
    이 난 초안·부모가 다시 한 조각·미집행/오분류 회수·Sol 회수; 같은 Luna 가 고쳐 채택돼도 해당 — 판독 2026-09-10) — 은
    **고용자가** `docs/ops/luna-observation-log.md` 에 한 행 append 한다(조각·조건·실패 형태·처분 = 같은 Luna 수리 / Sol 회수 /
    부모 직접) — 사장 보고에 별도 관찰 절은 두지 않고, packet 이 보고 양식에 `Luna 관찰` 절을 요구해도 문서함 행이 그 자리다.
    사용자가 문서함을 비정기로 열어 예외 문장 개정을 판정시킨다. 잘 된 고용(첫 반환이 그대로 채택)은 쓰지 않는다(분모 =
    `codex_usage.py` `luna.summary.children`).
    **깊이**: 작은 사장 → Luna, 또는 작은 사장 → Sol(예외) → Luna. 부모가 있는 직원이 고용할 수 있는 것은
    `luna_worker` 뿐(Sol→Sol 연쇄 금지)이고 Luna 는 스폰 도구가 없는 말단이다. codex 는 스폰된 agent 에 "부모가 있고
    final 응답은 부모에게 간다"는 developer 메시지를 주고 `<multi_agent_mode>` 는 고용을 "AGENTS.md 가 명시할 때만"으로
    묶는다 — 이 문단이 그 명시다. Sol 직원을 두는 것은 packet 이 "작은 사장"으로 캐스팅한 root(codex-bg 로 시작된
    스레드)만이다. Luna 는 sub-agent 로만 산다 — codex-bg 최상위 `--model gpt-5.6-luna` 는 wrapper 가 거부한다
    (실측 2026-09-06).
  - Outside those two lanes, review and audit outputs stay factual — verify
    claims, restate facts and invariants, and do not append design
    recommendations.
- Evidence-grade reporting binds: SHA-pinned coordinates; authority claims
  (contract/ADR) carry verbatim quoted lines; load-bearing claims carry a 1:1
  evidence pointer; partials and blockers are reported honestly with the exact
  failing command + transcript. Summary-only assertions are not acceptable for
  load-bearing claims.
- Dossier-class deliverables meet the dossier bar: authority excerpts, probe
  pack, producer↔consumer trace per tension, claim ledger, core ≤500 lines
  (the inline list is the current rule; its origin, the PC2-era orchestration
  contract §Design-Material Dossier Bar, is archived). The
  deliverable's purpose is to replace Fable re-exploration with cheap
  verification — Fable tokens are the scarce resource; codex context is not.
- Brief↔code drift (multi-session reality) is severity-typed (the inline
  protocol below is the current rule; origin = archived PC2-era
  §Design-Ledger Drift Protocol): location-only drift
  (premise holds) → re-pin coordinates and report; premise-breaking drift →
  STOP and return a delta packet (brief assumption quoted vs current
  evidence, options, no improvised redesign). Unsure ⇒ treat as
  premise-breaking.
- Evidence gathering declares its own boundary: dossiers carry a
  search-frontier ledger (what was swept with which commands; what was NOT
  swept + stop-rationale; no silent caps) and an unpursued-questions list.
  Listing an unpursued question is never a penalty — silently omitting one
  is the failure mode. Expect designer supplement rounds; they are the
  normal loop, not a rebuke.
- **Never close satisfied — standing duty of audit/falsifier roles (user
  decision 2026-07-31)**: an agent hired to falsify or audit holds its
  instructions to the maximum bar — one or two findings are a reason to hunt
  siblings, not to wrap up, and before reporting it thinks once more about what
  one more pass would surface. Why: its context-acquisition cost is already
  paid; closing early destroys that asset and makes the next fresh hire pay it
  again (evidence: BP-145 / ADR-673 r22–r25). The duty lives in the role surfaces themselves
  (`.codex/agents/falsifier.toml`, `.codex/agents/closure.toml`,
  `.claude/agents/closure.md`) — packets need not restate it. Exhaustive
  devices (authority enumeration, dataflow audit tables) are tools a packet may
  specify, not a standing obligation. Fresh spawning between rounds stays
  unchanged (independence device) — this deepens what one hire exhausts before
  closing. Hirer-side mirror: **dispatch work with a
  high acquisition cost so one hire exhausts it deeply** — re-tasking an
  already-briefed agent is cheaper than a new hire; shallow multi-hire
  round-trips pay the startup cost repeatedly (fresh spawns for independence
  are the exception; user-adopted). Twin: `.claude/rules/delegation.md` §만족-종료 금지.
- **PC2 operation CLOSED permanently (user-confirmed 2026-06-25).** The producer,
  the absorption poll, and every PR-absorption / notify / issuance lane are
  inactive. **PC2 is not coming back — assume no revival**; no future work treats
  PC2 as operating. Closure and retired-lane detail SoT =
  `@docs/fable_to_opus_260613/PC2-OPERATION-CLOSED-2026-06-25.md`.

Twin note: the Claude-side restatement lives in `.claude/rules/delegation.md`
(Tool And Delegation 상세 + PC2 레인 — CLOSED; CLAUDE.md §Tool And
Delegation 은 좌석 정책 + 포인터만) (cross-audience twin — keep meanings in sync; see
`@docs/adr/340-coding-agent-instruction-surface-governance.md`). A Claude main
session is in boss mode **by default**, and that posture's operating-sense text
lives in the same file (`§사장 운영 감각`). Current lane map: tier-1 Opus employee
one-shot / tier-2 = Codex deputy boss only / VP = fresh Codex one-shot on the
wrapper's `vp-*` role model (ADR-872 D4 trial); the Codex
`### 사장 모드 (Boss Mode)` contract above is unaffected.

### Claude-Coder MCP Calls

When using the Codex `claude-coder` MCP tools, omit `bare` or set `bare:false`
in this OAuth/Max setup. Claude Code `--bare` skips OAuth/keychain auth and
requires `ANTHROPIC_API_KEY` or apiKeyHelper auth; the local MCP server rejects
`bare:true` unless `CLAUDE_MCP_ALLOW_BARE=1` is explicitly configured.

### 사장 모드 (Boss Mode)

When the user asks for `사장모드` / `사장 모드`, explicit subagent-backed
orchestration, or a subagent-backed task list, main acts as orchestrator: frame
the goal, decision boundary, source of truth, risks, and done condition; keep
the critical path moving; delegate bounded work; integrate or override subagent
results. A standalone VP-consult request triggers that consultation only, not
full Boss Mode. Do not ask the user to paste the long `/goal` prompt — infer the
objective from the active request.

The orchestration methodology — default flow, closeable lanes, saturation loop,
authority model detail, role defaults, agent hygiene, session shape — is owned
by `@docs/user-agent-communication/boss-mode.md`; read it when Boss Mode
activates. Boss Mode can run in ordinary chat or inside `/goal`; goal mode owns
state custody through `@docs/user-agent-communication/goal-mode.md`
(`comments.md` live packets, `goal-state.md` index, `goal-runs/*.md` run files).

Goal-packet queue: `docs/goal_packets/` holds pre-authored rulebook+ledger
packets for long codex goal-mode loops (standard:
`@docs/goal_packets/CLAUDE.md`). When a registered goal points at a packet, the
packet's Goal Comment and rulebook are the operating contract and the ledger is
the sole run state — do not create a parallel `goal-runs/*` file for a packet
loop. Wake discipline (per-wake round procedure, terminal close on
completion+saturation, blocked instead of invented work, ledger-only progress)
binds through the Goal Comment because it is the only text that survives
compaction.

Always-loaded invariants (ADR-340 D7 governed twin, with its edit-boundary item
partially superseded by ADR-553 — keep in sync with the Claude twin):

- **Authority**: main is the only owner of task ordering, risk acceptance,
  approval requests, and final user-facing synthesis. Subagents are advisory
  inputs — convergence is not authorization, and no subagent holds
  approve/reject/completion authority.
- **Decision-class**: user decisions are policy (including permissions), scope
  creep, safety, risk acceptance, large dependencies, public-contract changes
  (including default-route changes, cutovers, and retirements), durable
  schema/storage decisions, live-model quota/runs, and data-loss-capable work.
  Main(+VP) may decide implementation design knobs such as location, wording,
  revision IDs, and lifecycle-hook placement. After a durable schema/storage
  decision is approved, authoring its mandatory companion migration remains an
  implementation artifact under §Testing. Production/external applies,
  destructive data changes, and broad backfills always escalate to the user.
- **Advisor cap**: after two advisory answers on the same decision, the next
  action is a main decision, user ask, worker packet, verification gate, or
  explicit park. A different named surface is a follow-up; the same question
  repeated is an advisor loop.
- **Completion claim**: worker green / map-clean / focused-test pass is
  evidence, not completion. When live-state, runtime, parity, or security
  evidence decides correctness, use a falsifier-style review before closing.
  Main reviews worker output, spot-checks the decisive path, and owns the close.
- **Execution capability and mutation scope**: Claude, Codex, mains, and
  subagents are full-write-capable by default. Caller direction, role name, or
  Boss/goal mode does not create a read-only or worker-only permission tier.
  The active request controls mutation: a review/report/diagnosis or explicit
  no-edit request remains non-mutating, while an implementation request may be
  executed directly by main or delegated. Delegation is leverage for volume,
  independence, or verification—not authorization to write. Dev/simulation DB
  rows remain agent-owned inside a bounded task (keep snapshot/readback
  evidence); production/external applies, destructive changes, and scope
  expansion still follow the user decision class above. Full bullets:
  `@docs/user-agent-communication/boss-mode.md` §Execution Capability And
  Mutation Scope (ADR-553).

Park only for a concrete blocker — missing user decision, required approval,
unavailable external state, destructive or hard-to-reverse boundary, explicit
scope conflict, or a saturated investigation with a recorded reopen trigger.
Large or hard work is not a blocker by itself. Keep agent hygiene: close
completed/stale workers before spawning more; the run file owns durable summary.

### Codex Project Subagents

This repository has project-local Codex agents under `.codex/agents/`. Each
agent TOML owns its live model/reasoning configuration; inspect those fields
instead of freezing the values in prose. Treat the custom roster as decision
leverage, not volume delegation. Use local commands, focused reads, and tests
directly for routine reconnaissance when they are cheaper than a sub-agent call.

There is no roster routing role (ADR-872 추기 (8)): main
routes, because the assignment rule is one list — everything outside "Luna 가 안
되는 자리" is Luna. Delegation chains are Codex-only — do not route
VP/design-review or worker work to Claude/Opus on your own initiative: Claude in
the chain has lifecycle/wake friction (detached/background Claude completion has
no Codex wake; the direct `claude-coder` MCP is a synchronous tool call, not an
autonomous background carrier; Claude background sub-agents get no auto-wake),
so chained turnaround is unreliable (user decision 2026-07-05). Cross-model
Claude review is not a worker-chain carrier; it follows the separate
`Design Review Channel` gate (explicit user request or a material Codex-led Boss
Mode VP/design-review decision). Do not spend a sub-agent call (the routing
question itself lives in `open_cognition_partner`) when the next step is
obvious, local, reversible, already constrained by the user, or cheaper to check
directly. All advisors are advisory; the main session owns integration, risk
acceptance, final judgment, and user-facing synthesis.

When a VP recommends another agent, frame it with the `Delegation
packet contract`. Prefer one agent. Use two only when scopes are independent and
both calls can change the next decision.

Subagent calls do not require user approval by themselves. Ask the user only
when the call or resulting decision changes goal/scope, durable policy,
architecture, public API, safety behavior, permissions, new dependencies,
services, storage, data-loss/destructive behavior, DB/storage boundary beyond an
approved product/storage boundary, or major user-visible behavior.

Delegation packet contract: each delegated task needs owned scope, write or
decision boundary, expected return shape, stop condition, and verification
signal. Do not duplicate main-session work or let workers widen ambiguous scope.
If the structure is incomplete, ask the worker for evidence and options instead
of letting it guess.

**Subagent 대기 규율 — 강제 기본값 (사용자 결정 2026-07-14, 단위 30분 통일 2026-09-15):** Codex
subagent 를 dispatch 하거나 다시 trigger 한 뒤 구체적인 개입 사유가 없으면 main 은
`wait_agent` 를 반드시 **30분 단위**(`timeout_ms: 1800000`)로 호출한다 — 60분은 쓰지
않는다: 사장 모델(sol) 프롬프트 캐시가 직전 호출 뒤 35~40분부터 죽기 시작한다(40–45분
cold 19%·45–50분 27%, 주간 더 나쁨; 자식 활동은 부모 캐시를 데우지 못한다 — 실측 =
`docs/report/pytest-consumption-and-deputy-wall-2026-09-15/deputy-cache-ttl-curve.md`).
`wait_agent` 는 대상 지정이 없는 wait-any 라 어느 자식이든 mailbox 갱신이 오면 즉시 깬다
(실측 91% 조기 반환) — 30분은 소식 없을 때의 최대 차단 길이지 결과 지연이 아니다.
**상시 5분 polling/wake 는 금지한다.** tool 의 더 짧은 기본 timeout 을
그대로 쓰지 않는다. 새 evidence 없이 timeout 된 것은 ping·interrupt·
짧은 polling 전환의 사유가 아니다. 다시 30분 wait 한다. “곧 끝날 것 같다”는 예상도
짧은 wait 의 사유가 아니다. 30분 미만 wait 는 user 가 명시적으로 요청했거나, 이미
예고된 30분 미만의 외부 event 에 맞춰야 하는 구체적 사유를 main 이 기록한 경우에만
허용한다. 단순 status 확인을 위해 worker 에 message 를 보내지 않는다. 이 규칙은 Boss
Mode, goal loop, 작은 사장, 구현 worker, advisor, falsifier, closure 를 포함한 모든
Codex subagent lane 에 적용한다.

**기계 하한 (사용자 결정 2026-07-23):** project-local `PreToolUse` hook
`@.codex/hooks/wait_agent_timeout_guard.py`는 `wait_agent.timeout_ms`가 생략됐거나
`600000`(10분) 미만이면 호출을 실행하지 않고 차단한다. 에이전트는 오류를 받은 뒤
정상 기본값 `1800000`(30분) 이상으로 명시 재호출한다. 이 10분은 catastrophic
short-poll 방지 하한이지 정상 cadence가 아니다 — 위 30분 기본값과 30분 미만
예외의 명시적 근거 규율은 그대로 적용한다. 자동 인자 재작성은 의도를 숨기므로 하지
않는다. Hook 등록/계약 검증은 `@.codex/hooks.json`과
`@.codex/hooks/test_wait_agent_timeout_guard.py`가 소유한다.

Delegate volume work to Codex sub-agents: reconnaissance, source gathering,
long-output summaries, repetitive edits, implementation fill inside an explicit
task scope, parallel verification support, and first-pass drafts. The worker
default is Luna/max from `.codex/config.toml` `[agents]` (§Worker Principles owns
the black list and the Sol exceptions); Spark (`gpt-5.3-codex-spark`) is explicit
opt-in only, not a default or a fallback. Do not make main absorb volume work by
default; give a bounded worker owned scope, stop condition, and expected return
shape, then spot-check decisive evidence. Trust the output enough to move faster,
but spot-check the decisive evidence before committing to a design or patch. Do
not use Claude/Sonnet/Opus anywhere in a **Codex-carrier** delegation chain — as
staff or worker, including 작은 사장 deputy chains — because wake friction makes
chained completion unreliable; the only exceptions are an explicit user override
or work specifically about Claude behavior. (Scope note: this ban binds chains
whose carrier is Codex; the only Claude-side deputy is the journey-round-boss —
see §Worker Principles.)

Ask implementation workers for changed files, tests run, and remaining doubts,
not final completion claims. Use falsifier-style review to attack high-risk
completion claims before handoff when live-state, runtime, restart, parity, or
security evidence is decisive.

Use `closure` when the handoff risk is not only "is the claim false?" but
"did the lane finish its derivative work?" — doc criteria, SoT/ADR alignment,
dead-code fallout, worktree status, stale wording, and
verification gaps. `closure` is evidence for main judgment, not authorization.
Skipping the closure agent on a small code change skips the agent call, not
the audit (user directive 2026-07-10): main then walks the closure surfaces
itself in lightweight form — doc/SoT impact, dead-surface, worktree
separation, verification gap (incl. the §Testing red-gate), stale wording,
remaining packets, and cross-cutting registration parity (duties derived
from what the lane PRODUCED, not from its file list — new metric, shared-state
machinery, flag, prompt tag, production-path change each have a registration
home outside the changed files; kind table = `.codex/agents/closure.toml`
"Registration parity" section) — and records the result in the final report.
(Twin of `@.claude/rules/delegation.md` §"규모 있는 작업 마무리 = 감리 기본" clause.)

User call word: **감리**. If the user asks "감리 받았어?", answer only from fresh
equivalent closure evidence for the current lane or run closure first. If the
user asks "감리 돌려", run the relevant closure inspection for the current main
(Codex main: `closure`; Claude main: `/closure`), then answer with one
evidence-based verdict line. The verdict remains main judgment. Do not use
`Atlas` as this call word; it collides with worker naming.

When the user explicitly asks for Claude review, follow `Design Review Channel`
below. If an explicitly requested Claude review or required map/MCP check fails
because the local wrapper, proxy, MCP routing, auth/session cache, or
command/config path is broken, repair the tool path first (when the active
request authorizes that infrastructure scope), then rerun the same required
check. Do not convert missing evidence into a green result.

