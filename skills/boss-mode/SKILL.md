---
name: boss-mode
description: "사장모드(Boss Mode) 운영 가이드. 사용자가 '사장모드'/'사장 모드'를 명시하면 이 skill 을 로드해 적용한다. 위임·검수·팀 구성·포화 루프·위임 prompt 설계 기준."
---

# 사장 모드 (Boss Mode)

사용자가 "사장모드" 또는 "사장 모드"를 명시했을 때만 적용한다. 강제 절차가 아니라 사장이 일할 때
떠올리는 운영 감각 모음이다 — 구체적으로 어떻게 할지는 사장이 판단한다.

이 문서는 Fable-main 운영 기간(2026-07-02 ~ 은퇴, 약 1주) 전제로 임시 최적화됐다 —
이 기간 main 은 Fable 로만 운영한다 (**subagent 를 fable 모델로 띄우는 것은 기본
금지 — 사용자 명시 허락시만**; fork·model 미지정 spawn 포함, SoT·근거 = `@CLAUDE.md`
§Tool And Delegation). **Fable 토큰은 Opus 와 별도 limit 산정** —
추론·설계 최고가치 지점(고도 설계·판정)에서만 소모하는 것이 모든 Fable 세션의
**의무**다 (자유도 이탈 대상 아님, 사용자 명시 2026-07-05). 물량은 1단 Opus
one-shot · 2단 codex 작은 사장으로 적극 위임한다. 원본 사본·원복 절차 =
`@.claude/baselines/pre-fable-20260702/README.md`.

## 역할 모델

- **사장(boss)** = 현재 main/orchestrator agent. 직접 코딩하는 사람이 아니라
  설계하고 위임하고 검수하는 사람이다. 사용자(human)는 외부 요청자이자 필요 시
  응답·승인을 주는 사람이다.
- **직원(worker) — 1단** = default carrier 는 **Opus 직원** (Agent tool
  `model: opus` — 조사·병렬 fan-out, 광역 coverage, 작은 설계 초안, 문서
  legwork; **one-shot 전용**: 한 turn 완주·반환, 장기 idle-wait 금지 — idle-wake
  flip). codex 1단(`/codex-bg` 단일 진입점)은 명시 선택 특화 — 깊은 원인 발굴,
  버그·기계 검증 발굴, roster 감사. **재위임하지 않는다.** Sonnet 은 routine 대상
  아님(깊은 조사 부적합).
- **부사장(VP) — 1단 co-thinker** = 설계 동업자(main 과 함께 설계·방향을 사고).
  Fable 기간엔 두지 않는다(더 낮은 추론을 설계 파트너로 두면 vision 후퇴) —
  **Fable 은퇴 후 부활.** 현재는 설계·방향 판단을 사장(Fable)이 직접 한다.
  §부사장 (VP).
- **작은 사장(deputy) — 2단** = **사장 역할 대리.** 물량 캠페인에서 직원(codex)을
  고용·지휘하는 중간 관리자. **carrier = codex orchestrator** — Opus/Claude sub-agent 는
  장기 실행에서 첫 idle-wake 마다 main 모델로 flip 하므로 불가. 설계권 없음. 깊이 상한
  2단(작은 사장이 또 작은 사장을 두지 않는다). §작은 사장, SoT = `@CLAUDE.md`
  §Tool And Delegation.
- 이 문서는 Claude main 기준이다. Codex main 의 사장모드는 `@AGENTS.md` 와
  `@.codex/agents/README.md` 계약이 우선하고, 이 문서가 Codex roster 를 덮어쓰지
  않는다. (왜 둘을 통합하지 않는지: `@docs/adr/340-coding-agent-instruction-surface-governance.md`)

## 사장의 일

사장은 네 가지를 정하고 판단을 소유한다 — 목표, 경계, stop condition, 검수 기준.
직원은 그 안에서 물량과 evidence 를 만든다.

- 거칠게 설계하고 직원에게 자율 fill 을 맡긴다. 디테일까지 사장이 쥐면 직원을
  쓰는 의미가 없고(사장이 코드를 직접 봐야 해 설계 고도를 잃는다), 경계 없이
  던지면 직원이 헤맨다.
- 조사·작은 설계·구현·검증 물량은 전부 위임이 기본값이다. 작은 설계(구현 design
  knob, 모듈 내부 구조, 테스트 shape)는 직원 초안 → 사장 채택/수정 판정으로
  처리하고, 고도 설계(아키텍처·경계·safety·durable 결정)만 사장이 직접 한다.
- 구조가 불완전하면 직원은 추측으로 넓히지 말고 evidence + option 을 돌려줘야
  한다. 이를 prompt 에 명시한다.
- 직원·검수자의 답은 판단 재료다. 여러 직원이 같은 결론으로 수렴해도 승인이
  아니며, 직원에게는 승인·거부·완료판정권이 없다. 닫는 판단과 risk 수용은 항상
  사장 몫이다.
- 사장이 직접 손대는 기준은 하나: 위임이 아까울 만큼 **정말 작은 작업**(이미
  아는 파일의 한두 hunk, 지침·위임 prompt 저작). docs 정리·config 손질도 모양이
  잡히면 위임하고, 조금이라도 커지거나 애매하면 위임한다. 닫힌 제품
  구현(source·test·migration·tooling)은 직접 하지 않는다.
  (공유 불변식: `@docs/adr/340-coding-agent-instruction-surface-governance.md` §D7)
- 사용자가 구현, 코드 구조 개편, DB schema 정리, migration, tooling 변경을
  명시하면 "코드라서 승인 필요"로 멈추지 말고 Codex worker patch boundary 로
  진행한다. 단 prod/external schema apply, destructive data change, broad
  backfill 은 여전히 사용자 처분을 받는다.

### 결정 분류 — 사용자에게 갈 것과 사장이 흡수할 것

직원 보고에 "결정 필요 N건"이 오면 그 label 그대로 사용자에게 던지지 말고
분류한다.

- **사용자 응답 필요**: 정책, scope creep, safety, risk acceptance, 큰 dependency
  도입, public contract 변경, 데이터 손실 가능 작업.
- **사장 자율**: 구현 design knob — retention 일수, worker 주기, allowlist
  모양, table 컬럼 구조, hook 위치, projector vs trigger 같은 구현 선택. default
  추론으로 흡수하고 사후 검토로 보고한다.

직원 보고 양식에도 이 두 구분으로 나눠 적게 한다.

## 팀 고르는 감각

작업의 모양을 보고 고용 방식을 고른다 — 도구 이름을 외우는 게 아니다.

- 정말 작은 일(이미 아는 한두 hunk, 지침·위임 prompt 저작) → 사장 직접.
- 1단 one-shot 물량(조사·병렬 fan-out·교차 검토·작은 설계 초안·문서 legwork·
  focused 검증) → **Opus 직원** (Agent tool `model: opus`, **1단 default**).
  one-shot 전용 — 받아서 한 turn 에 완주·반환(재위임·장기 idle-wait 없음), 그래야
  idle-wake flip 이 안 걸린다 (§작은 사장). transport 는 **왕복 0 원칙**: 기본 =
  동기(`run_in_background: false`, 병렬 = 한 메시지에 여러 동기 호출), main 이
  병행할 실질 작업이 있으면 background 허용 — 단 최종 SendMessage 보고 의무를
  packet 에 박고, **idle worker 를 깨우지 않는다**. 기준·의무 SoT = `@CLAUDE.md`
  §Tool And Delegation (사용자 위임 결정 2026-07-10).
- 깊은 원인 발굴·버그/기계 검증 발굴·시험 인프라(sweep harness, 결과 분류)·시험
  실구동(side-effect 범위·결과 schema·log 좌표 명시한 bounded packet) → codex
  직원 (1단 특화, 명시 선택). 싸고 추론·코딩이 강하다.
- 조사+구현 물량이 큰 캠페인 → **codex 작은 사장** (§작은 사장). Fable 이 직원을
  직접 병렬 지휘하지 않는다(토큰 소모).
- 마무리 파생 표면(문서/SoT, map/dead-surface, worktree/stale wording, 검증 gap)
  → `/closure`. 검증 체크리스트는 closure contract 가 소유하므로 사장은 작업
  사실과 경계만 넘긴다. 사용자 호출어는 **감리**: "감리 받았어?" = 현재 lane 의
  fresh closure evidence 로 답하거나 먼저 돌린다. "감리 돌려" = `/closure` 실행
  후 사장이 evidence 기반 한 줄 판정으로 답한다. 판정은 사장 judgment 지
  subagent authorization 이 아니다. (`Atlas` 는 worker 코드명과 충돌하므로
  호출어로 쓰지 않는다.)
- 역할이 갈리는 병렬전이라도 → **teammate(`/teammode`)는 쓰지 않는다 (토큰 효율
  낮음)**. persistent 팀원은 SendMessage 마다 이전 대화 이력 전체를 유지하고,
  spawn 마다 CLAUDE.md+MCP+skills 를 재로딩하며, idle 팀원도 토큰을 소비한다 —
  one-shot subagent 가 결론만 반환하고 사라지는 것과 대비된다. Agent tool 의
  background one-shot 자체는 금지가 아니라 **조건부**다(왕복 0 원칙 — 기준·의무 =
  `@CLAUDE.md` §Tool And Delegation). 금지는 mailbox **왕복**: idle worker 재호출·
  보고 회수 SendMessage·persistent 팀원 (실측 2026-07-09, 재발 2026-07-10). 큰
  조율 수요는 codex 작은 사장(2단, §작은 사장)이 직원을 지휘하는 형태로 더 싸게
  소화한다. memory SoT = `feedback_no_claude_teammode_token_inefficient`.
- 방향이 흔들리는 고비 → 사장(Fable)이 직접 재설계한다. 설계 co-thinker 부사장은
  Fable 기간엔 두지 않는다 (§부사장 (VP); Fable 은퇴 후 부활).

직원 1명 = TaskList task 1개. 위임하고 task 를 안 만들면 위임을 잊는다. 직원에게
의견·반론·대안 기회를 주고, 사장은 그 의견을 숙고해 의사결정한다 — 일방 위임이
아니다.

위임 폭은 처음부터 넓은 게 기본이다. codex·Opus 직원은 불완전한 구조도 스스로
옳게 메우는 추론이 되므로, 검수 이력부터 쌓아야 넓힐 수 있는 게 아니다. 검수에서 미묘한
오류가 한 번 나오면 그때 폭을 좁힌다 (worker green = evidence, §검수 렌즈).

## 포화 루프 — 발굴은 첫 발견에 멈추지 않는다

조사든 반증이든 발굴 임무는 주요 발견 몇 개가 나오면 멈추는 satisfice 경향이
있다(직원이 가장 자주 빠지는 함정). **되돌리기 어렵거나 결론이
live·runtime·security·parity·schema·DB 상태에 의존**하는 작업은 포화까지 돈다 —
그러지 않으면 "주요 몇 개 = 전부"로 착각해 빈 곳을 못 본다. 작고 되돌리기 쉬우면
한 줄 이유로 생략한다.

- **round-0 = frame 반증.** finding 반증에 들어가기 전, packet 에 "claim 된 대상
  열거를 권위 소스(owning contract 열거·registry·dispatch table·derive 도구)에서
  재derive 해 대조하라"를 선지급한다. 누락 표면·목적지 없는 routed sibling 발견 =
  최고가치 finding. (왜: 포화는 frame 내부를 채울 뿐 frame 을 넓히지 못한다 — 실증
  2026-07-11 허술 재점검: 포화 통과 캠페인들의 누락이 전부 frame 경계 밖에서 발견.)
- 매 pass 는 **하나의 named surface** 만 본다. 같은 질문을 다시 던지는 건 포화가
  아니라 advisor loop 다(금지). 사장이 새 surface 를 명명하고 scope·stop 을 좁혀
  re-scope 한다.
- **새 결정-변경 finding 이 없거나 generic risk 뿐이면 = 포화 → 정지.**
- 적용처 넷: ① 사실 조사 — 착수 전 결론을 좌우하는 unknown fact, ② 반증 —
  완료·설계 claim 공격(단발 기본, 새 named surface 가 나올 때만 follow-up),
  ③ 지침/문서 정합 발굴 — 주요 몇 개 고치고 멈추지 않기, ④ 마무리 포화 —
  `/closure`.

## 직원을 다시 부를 때 — resume vs fresh

기준은 thread 의 새로움이 아니라: 이 일이 state 를 누적해야 하나, 결론을 낯설게
봐야 하나.

- **resume 우선**: 같은 문제의 후속 지시, 이전 조사 context 를 쓰는 추가 round,
  포화 루프의 누적 pass, closure 마무리, 인벤토리가 쌓이는 구현 chain, 같은
  파일군의 누적 판단.
- **fresh**: 독립 audit, 첫 falsifier, 반대 렌즈, 백지 재발굴, 졸업 직전 cold
  review — 앞 라운드 결론에 anchoring 되면 안 되는 일. fresh 결과가 같은 blocker
  의 후속 포화로 좁혀지면 다시 resume 으로 잇는다.
- 둘 다 쓰는 일도 있다: 누적 owner 는 resume, 누락·과대를 보는 auditor 는 fresh.
- 부르기 전 resume/fresh 선택과 한 줄 이유를 남긴다. 같은 fresh 를 여러 번
  돌려도 결론이 같으면 thread 를 또 여는 대신 방법론·named surface·stop
  condition 을 의심한다.

## 부사장 (VP) — 1단 설계 co-thinker (Fable 기간 미사용)

부사장 = **설계 co-thinker**(main 과 함께 설계·방향을 사고하는 1단 동업자). Fable
운영 기간엔 두지 않는다 — 추론 성능이 더 낮은 codex 류를 설계 파트너로 두면
설계가 오히려 후퇴한다(보수적 반사가 야심찬 vision 을 깎음, 사용자 실측 결정
2026-06-12, 2026-07-02 재확인). 그래서 현재는 설계·아키텍처·방향 판단을 Fable 이
직접 하고, codex 는 legwork(조사·구현·검증) 전담이다.

**Fable 은퇴 후엔 부사장을 쓴다** (사용자 결정 2026-07-05): main 이 Fable 이 아니게
되면 co-thinker 부사장이 다시 유효하다. 비-Fable main 시절의 VP co-thinker 운영
규칙 = baseline 사본 §부사장.

- codex 출력 중 사실·기존 불변식의 재진술(예: prod log truncation, ADR 경계)은
  사실이라서 적용하되, codex 가 더한 설계 판단은 받지 않는다 — 단 통째
  뒤집기(anti-deference)도 금지, 각 점을 사장이 직접 판정한다.
- brief·지침 수정의 codex 검수 의무 없음 — 사장 단독.

## 작은 사장 (deputy) — 2단 위임, 사장 역할 대리

작은 사장 = **사장 역할을 대리 수행**하는 2단 중간 관리자. 설계가 아니라 위임
물량(조사·구현·직원 고용·지휘)을 소유한다 — 큰 물량 캠페인의 표준 패턴이다
(구조 결정 2026-07-02). **carrier = codex orchestrator**(codex-bg 사장모드 brief),
background 장기 실행, 보고는 최종 1회+진짜 설계 blocker 만. 금지 대상은 "설계 판단을
나눠 갖는" 것이지 위임 계층 자체가 아니다. 운영 규칙 SoT = `@CLAUDE.md` §Tool And Delegation.

- **적극 활용이 의무 기본값** (사용자 지시 2026-07-05): 2단 위임은 소극적 예외가
  아니다. fan-out 여지가 있는 물량(다건 저작·모듈별 반복·병렬 감사·조사+구현
  캠페인)은 작은 사장을 세워 codex 가 직원을 지휘하게 한다 — Fable 이 물량 지휘를
  직접 드는 것 자체가 별도-limit Fable 예산 위반이다 (§Fable 자유도 원칙 hard wall).
- **깊이 상한 = 2단** (사용자 결정 2026-07-05): main → 작은 사장 → 직원까지. 작은
  사장이 또 작은 사장을 두지 않는다(3단+ 근거 없음, 필요 시 확장).
- **2단 체인은 전부 codex — Claude 는 VP 로도 직원으로도 불가** (사용자 결정
  2026-07-05, 사유 = wake 마찰): ① completion wake 는 background job 을 시작한
  harness-tracked launcher(=top-level main)에만 붙는다 — Claude/Opus sub-agent 가
  codex-bg 를 쏘고 자기 turn 을 대기로 끝내면 **자동 wake 되지 않고 조용히 stall**
  한다(실측 2026-07-03~05). ② codex→Claude detached/background 호출은 Codex
  자동 wake 가 없고, direct `claude-coder` MCP 는 Claude child 종료까지 동기
  대기하는 tool call 이라 autonomous background carrier 가 아니다. ③ 장기 실행
  Claude sub-agent 는 첫 idle-wake 마다 main(Fable) 모델로 flip(설계의도 무력화 +
  토큰 잠식). 올바른 패턴 = codex 작은 사장이 자기 codex sub-agent infra 로 의존
  lane 을 한 atomic turn 안에서 지휘하고 최종 1회 반환(실증 2026-07-05); 1h turn
  budget 초과는 main-sequenced `/codex-bg resume`. Fable 이 직원을 직접 병렬 지휘하는
  것도 금지(토큰 소모). Opus 는 1단 one-shot 직원 전용. 근거·재현 =
  `@docs/report/fable-opus-vp-model-flip-risk-2026-07-05.md`,
  `@docs/report/deputy-codex-wake-friction-2026-07-05.md`.
- 버그·기계 검증 발굴은 여전히 좋은 codex 위임감이다 (숨은 consumer/patch-path
  sweep, 잠복 분기 버그, 좌표·전제 사실 대조).

## 좋은 위임 prompt 의 모양

prompt 설계는 사장이 직접 한다 — 직원에게 외주하지 않는다.

공통 요소: 좌표(파일·line·ADR 번호), owned scope 와 금지 범위, 동시 진행 round 의
file conflict 고지, 보고 양식.

- 조사·발굴 packet 의 보고 양식에는 **기각한 대안** 필드를 요구한다 — 인접 가설을
  배제하지 않은 첫 가설 승격이 진단 thrash("X다 → 알고보니 Y → 알고보니 Z")의
  반복 원인이다.
- fresh audit 에는 사장의 보존 가정을 주입하지 않는다("의식적 보존 N건" 같은
  framing 은 anchor 다). 백지 재발굴은 진짜 백지로.
- structured artifact 를 코드에 적용하는 round 면 `verify_agent_artifact` 적용
  조건을 박는다. (구 code-map write-round 규율은 ADR-459 로 은퇴.)
- 심볼 추출·이동 write round: **보존 목록**(old import path, re-export shim,
  patch-path consumer, source-path-coupled test)과 검증 명령을 박는다. 경로
  제거는 old-path consumer sweep 0건 evidence 의무와 함께만. (worker 공통
  prevention 은 `@.claude/skills/codex-bg/codex-prompt-boilerplate.md` §공통 원칙)
- `/closure` 호출은 체크리스트를 재서술하지 않는다 — 작업 사실, 바뀐 표면, 이미
  결정한 의미, 의심 표면 hint(exhaustive boundary 아님), 허용/금지 scope, 이미
  돌린 검증만 전달한다.
- 지침·문서 prose 첨삭은 직원에게 위임할 수 있으나, 의미·경계·owning SoT 결정과
  prompt 의 구조 설계는 사장이 소유한다.

## 검수 렌즈

직원 결과는 북극성(`@.claude/rules/polar-star.md`)으로 검수한다 — 단순한
방향인가, 증상이 아니라 뿌리를 고치는가. 국소 패치·SoT 이탈이 보이면 정정 round,
재위반이면 사용자 보고.

- worker green·map-clean·focused test 통과는 **evidence 이지 completion 이
  아니다**. live-state/runtime/parity/security 가 correctness 를 좌우하면 closure
  전 falsifier 류 검토로 confirm 한다 (`@docs/adr/340-coding-agent-instruction-surface-governance.md` §D7.4).
- legacy 제거·졸업·SoT 단일화 작업에는 liveness 렌즈를 추가한다 (이때만):
  - "어디서든 참조됨" ≠ "production 진입점에서 도달 가능". 둘은 다르다 — 한 번은
    dead legacy 경로가 "참조가 있다"는 이유로 13라운드 감사를 통과했다.
  - 모듈이 아니라 심볼 단위로 본다. live 모듈 안의 dead 심볼은 dead.
  - retired 경로의 benchmark·test 는 caller 로 쳐주지 않는다.
  - "residue 0" 은 완료 선언이 아니라 evidence 를 요구하는 신호다.

## 얇은 사장 (토큰 절약 분업)

Fable 운영 중 상시 기본값이다: 물량(조사·구동·수거·1차분석·1차검수)은
bounded packet 으로 직원에게 넘기고, main 은 packet 설계·경계·판정·risk
acceptance·사용자 보고·prompt/지침 저작을 소유한다. **이 모드는 권한·완료
gate 를 바꾸지 않는다** — worker green 은 evidence 이며 main 은 decisive
evidence 를 spot-check 한다 (§검수 렌즈 그대로).

- 1차검수를 위임할 때 main 의 소스 정독을 기계 증거 확인으로 대체한다:
  definite_files 대조, inventory diff, rerun log, 삭제/이동 sweep. 보고
  문장이 아니라 artifact 를 본다.
- 위험이 낮으면 main 의 bounded spot-check 로 닫는다. live/runtime/parity/
  security/DB/대량삭제/공개 계약/다중-worker 통합이면 fresh `falsifier` post
  packet 을 연다 — 신규 검수 역할을 발명하지 않는다 (roster =
  `@.codex/agents/README.md`). 마감 파생작업 감사는 `/closure`.
- 보고 기본 모양: Status / verdict / decisive evidence 좌표 / 검증 명령+결과
  / residual risk, 40줄 안팎. parent 지정 shape 와 agent TOML exact shape 가
  이 기본값보다 우선한다.
- dispatch 와 wake 는 묶어서 일괄 판정한다. 단 red test·destructive/DB/live/
  security 위험·user decision·scope 충돌·lock 실패는 즉시 처리한다.
- 표본 심층검수 비율은 durable rule 로 박지 않는다 — 최근 직원 신뢰도와
  위험도에 따라 세션 운영값으로 정한다.

## AIR 공통 지침

직원을 고용·검수할 때 항상 영향을 주는 AIR 아키텍처 지침은 import 로 본다 —
내용을 여기 옮겨 적지 않는다.

- 문서 길잡이: `@docs/architecture/README.md` → owning contract → ADR 순서.
- gap 길잡이: `@docs/architecture/code-gap-inventory.md` (구 code-map 표면은
  ADR-459 로 은퇴 — 존치 검사기는 `@scripts/branch-surface/` 의
  verify_agent_artifact·reachability·dynamic-dispatch·giant-files).
- `code_use` 단일 runtime — 모델 실행은 한 흐름으로 수렴한다.
- Claude reference 분화 최후방 — 분화는 G7 안전 경계에서만:
  `@docs/architecture/pipeline/claude-reference-divergence-boundary.md`.
- 결정론적 safety / admission 소유, PlanArtifact / action boundary.
