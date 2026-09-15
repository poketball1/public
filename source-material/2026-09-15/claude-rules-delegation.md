# Tool And Delegation — 위임 운영 규칙

이 파일이 위임 운영 규칙의 SoT 다 — `@CLAUDE.md` §Tool And Delegation 은 좌석 정책만
두고 여기를 가리킨다. Codex-audience twin = `@AGENTS.md`
§Tool And Delegation·§Worker Principles — cross-audience 동기 규율 =
`@docs/CLAUDE.md` §cross-audience.

main 좌석은 Fable 기본·Opus 병행이며 행동 양식·운영 lane 은 모델 무관 동일하다
— 좌석 정책·Fable 판단 필요 신호 3종의 SoT = `@CLAUDE.md` §Tool And Delegation
(사용자 결정 2026-07-27). 이 파일의 "main(Fable)" 표기는 좌석(사장 자리)
서술이지 모델 제한이 아니다.

**Fable 은 main 전용이다 — subagent 를 fable 모델로 띄우는 것은 기본 금지이며,
사용자 명시 허락 시에만 가능하다** (사용자 결정 2026-07-12). fable subagent =
별도-limit fable 토큰을 위임 물량에 소모 = 아래 토큰 hard wall 위반. 위임은 Opus
직원·codex·sonnet lane 으로만 한다 (closure 등 agent 정의는 이미 `model` 을
pin 한다). Agent tool 의 `subagent_type: "fork"` 는 model override 를 무시하고
부모 모델을 상속하므로, fable-main 세션에서의 fork·model 미지정 spawn 도 이 금지에
포함된다 — 명시 허락 전까지 쓰지 않는다. **기계화**: `.claude/settings.json` 의
`CLAUDE_CODE_SUBAGENT_MODEL=opus` + `deny Agent(subagent_type:fork)` 가 생략·fork 두
누수를 구조로 닫아, 명시 `model: fable` 만 산문 금지(사용자 허락 경로)로 남는다.
`deny Agent(model:fable)` 은 쓰지 않는다 — model 을 생략한 호출을 못 잡는다.

**Fable 토큰은 Opus 와 별도 limit 로 산정되는 희소 예산이다** — 추론·설계 가치
최대 고도에서만 소모한다. 이건 조정 가능한 기본값이 아니라 **모든 Fable 세션의
의무**다 (사용자 명시 2026-07-05; §Fable 자유도 원칙 hard wall — 자유도 이탈
대상이 아니다). 다만 이는 권한벽이 아니다. Claude·Codex·main·subagent 는 역할과
호출 방향에 관계없이 full-write-capable 이고, 실제 수정 여부는 active request 가
결정한다. review/audit/no-edit 요청은 full capability 에서도 수정하지 않으며,
구현 요청은 main 이 직접 수행하거나 위임할 수 있다(ADR-553). Fable 이 가장 먼저
주의를 쓰는 곳 = 문제 정의, 고도 설계(아키텍처·경계·safety·트레이드오프·durable
결정), 위임 packet 저작, 판정·risk acceptance, 사용자 보고. 조사·작은
설계·구현·검증 물량은 토큰 효율상 기본 위임한다 — 작은 설계(구현 design knob,
모듈 내부 구조, 테스트 shape)는 직원 초안 → Fable 채택/수정 판정. 직접 구현이 더
짧고 명확한 경우에는 main 이 같은 task scope 안에서 닫을 수 있다. 얇은 사장
분업(아래 §사장 운영 감각 ▸ 얇은 사장)은 기본값이다 — 단 권한·완료 gate 는 불변:
worker green 은 evidence 지 완료가 아니고, main 은 decisive evidence 를
spot-check 하며 불일치·flaky·고위험(live/DB/security/대량삭제) 표면은 직접
재검증한다. **규모 있는 작업 마무리 = 감리 기본** (사용자 결정 2026-07-05):
다파일·구조 변경·campaign 처럼 docs/map/dead-code/worktree 파생작업이 생기는
작업은 닫기 전 `/closure` 를 기본으로 돌린다 — 생략하면 한 줄 이유. **생략은
agent 호출의 생략이지 감리 항목의 생략이 아니다** (사용자 지시 2026-07-10):
소규모 판단으로 closure 를 skip 한 코드 수정 작업은 main 이 closure 표면을
직접 경량 self-check 한다 — 문서/SoT 영향 · dead-surface · worktree 분리 ·
검증 gap(§Testing red-gate 포함) · stale wording · 잔여 packet · **횡단 등재
parity**(변경 파일이 아니라 만든 산출물 종류에서 의무를 derive — 종류 표 SoT =
`@.claude/agents/closure.md` §Registration parity, 여기 복사하지 않는다) — 하고
결과를 최종 보고에 남긴다. falsifier
는 규모가 아니라 위험 트리거 유지(live/runtime/parity/security 가 completion
claim 을 좌우할 때, 아래 §사장 운영 감각 ▸ 검수 렌즈) — 규모-강제 시 합성 gap noise·비용만 는다.

운영 lane (사용자 결정 2026-07-25): ① **main(Fable) = 최대
추론 고도 우선**(설계·판정·packet 저작·보고), ② **1단 직원 default = Claude Opus
직원** (Agent tool `model: opus`), ③ **부사장(VP) = wrapper `vp-*`
역할 모델(Fable-급 codex)의 codex fresh one-shot** — 설계 반증·검토, **사용자 명시 호출만**
(ADR-872 D4; §부사장), ④ **2단 캠페인 = codex 작은 사장** (단일 carrier — §작은 사장).
②·④는 소극적 예외가 아니라
**적극 활용이 의무 기본값**이다 — 큰 물량을 Fable 이 직접 들고 있는 것은
별도-limit 예산 위반이며, 직접 편집 가능성 자체를 금지하는 뜻은 아니다. Claude
sub-agent 는 "오래 살며 기다리는" 자리에는 앉히지 않는다 — one-shot 은 안전하다
(근거 = 아래 §작은 사장의 wake 마찰 2개 + 왕복 0; 측정·처분 =
`docs/report/fable-opus-vp-model-flip-risk-2026-07-05.md` §재측정, CP-1648 A8).

**②↔④ 판별선 — 물량이 오면 어디로 가는가** (사용자 룰링 — ADR-872 추기 (6); **압력 =
Opus**): **1단 직원 = Opus 기본.** 조사·census·정독·
교차 검토·감리(closure·front-closure)·교차 family 반증·좌표 확정된 작은 구현은 1단 Opus one-shot 이다.
**codex 는 좌석 둘 — 작은 사장(2단)·VP** 이지 1단 직원이 아니다. 조사·구현이 **작은 사장 자리를 둘 만큼**
중규모 이상(다라운드가 도는 것 — 아래 전형 3종)일 때만 codex 작은 사장으로 보낸다; 애매하면 1단 Opus 로
시작하고 2단 필요가 드러나면 올린다. "one-shot" 이라는 이유만으로
1단이 되지는 않는다(100턴 이상 run 도 one-shot 이었다 — 다라운드 조짐이면 2단). 왜: **조사의 질이 설계 판정의
질로 이어진다** — Opus 직원 몫 상승은 감수하고 `claude_usage.py --by agent` 로 판독한다.
codex 작은 사장의 직원 기본 = Luna/max (규칙 본문 = §작은 사장). (근거·실측 =
`docs/report/claude-usage-opus-vs-fable-2026-09-07.md`, ADR-872 추기 (6); dial 이력 =
`@docs/ops/token-dial-ledger.md`.)
**2단이 값을 하는 전형 3종 (사용자 채택 2026-09-02 — 판단 신호이지 게이트가 아니다: 층 선택은
Fable 재량, §Fable 자유도 원칙 그대로. 전형 밖이어도 Fable 이 판정 turn 흡수 값이 있다고 보면
2단, 전형 안이어도 1단이 더 낫다고 보면 1단 — 한 줄 근거만 남긴다)**: ① 결과를 합쳐 다시
발주해야 하는 직원이 5명 이상 (정산 패스·골든 재녹화 파도·모듈별 sweep·여정 회차 — main 이
결과 다섯을 읽고 후속을 던지는 순간 Fable 토큰이 녹는다) ② **공용 상태 쓰기 권한을 주기로 한
작업** (§좋은 위임 prompt 의 권한 결정 = 곧 층 결정 — 동시성 결함이 라운드마다 형제로 나온다,
실측 ①5→3→2) ③ Fable 부재 중 수 시간 무인 완주가 필요한 캠페인 (codex 풀에서 혼자 돌고 판정
packet 하나로 귀환). 2단 = main 이 여러 번 들어야 할 판정 turn 을 대신 흡수하는 층이며, 그
값이 조율층 토큰이다. **2단 위생 2줄**: 사전 조사
직원 fan-out 을 두지 않는다(사장이 직접 읽거나 최대 1명) · 직원 결과는 파일로 받고 사장은 요약만 문맥에
올린다 (ADR-600 state 외부화의 사장판).

- **Opus 직원 — 1단 직원 default** (Agent tool, `model: opus`; 사용자 결정
  2026-07-25): **1단 one-shot 의 기본 얼굴 (압력 = Opus)** — 조사·census·
  정독·교차 검토·buggy 표면 발굴, focused 검증, 좌표 확정 국소 수정, 작은 설계 초안, 문서 legwork, 감리·교차
  반증 (§판별선 — 탐색도 작은 사장 자리가 값하지 않으면 Opus).
  의존·다라운드 fan-out 은 ④ 작은 사장 몫이다. 완료 통지 1회 회수(왕복 0)가 기본 이점이다.
  **Opus 자리 셋 (ADR-872 추기 (6))**: ① 1단 one-shot (기본 얼굴 —
  §판별선) ② closure·front-closure ③ Fable-급 사장 반환물의 교차 family 반증 1회(판정 로그 + 실제 효과).
  절반 원칙·균형 관측 = §두 병목.
  **one-shot 로만 쓴다** — 받아서 한 turn 에 완주·반환
  (재위임·장기 idle-wait 없음). 왕복 0 이 근거다.
  **transport 기준 = 왕복 0** (사용자 위임 결정 2026-07-10): 스폰은
  **항상 background** 다 — interactive 세션의 agent 스폰은 background 기본이고, Agent tool
  스키마에 `run_in_background` 파라미터가 없다(넣으면 InputValidationError).
  "왕복 0" 은 동기 호출이 아니라 **완료 통지
  1회로 결과가 닿는 것**이다: 병렬 = 한 메시지에 발주 여러 개, 회수 = 완료
  task-notification (main 이 별도 폴링·wake 없이 받는다). 사용자가 착석해 대화
  중이면 그 대화가 곧 병행 작업이다 — 직원 발주가 대화를 막지 않는다 (사용자 정정
  2026-08-27). ① **보고 의무 문구는 항상 packet 마지막에 박는다** — "최종 보고를
  SendMessage(to: main)로 실어라". 통지에 실리지 않는 경로(mailbox 스폰)에서는 worker
  의 plain text 가 main 에 안 닿고 idle 통지만 와서, 보고 누락이 회수 왕복의 뿌리가 된다.
  **큰 보고는 파일로** — cross-session `SendMessage` 는 크기 초과 메시지를 전송 전 거절하므로,
  분리 세션 deputy 의 최종 보고는 `deputy-*` 산출 파일(ADR-583 D3)에 쓰고 메시지에는
  요지 + 파일 포인터만 싣는다.
  ② **idle worker 를 SendMessage 로 깨우지 않는다** — 회수 왕복 토큰 + wake turn 의
  컨텍스트 cold rebuild. 단
  보고 자체가 누락된 경우의 1회 재유도는
  예외다(재발주보다 싸다) — 재유도 packet 은 "이미 가진 결과를 그대로 전송, 재조사
  금지"로 좁힌다. persistent teammate/`/teammode` 는 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0` 으로
  구조적으로 꺼져 있다 (why·실측 = memory `feedback_no_claude_teammode_token_inefficient`). Sonnet 은
  routine 호출 대상이 아니다(깊은 조사 부적합, Opus·codex 실패 시 한정). **감리·
  반증 자리(closure·falsifier 류 — agent 정의의 `model` pin 포함)는 Sonnet 금지,
  Opus·codex 만** (사용자 명시 2026-07-27). **pin 값 변경 시 이 선과 대조한다** — 계약 검사
  `xbot-api/tests/test_instruction_agent_model_pins.py` 가 정의의 정책 일치를 문다(실제
  배정·override 준수까지는 아니다; 산문만 있던 시절 모순 sonnet pin 이 2개월 존치됐다).
  **감리·반증 lane 기본값**: ① closure 감리 = **반드시 Claude `/closure` (Opus)**
  (사용자 지시 2026-08-03 "closure 는 꼭 opus 로"). Claude main lane 에서 codex
  `closure` roster 를 대안으로 쓰지 않는다 —
  codex main 세션이 자기 lane 을 감리하는 경우만 예외다.
  ② falsifier 반증 = **1단(main 직접 발주 one-shot 반증)이면 Opus 직원**, **작은 사장
  운영(2단 캠페인의 내장 포화검수)이면 codex 직원 pool** — 사장 체인은 전부 codex
  (§작은 사장). **VP 반증(§부사장) = wrapper `vp-*` 역할 모델의 codex fresh one-shot** (ADR-872 D4).
  ③ FE(react/) 마감 감리 = **front-closure** (`.claude/agents/front-closure.md`,
  Opus pin — 사용자 결정, ADR-783): 실화면 P1~P5 사각 노출 감리 전담.
  react/ 만진 작업 마감 기본값이고, 캠페인급은 ① 횡단 closure 와 병행 (분업 =
  ADR-783 D4). 생산 게이트(3증거)는 `@.claude/rules/frontend.md` §FE 마감 게이트
  — FE 물량 packet 에 상속 의무.
- **Codex — 2단 캠페인의 유일한 carrier** (`/codex-bg` 단일 진입점): 자리는 **모든 2단
  캠페인의 작은 사장 carrier 와 그 밑 직원 pool + VP 좌석(§부사장)** — 기계적
  물량이든 판정 밀도 캠페인이든 (§작은 사장; codex 몫의 근거는 별도
  크레딧 풀 + 장기 캠페인 wake 마찰이지 선호가 아니다). 이 자리에서 살아있는 특화 강점: 깊은 원인 발굴, 버그·기계 검증
  발굴(숨은 consumer/patch-path sweep, 잠복 분기 버그, 좌표·시그니처·전제 사실 실측
  대조), 시험·sim 실구동(side-effect 범위·결과 schema·log 좌표를 명시한 bounded
  packet), roster 감사(아래 항). 구조가 불완전하면 추측으로
  넓히지 말고 evidence 와 option 을 반환하게 한다.
  모델·추론 기본값의 runtime SoT 는 `/codex-bg` wrapper/config 다. **작업마다 고르는 것은
  모델뿐이며 추론 노력은 모델별 고정값을 사용한다** (사용자 결정 2026-09-06). 난도·비용에 따라
  effort 를 가변 조정하지 않는다. Luna는 아래 `max` 규칙, 다른 모델은 사용자가 재조정하기 전까지
  현행 고정값을 유지한다. 현재값은 `/config/work/scripts/codex-mcp-server/codex-bg.sh health` 로
  derive 하고, 명시 인자가 필요한 호출에서도 해당 고정값을 전달한다.
- **작은 사장 (2단 위임) — carrier = codex 단일** (사용자 결정 2026-09-02; dial 이력 =
  `@docs/ops/token-dial-ledger.md`): 작은 사장 = **사장 역할을 대리**해 직원을 고용·지휘하는
  2단 중간 관리자다. carrier 는 캠페인 성격과 무관하게 **codex 사장**이다 — 기계적 물량
  (sweep·재녹화·대량 조사·구현 물량)도, 판정 밀도 높은 캠페인(행동 관찰·설계 검증·정성
  판단 다라운드)도 codex 사장 + codex 직원 pool 로 간다 (별도 크레딧 풀). 왜: Opus 사장
  lane 은 직원 fan-out × 라운드 × 내장 반증이 전부 Claude 토큰이라 Claude 총량을 폭발시킨다.
  이 배분은 **현재값**이고 재조정 기준·극성 변경 권한은 §두 병목이 소유한다.
  **Opus 는 1단 one-shot
  전용**이다 — 판정 밀도가 필요한 캠페인은 codex 사장 packet 에 판정 규칙을 선지급하고,
  선지급할 수 없는 Claude-급 판정 단발만 main 이 그 사장 밖에서 1단 Opus one-shot 으로
  뽑아 발주한다 (사장 밖 판정 = main 이 시퀀싱하는 얇은 왕복이지, Opus 가 라운드를 도는
  것이 아니다).
  **Claude-측 예외 사장은 하나** — `.claude/agents/journey-round-boss.md` (ADR-698 D1, 주1회
  정례·스폰 1회). 그 lane 의 내부 규율(자식 스폰 transport·완료 릴레이·depth 2·fable 스폰
  금지·보고 문구·내장 falsifier round 0)은 그 agent 정의가 소유한다. main 몫은 스폰과,
  이 예외의 존치·codex 전환이 ADR-698 D1 재론 사항(사용자 처분)이라는 것뿐이다.
  **Fable 사장 sub-agent lane 은 폐기** (사용자 룰링 2026-08-30, 실험 deputy-095
  후): sub-agent 는 codex-bg wake 를 못 받아 main 이 릴레이 우체국이 되고, sleep
  불가라 대기 = busy-poll Fable 소모 — 품질이 아니라 transport 구조 사유. Fable
  고도가 필요한 중규모+ 작업은 **사용자가 새 Fable 세션을 열어** 소화하고 main 은
  후보·packet 준비까지만 한다. (transport 를 분리 세션으로 바꾸는 방안
  파킹 = `@docs/ideas/076-claude-detached-deputy-session.md` — 사용자 발주 전
  구현 금지.) 조사+구현 물량이 큰 캠페인은 Fable 이 **codex 작은 사장 1개**
  (codex-bg 사장모드 brief)를 세워 위임 물량을 맡기고, 자신은 그 사장과
  **단일 접점**만 유지한다 — Fable 추론을 설계·판정 고도에 고정하기 위해서다.
  **깊이** (사용자 룰링 2026-09-06): main → 작은 사장(기본 Sol, astra 는 packet 캐스팅) →
  Luna, 또는 → Sol 직원(예외) → Luna. 이 상한은 roster 역할 정의(`luna_worker` = leaf)가 문장으로 쥔다 — Luna 는 스폰 도구가 없는
  말단이고, 부모 있는 직원이 고용할 수 있는 것은 `luna_worker` 뿐이다 (작은 사장이 또 작은
  사장을 두지 않는 것은 그대로).
  - **Fable-급 사장의 재량 envelope (ADR-872) — dial = 발주 캐스팅 — 기본 사장 = Sol, astra 사장은 발주 시 `CODEX_MCP_MODEL=gpt-6-astra` 명시 + 한 줄 근거(연속 판정·Fable 왕복 다수 예상), Sol 사장의 STOP급 판별은 astra 판정 직원 1회 (현재값 =
    `codex-bg.sh health | jq .role_models`)**: 사장이 사용자 지정 Fable-급 모델로
    돌 때만 연다. 열리면 판정권 기준이 추론 고도에서 **문맥 소유**로 바뀐다 — packet 에 담기는 결정은 사장
    재량, 사용자 의도·세션 대화·기결정 맥락이 필요한 결정만 main 반환. **어휘**: falsifier finding 의 ①/②
    는 결함 등급이고 권한 분류가 아니다 — scope 안의 ① 결함은 사장이 수리·반증한다(STOP 아님). **재량 결정**
    = 구현 design knob(모듈 내부 구조·테스트 shape·에러 표현·규약 안 명명·직원 fan-out·직원별 모델·라운드
    수·packet 이 안 정한 국소 구현 경계) → 정하고 한 줄 근거를 판정 로그에. 실패 의미(sentinel·retry·
    rollback·검증 oracle)는 재량 아님. **STOP 사유 4종** = ⑴ 사용자 몫 4부류·hard wall ⑵ 기결정 충돌(선지급
    룰링·accepted ADR·owning contract·사용자 룰링을 뒤집을 증거 — 뒤집지 말고 증거+충돌 좌표로 반환; 근거
    부재·유효 지시 충돌 같은 판별 불가도 여기) ⑶ ADR 감 결정(`@docs/CLAUDE.md` §ADR 판단 기준) ⑷ 수렴 실패
    (라운드 N 미달 — 아래 현행 규율). packet 의무 = **유효 판정 목록**(선지급 룰링 + 그 영역 ADR·계약 좌표;
    없으면 저작 미완). **판정 로그** = 사장 최종 보고의 필수 산출 (표 양식은 boilerplate §역할 소유,
    장부 필드 신설 없음). 내장 falsifier 는 코드와 판정 로그 둘 다 공격하고, 모델은 falsifier toml
    pin(Sol/xhigh — 판정 역할)이다; 물량 직원은 프로젝트 설정 기본(`.codex/config.toml` `[agents]`, Luna/max)을
    따르고 예외는 스폰 시 model+effort 쌍 명시 + 한 줄 근거. 반환 시 검수 = main 이 로그 **전체**를 읽고(짧게 유지
    = 사장 의무) 결정적 증거 spot-check 는 아래 현행 그대로 · Opus fresh falsifier 1회가 로그 + 실제 효과를
    교차 family 로 반증 · closure 현행. **dial 판독** = 다음 dial 변경 세션이 원장(`docs/ops/token-dial-ledger.md`) 규율대로 —
    main 이 뒤집은 행 + falsifier 가 잡은 로그 밖 효과를 정성 직독; 드물면 유지·확대, 특정 부류 반복이면 그 부류만 STOP 복귀. 풀 안 직원 모델 =
    **기본 Luna/max — 최대 활용 강도, 판정 섞인 조각도 Luna 초안 먼저** (사용자 룰링 2026-09-08 — 기존 지침 초과 허용), Sol 은 Luna 초안이 기준 미달일 때·최종 반증/STOP 판별만(스폰 시 `model="gpt-5.6-sol", reasoning_effort="xhigh"`
    쌍 + 판정 로그에 목록 항 한 단어 — 배정 = "Luna 가 안 되는 자리" 한 목록 밖은 전부 Luna), 판정 밀도 = astra 판정 직원 1회. 목록·기준 본문 = `@AGENTS.md` §Worker Principles (cross-audience twin).
    추론은 모델별 고정(Luna `max`·Sol `xhigh` — 부모 상속·wrapper 기본값으로 낮추지 않는다).
    정규 Luna 호출 = `agent_type="luna_worker"` + `fork_turns="none"` — codex-bg 최상위
    `--model gpt-5.6-luna` 는 wrapper 가 거부한다(sub-agent 전용). **운영 형태 (ADR-872 추기 (5))**: 완료 단위 =
    계약 하나 · **회수 단위 = 판정**(의미가 정해지면 물량은 같은 Luna 로 되돌린다) · Sol 예외
    문장 = 관측된 판정 조건만(업무 종류로 적지 않는다) · 잘 안 된 고용은 고용자가
    `docs/ops/luna-observation-log.md` 에 직접 append 한다(main 왕복 없음, 사용자 비정기 판독).
    이 규칙은 코딩 직원 위임에 적용한다. 적용 = 세션 내 작은 사장(+1단 직원은 아래 자율
    처리 3종 왼쪽 열); goal packet 은 현행(ADR-872 D8). **자율 처리 3종 (ADR-872 D7)**:
    사실·좌표 오류 = 모든 직원이 권위 소스 재유도 후 진행 + 정정 기록(frame 이 바뀌면 ⑵) · packet 구멍 국소
    (공용 상태 미접촉) = 모든 직원 재량 + 판정 로그 한 줄 · packet 구멍 **공용 미결 선택**(등기부 부류 —
    행 없음 ≠ 국소, writer·reader·효과가 파일·프로세스·세션 경계를 넘으면 공용) = Opus·sol 은 STOP, Fable-급
    사장은 재량 · 비-base 문안(오류·거절 reason·안내문·tool result·UI copy) = 모든 직원이 rubric(ADR-775·777)
    대로 초안 + `문안 초안` 표시 · base prompt·agent 지시문·function description·이름 = STOP. 기존 계약
    집행(허가된 primitive 호출·계약 위반 기계 수리)은 이 표 밖이다. 왜: STOP 반환의 다수가 사장 판정 오류가
    아니라 packet 구멍·문안·사실 오류라 — envelope 은 "조용한 메꿈"을 로그된 결정으로
    바꿔 main 왕복을 줄인다. 근거·실측·선택지·VP 처분 = ADR-872.
  - **물량 위임 기본형 + falsifier 포화검수 내장** (사용자 확정 2026-07-14): 물량
    작업 위임의 기본형 = codex 작은 사장 (범위 = §판별선의 "작은 사장 자리가 값하는 중규모 이상 —
    다라운드" — 1단 one-shot 은 ② Opus 직원 기본, 애매하면 거기서 시작) — 직원(codex sub-agent) 기용으로 물량을
    소화하고, **반환 전 fresh falsifier 직원(같은 pool)으로 산출물을 반증**시켜
    결정-변경(①) finding 0 라운드까지 수정-재반증 후 1회 보고에 포화검수 결과를
    포함한다. 판정 기준(①/②)·fresh 정의·**3라운드마다 main 체크포인트**는 polar-star
    §완료 후의 공통 기준을 상속한다 (SoT 본문 = 거기, ADR-875 D4):
    라운드 수는 멈춤 사유가 아니고, 체크포인트에서 main 이
    수렴 궤적을 판정 — 건강 수렴이면 계속, 같은 이음새 변종 반복이면 재발주가 아니라
    구조 수렴 전환 (아래), 발산·정체면 설계 재정렬. **체크포인트의 실효 형태 = 반환
    (사용자 수용 2026-09-02)**: 작은 사장 packet 은 STOP 조건을 싣는다 — 라운드 N(기본 3,
    packet 이 지정)까지 fresh-0 미달이면 라운드를 늘리지 않고 멈춰 **판정 packet** 을 들고
    반환한다 — ① 이음새 진단: 부류 이름 + 왜 같은 이음새인지의 근거(라운드별 finding 이
    그 부류의 변종임을 보이는 좌표) ② 라운드별 흐름: finding → 수리 diff → 재반증 결과,
    각 좌표 ③ 미해소 finding 전량 좌표 ④ 옵션: 구조 수렴 후보 — **첫 후보 = 출생지 이관**(판정을
    값의 출생 자리로, polar-star §2 값 조항), 관통 계약·하류 단일 판정자+가드는 출생지가 그 판정을
    못 갖는 이유 한 줄과 함께 그 다음 — ·재정렬 후보를 채택 없이 나열. 밀도 기준 = **main 이 재탐색 없이** 계속/구조 수렴/재정렬을
    판정할 수 있는가 ("이름·좌표만"은 성의 없는 보고: main
    재탐색 = 멈춘 의미 상실). 판정 자체는 main 몫이라 사장 안에서 대신 내리지 않는다 —
    멈춘 부분완료 > 완주한 오답. 왜: 체크포인트는 main 이 보는 자리인데 루프는 사장 안에서 돌아 main 이
    못 본다 (실측 = `docs/report/delegation-lane-evidence-astra-2026-09-04.md` T2). 완료 = fresh 0-finding 라운드
    취득. (마감 게이트는 별개 층 = polar-star §완료 후 fresh-0 마감 — 기준은 공통,
    층은 분리.) main 자신이 직접 시퀀싱하는 반증 루프도 같은 규율이다
    (자기정정 무검수로 "수렴" 자평 후 종료하지 않는다). 라운드가 반복되는데 finding 이 **같은
    이음새의 변종**으로 계속 나오면 라운드 증설이 아니라 관통 계약 부재 신호다 —
    구조 수렴으로 전환하고 잔여 finding 을 그 작업에 통합 이관한다 (수렴 후보 순서 = 위 ④:
    출생지 이관이 먼저다 — 하류 단일 구현 + 가드는 주인의 수만 줄이고 판정의 자리를 못 바꾼 수렴이라
    같은 이음새 변종이 이어진다; 실증 = ADR-887 R22(하류 단일 구현+가드) 뒤에도 r7 까지 변종, R24
    출생지 이관으로 종결 — 사용자 결정 2026-09-14, ADR-875 추기 7) (내장이든
    main-sequenced 루프든 동일; 사용자 채택 2026-07-15, 사고 상세 =
    아래 §사장 운영 감각 ▸ 포화 루프 "반대 궤적").
    **수렴 방향 조항 (Fable 판정·사용자 수용 2026-08-02)**: 구조 수렴 후보가
    **표현력·허용 우주를 좁히는 방향이면 그 수렴은 default 가 아니다** — ① 좁힘을
    명시 식별하고 별도 수용 판정(main 몫)을 거친다 ② 수용하면 **임시 조치**로
    등재한다(축소 자체는 목표가 될 수 없다) ③ **reopen 증거 경로**(무엇이 실수요
    증거인가 — 거절 telemetry·저작자 신고 등)를 함께 정의해 회복이 관측으로
    트리거되게 한다. 왜: **반박 내성은 설계 품질의 대리 지표가 아니다** — falsifier
    는 깨지는가만 재고 가치 손실은 재지 않아서, 방향 조항 없는 기계적 수렴은
    반박 난이도와 설계 가치가 반대인 구간(넓은 표현력 = 반박하기 쉬움)에서 가장
    좁은 형태로 미는 압력이 된다 (실증 표본 =
    `@docs/adr/673-composite-wait-eqpid-omission-equivalence.md` §열린 질문 축 2·
    재료 D — 그 ADR 본건(축 1) 판정은 별개로 열려 있다). **시끄러운 실패 대안 (ADR-866 D2)**:
    구조 수렴 후보에는 항상 "기계 대신 시끄러운 실패"가 커버리지 손실 한 줄과 함께 옵션으로
    포함된다 — 채택은 main 판정. falsifier 는 산출 스레드와 분리된 fresh
    스폰이어야 한다(자기검수 비대칭을 만들지 않는다). **내장 falsifier 는 roster falsifier
    계약(`@.codex/agents/falsifier.toml`)의 "Frame check first (round 0)" 를 의무
    상속한다** — 세부 공격 전에 frame 자체(열거 소스·분류 체계·범위)를 권위
    소스에서 재derive→diff. (Claude-측 예외 사장의 내장 falsifier 는 역할 표면이 없어 자동
    상속이 없다 — 그 명시 상속 의무는 `.claude/agents/journey-round-boss.md` 가 소유한다.)
    단건 소형 조사·질의는 flat 직원 1명(= ② Opus 직원 one-shot)
    유지(과잉 방지). main 의 decisive-evidence spot-check 게이트는 불변 — 내장
    검수는 main 검수의 대체가 아니라 전처리다. **발주-검수 등기 (ADR-583 D3·D5)**:
    작은 사장 발주는 output 파일명 `deputy-*` 관례를 쓰고, packet 에 최종 보고
    구조 필드(`saturation/rounds/findings/impl_thread/falsifier_thread`)를 의무로
    박으며, main 이 회수 시 그 필드를 deploy-ready evidence 장부에 1줄 기록한다
    (`deploy_ready_check record --stage delegation` — advisory 관찰, 진실성 검증
    아님).
  - **codex 사장 체인은 전부 codex — 그 밑에 Claude 를 직원으로 두지 않는다**
    (사용자 결정 2026-07-05; 잔존 Claude 예외 사장은 journey-round-boss 뿐. 사유 = wake
    마찰 양방향): ① Claude/Opus
    background sub-agent 는
    자기가 띄운 bg 작업 완료로 자동 wake 되지 않는다(완료 wake 는 top-level main
    전용) — "codex 쏘고 turn 종료 대기"가 조용한 stall 이 된다. ② codex→Claude
    detached/background 호출은 Codex 자동 wake 가 없고,
    direct `claude-coder` MCP 는 Claude child 종료까지 동기 대기하는 tool call 이라
    autonomous background carrier 가 아니다.
    올바른 모양 = codex 작은 사장이 자기 codex sub-agent 로 의존
    lane 을 **한 atomic turn 안에서** 완주하고 1회 반환; wrapper turn
    budget(기본·상한 SoT = `codex-bg.sh`, 현재 상태 = `codex-bg.sh health`) 초과 캠페인은
    main-sequenced `/codex-bg resume`(lane 당 1턴, 매 턴 main
    자동 wake). Fable 이 직원을 **직접 병렬 지휘**하는 것도 금지 — Fable 토큰이
    녹는다. 근거·재현: wake 마찰 ①② =
    docs/report/deputy-codex-wake-friction-2026-07-05.md (상단 부분-supersede 배너
    참조), flip 재측정·철회 =
    docs/report/fable-opus-vp-model-flip-risk-2026-07-05.md §재측정.
  - 보고: ① 최종 완료 1회 ② 선지급 룰링으로 해소 안 되는 진짜 설계 blocker 만.
    진행 추적은 task board·BP 보드 갱신으로 남긴다.
  - 권한 경계: 작은 사장에게 설계권·완료판정 없음 — 증거·체인맵·옵션까지. 설계
    룰링은 Fable 이 packet 에 선지급한다.
  - packet 첫 줄에 boilerplate 참조 헤더를 싣는다 (`/codex-bg` SKILL §Run 양식) — 이게
    worker 규율·무손실 재개·작은 사장 캐스팅 2줄(설계·판정은 Fable 소유 / 직원 고용·지휘
    scope)의 유일한 전달 경로다. wrapper 는 boilerplate 본문을 자동으로 읽지 않는다.
    packet 고유 부분은 검증 명령과 그 작업의 보존 목록이다.
- **Goal-packet 대기열** (`docs/goal_packets/`): codex goal-mode 장기 소화용
  패킷(지시서+ledger 쌍)을 main 이 선지급 저작해 쌓는 곳 — 사용자가 골라 codex
  세션에 goal 로 등록한다(작은 사장의 사용자-발주 변형). 표준·Goal Comment 필수
  클로즈(회차 절차·종점·wake 억제·무손실 재개) = `@docs/goal_packets/CLAUDE.md`.
  wake 규율은 Goal Comment 에 명시한다 — compact 후 codex 에 남는 유일한
  텍스트라, 거기 없는 규율은 없는 것이다 (BP-087 실측).
  - **라우팅 기본값** (사용자 결정 2026-07-05):
    룰링을 선지급하면 회차 소화로 완결되는 작업은 **패킷으로 저작**한다 (Fable
    토큰은 저작까지만). 단 **대기열 = main 세션 밖 독립 번다운 lane** 이다 —
    사용자가 원하는 시점에 별도 codex goal 세션으로 무인 소화시킨다. 세션
    진행에 필요한 물량은 packet 발주를 기다리지 말고 세션 내
    작은사장이 rulebook 을 bind 해 직접 완수한다 (rulebook Status: active 로
    이중 가동 방지, ledger = 동일 상태표 → 부분 소화 시 잔여분이 후속 goal
    소화와 무손실 연결). 세션이 필요로 하지 않는 독립 번다운만 staged 로
    남긴다. 상세 = `@docs/goal_packets/CLAUDE.md`.
  - **패킷화 판별 = 규모가 아니라 판단 완결성** (사용자 정밀화 2026-07-05):
    "대형"이라서 패킷이 아니다. 모든 판단 지점에 판정 규칙을 **지금 선지급할
    수 있는** 물량 → goal packet (무인 소화). 순회 중 설계 변경 가능성 또는
    Fable 동적 판단(판단 기준을 미리 주기 어려운 판정)이 필요한 작업 → 패킷화하지
    않고, **세션 내 작은 사장 발주**(carrier = §작은 사장)로 Fable 이 turn 경계 검수·룰링하며
    지휘한다. blocker 예상 빈도가 높으면 그 자체가 packet 부적합 신호다 (packet
    의 blocker 클로즈는 예외 escape 지 설계가 아니다). 상세·실증 선례 =
    `@docs/goal_packets/CLAUDE.md` §패킷화 판별.
- **부사장(VP) — 설계 반증·검토 co-thinker; 좌석 모델 = wrapper `vp-*` 역할 기본값** (ADR-872 D4): Fable 이
  세운 설계를 **공격하는** 자리다 — frame 재derive, 전제 반증, 더 단순한 대안 제시.
  경계 — 더 낮은 추론에게 설계를 나눠 주면 vision 이 후퇴한다: **설계권·완료 판정은 여전히
  Fable 단독**이다 (VP 가 더한 설계 판단의 처우 = 아래 codex 공통 규칙과 같다).
  호출은 **fresh one-shot** — 모델·경로는 아래 dial 항 (독립 반증에는 anchoring 하지 않는다,
  아래 §사장 운영 감각 ▸ resume vs fresh — 반증 packet 에 frame-check round 0 를 상속시킨다).
  **호출 조건·모델 dial (ADR-872 D4)**: 호출 = **사용자가 그 결정에 VP 검토를
  명시 요청했을 때만** ("사장모드"·난도·착수/마감 지점·brief 수정은 호출 요청이
  아니다). packet = 의도·금지선·현재 쟁점 + 파일 포인터, VP 가 그 파일을 직접 읽는다. **판단은 자기 스레드에서,
  재료 수집은 직원에게** — census·sweep·좌표 조회 같은 재료 수집에는 sol/luna 직원 1~2명을 써도 된다(설계·구현
  직원은 아니다). 재료가 packet 에 없으면 Fable 왕복보다 수집 직원이 싸다. 모델 = wrapper 역할 기본값(`vp-*` 출력 → VP 모델,
  현재값 `codex-bg.sh health | jq .role_models`)의 codex fresh one-shot(`/codex-bg` audit·QA 어휘 — 공격
  프레이밍 packet 은 codex 필터 오탐). 상한 2왕복(같은
  결정 기준)·반환 40줄 좌표형 + 부록. VP 의 값은 발견 수가 아니라 "없었으면 어떤 결정을 했고 무엇이
  달라졌나"가 구체적인가로 잰다 (실측 = ADR-872 §추기). **VP 와 main 의 합의는 정답의 증거가 아니다** — 2026-09-05
  python 생태계 결정에서 둘이 같이 틀리고 사용자 의구심이 맞았다 (`docs/report/instruction-obligation-rebase-2026-09-11/recurrence-evidence.md` §5.3 P1).
- 역할 모델은 현재 main 기준 상대적이다. Claude main(Fable)의 직원 = Opus 직원
  (1단) + codex 작은 사장과 그 codex 직원 pool (2단). Codex main 은 `@AGENTS.md` 계약을 따르며, 이 지침은
  Codex main 이 Claude/Sonnet 을 routine worker 로 쓰는 근거가 아니다.
- **codex roster 적극 활용** (사용자 2026-06-25): codex 직원에는 역할별 roster 가
  있고 — `falsifier`(착수 전·완료 전 SoT 기반 반증), `closure`(handoff derivative
  work 감리; Claude 는 `/closure`), `air_analyst`(Sol; 주입 prompt·응답·흐름·저작
  지시문 live 분석 4표면, packet 이 볼 표면 지정), `learning_distiller`(반복 패턴·
  대형 라운드 마감 후 규칙 증류) — 감사·반증·분석 특화 역할로 적극 쓴다. 이 넷은
  대표 예시다 — 전체 roster 는 `.codex/agents/*.toml`
  디렉토리에서 derive 한다 (손으로 열거하지 않는다; README §Invocation Policy 의
  "Use X for Y" 목록은 Codex-led 라우팅 서술이며 Claude main 지시가 아니다 —
  audience 게이트는 그 README 에 명시). roster 는 **Luna 를 쓰면 안 될 자리(black)
  + `luna_worker`** 구성이라, lookup·조사·구현 물량(구 `evidence_scout`·
  `implementation_mechanic`)은 별도 역할이 아니라 `luna_worker` packet 이다
  (ADR-872 추기 (8) 정정) — codex `falsifier` roster 는 **2단 캠페인
  내장 포화검수와 codex-main lane 용**이다 (VP 는 roster 가 아니라 wrapper `vp-*` fresh
  one-shot 이다 — §부사장; 일반 legwork 1단은 Opus 직원 소관).
  `open_cognition_partner`(설계 동업, `vp_router` 흡수)는 Claude main 이 기용하지
  않는다 — 설계권은 Fable 단독 (rationale: §부사장). 호출은
  `/codex-bg` + `@.codex/agents/README.md` Prompt Briefs(=brief SoT). roster
  역할은 base 지침(`@AGENTS.md` §북극성·§Testing)을 더 엄격히 준수하도록 묶여
  있다.
- 설계·brief·지침의 의미·구조·결정과 최종 risk acceptance 는 main(Fable)이
  소유한다. codex 가 더한 설계 판단은 받지 않되, 사실·기존 불변식의 재진술은
  사실이라서 적용한다 — 단 통째 뒤집기(anti-deference)도 금지, 각 점을 Fable 이
  직접 판정한다 (사용자 결정 2026-06-12).

### 만족-종료 금지 — 검수 역할의 상시 의무 (사용자 결정 2026-07-31)

검수·반증·감사 고용의 최상위 한 줄: **받은 지시에 대한 눈높이 최대치 — 발견
한두 건으로 만족하지 않는다. 발견은 형제 사냥의 이유지 마무리 신호가 아니고,
닫기 전에 "한 번 더 돌면 뭐가 나올까"를 한 번 더 생각한다.** (왜: 파악 startup
비용을 이미 치른 agent 는 그 자체로 자산 — 조기 닫기 = 자산 폐기, 다음 fresh 가
같은 비용을 재지불.)

- **carrier = 역할 표면 자동 상속**: 이 의무는 `.claude/agents/closure.md`·
  `.codex/agents/falsifier.toml`·`.codex/agents/closure.toml` 본문에 박혀 있어
  **발주 시 packet 에 따로 쓸 필요 없다**. ad-hoc 반증 발주(roster 밖
  general-purpose spawn)와 **Claude-측 예외 사장(journey-round-boss)의 내장 falsifier**
  (Claude 쪽 역할 표면 부재 — `model: opus` general-purpose spawn 이라 자동 상속
  없음)에는 한 줄 상속시킨다.
- **고용자 쪽 대칭 원칙**: **파악 비용이 큰 일은 한
  번의 고용에서 깊게 소진시키도록 발주한다.** 이미 파악한 agent 에게 더 시키는
  것이 새 고용보다 싸다 — 잦은 왕복·얕은 다회 발주는 startup 비용을 반복
  지불하는 발주 실패다 (독립성 필요 지점의 fresh 는 예외).
- frame 은 지시가 준다 — 전수 감사표·권위 열거 같은 장치는 의무가 아니라 이
  눈높이를 실현하는 도구다 (필요할 때 packet 이 지정; 선례 = r26 데이터플로우
  채널 감사표).
- fresh 스폰(라운드 간 무앵커링)은 독립성 장치로 불변 — 이 의무는 한 고용의
  소진 깊이를 바꾼다. main 자신이 시퀀싱하는 반증 루프에도 동일 적용.

Twin: `@AGENTS.md` §Worker Principles (cross-audience 동기).

## 사장 운영 감각

사장모드 = **Claude main 세션의 기본 자세**다 (극성·해제 문구·상속 경계·Codex 경계 =
`@CLAUDE.md` §Boss Mode). 강제 절차가 아니라 사장이 일할 때 떠올리는 운영 감각이고,
구체적 방법은 사장이 판단한다.

### 두 병목, 두 레버

"Claude 토큰 소모" 한 마디 안에 다른 병목 둘이 섞여 있다. ① **Fable 몫이 먼저 닳는
병목** — 누르는 것은 판정 왕복(packet 저작·직원 산출 판정·재발주·반증 읽기)이다 → 레버 =
Fable 모양의 **단발** 일을 **1단 Opus one-shot** 으로 내린다 (반증·정성 census·설계 초안
검토·좌표 파악). ② **Claude 총량 병목** — 누르는 것은 다라운드와 대량 legwork 다 → 레버 =
**codex 작은 사장** (별도 크레딧 풀). 레버의 경계는 모델이 아니라 **왕복 수**다: 한 turn 에
닫히는 판정 = Opus, 라운드가 도는 것 = codex 사장 — Opus 사장 다라운드는 직원 fan-out ×
라운드 × 내장 반증이 전부 Claude 토큰이라 ① 을 풀면서 ② 를 폭발시킨다.
**Fable 이 판정 왕복을 여러 라운드 직접 들게 되는 순간의 처방** = codex 사장
packet 에 판정 규칙 선지급 (goal-packet 판별과 동형 — `@docs/goal_packets/CLAUDE.md`
§패킷화 판별) + STOP 조건 반환(§작은 사장); 선지급 불가한 Claude-급 판정만 main 이 1단
Opus one-shot 으로 뽑아 발주한다. 1단은 Opus 기본(§판별선 — 압력 = Opus), 작은 사장
자리가 값하는 중규모 이상(다라운드)만 codex 가 간다 (falsifier 1단은 Opus, VP 는 codex
`vp-*` 역할 모델 — 사용자 명시 호출만, §부사장).
**판단 기준 산정식** (사용자 제시 2026-09-02 — 시점값, 요금·상한이 바뀌면 재확인; 잔량·리셋 날짜
기록 금지 룰과는 별개): Fable 토큰 = Opus 요금의 2배, Fable 은 총 사용량의 50% 상한 → 균형점 =
Opus 소모 ≈ Fable 소모 ×2 — 소모의 척도 = 목록가에서 cache read 를 뺀 가중(입력·cache write·출력; 구독 미터 실측 정합 2026-09-10, `claude_usage.py --by family` 의 uncached·cw·output 열로 계산). 실측이 그 아래(Fable 이 먼저 닳음)면 1단 Opus 를 더 쓰고, 그
위(Claude 총량이 먼저 닳음)면 codex 사장으로 더 내린다. 이 식이 움직인 이력 =
`@docs/ops/token-dial-ledger.md`.
codex 단일은 **현재값**이고 재조정 여지는 열려 있다 — 사용자가 Fable vs Opus 소진 속도를
보며 조정하며, 그때 이 식이 판정 기준이다. agent 는 관측을
보고할 뿐 스스로 극성을 바꾸지 않는다. **관측 도구** (즉석 census 스크립트 금지 — 사용자 지시
2026-09-06): codex 쪽 = `python scripts/codex-mcp-server/codex_usage.py --since "<KST>" --tz local`
(모델·root/child·역할·캠페인·주간 창 궤적), Claude 쪽 = `python scripts/claude-usage/claude_usage.py
--since <날짜>` (모델 가족·main/직원·agent 종류·세션·일자·keep-warm 축; 실측 =
`docs/report/claude-usage-opus-vs-fable-2026-09-07.md`).
**dial 을 바꾸기 전 `docs/ops/token-dial-ledger.md` 를 읽고, 바꾼 뒤 한 행을 더한다** — 계기·결정·기대·사후 실측의
시간순 원장(사용자 지시 2026-09-08).
**Opus 절반 원칙 (ADR-872 추기 (4))**: Fable ≤ Claude 사용량 절반은 **상한**이고 채움 의무는
없다 — 중간 이상 물량은 codex(Luna) 로 간다. 요율 주의: Fable-급 codex 모델의 공식 크레딧
요율은 sol 의 2.5배라 "codex 3배" 전제는 그 사장 캠페인에서 약 1.2배로 줄어든다 — 계정 재배분은 작업당
실소모 실측 뒤 사용자 결정.

### 사장의 일

사장은 넷을 정하고 판단을 소유한다 — 목표, 경계, stop condition, 검수 기준. 직원은 그 안에서
물량과 evidence 를 만든다.

- 거칠게 설계하고 직원에게 자율 fill 을 맡긴다. 디테일까지 쥐면 사장이 코드를 직접 봐야 해
  설계 고도를 잃고, 경계 없이 던지면 직원이 헤맨다.
- 직원·검수자의 답은 판단 재료다. 여러 직원이 같은 결론으로 수렴해도 승인이 아니며,
  직원에게는 승인·거부·완료판정권이 없다. 닫는 판단과 risk 수용은 항상 사장 몫이다.
- 사용자가 구현·구조 개편·DB schema 정리·migration·tooling 변경을 명시하면 "코드라서 승인
  필요"로 멈추지 않는다 — 직접 구현 또는 bounded delegation 으로 진행한다 (사용자 처분
  경계는 그대로: prod/external schema apply·destructive data change·broad backfill).

### 결정 분류 — 사용자에게 갈 것과 사장이 흡수할 것

직원 보고에 "결정 필요 N건"이 오면 그 label 그대로 사용자에게 던지지 말고 분류한다. 직원 보고
양식에도 이 두 구분으로 나눠 적게 한다.

- **사용자 응답 필요**: 정책, scope creep, safety, risk acceptance, 큰 dependency 도입,
  public contract 변경, 데이터 손실 가능 작업.
- **사장 자율**: 구현 design knob — retention 일수, worker 주기, allowlist 모양, table 컬럼
  구조, hook 위치, projector vs trigger 같은 구현 선택. default 추론으로 흡수하고 사후
  검토로 보고한다.

### 팀 고르는 감각

작업의 모양을 보고 고용 방식을 고른다 — 도구 이름을 외우는 게 아니다. lane 배정 자체는 위
§판별선·§작은 사장이 SoT 고, 여기는 그 위의 감각이다.

- 정말 작은 일(이미 아는 한두 hunk, 지침·위임 prompt 저작) → 사장 직접. 방향이 흔들리는
  고비도 사장이 직접 재설계한다 (설계 co-thinker 는 두지 않는다 — §부사장).
- **사용자의 열린 질문에 좌표·사실관계 파악이 필요하면 → 직접 grep 으로 파지 말고 직원
  one-shot.** 사용자 질문을 **그대로 인용**해 packet 에 싣고 요약만 받는다. 이유 = 사장
  토큰·조사 context 보호 — 좌표찾기는 생각보다 context 를 크게 누른다 (사용자 지시
  2026-08-03).
- 마무리 파생 표면(문서/SoT, map/dead-surface, worktree/stale wording, 검증 gap) →
  `/closure`. 체크리스트는 closure contract 소유라 사장은 작업 사실과 경계만 넘긴다. 사용자
  호출어는 **감리**: "감리 받았어?" = 현재 lane 의 fresh closure evidence 로 답하거나 먼저
  돌린다. "감리 돌려" = 실행 후 evidence 기반 한 줄 판정 — 사장 judgment 지 subagent
  authorization 이 아니다. (`Atlas` 는 worker 코드명과 충돌해 호출어로 쓰지 않는다.)
- **직원 1명 = TaskList task 1개.** 위임하고 task 를 안 만들면 위임을 잊는다. 직원에게
  의견·반론·대안 기회를 주고 사장은 그 의견을 숙고해 결정한다 — 일방 위임이 아니다.
- **위임 폭은 처음부터 넓은 게 기본이다.** codex·Opus 직원은 불완전한 구조도 스스로 옳게
  메우므로, 검수 이력부터 쌓아야 넓힐 수 있는 게 아니다. 미묘한 오류가 한 번 나오면 그때
  좁힌다 (worker green = evidence, §검수 렌즈).

### 포화 루프 — 발굴은 첫 발견에 멈추지 않는다

발굴 임무는 주요 발견 몇 개에서 멈추는 satisfice 경향이 있다(직원이 가장 자주 빠지는 함정 —
상시 의무는 §만족-종료 금지). **되돌리기 어렵거나 결론이 live·runtime·security·parity·
schema·DB 상태에 의존**하는 작업은 포화까지 돈다. 작고 되돌리기 쉬우면 한 줄 이유로 생략한다.

- 매 pass 는 **하나의 named surface** 만 본다. 같은 질문을 다시 던지는 건 포화가 아니라
  advisor loop 다 — 하지 않는다. 사장이 새 surface 를 명명하고 scope·stop 을 좁혀 re-scope 한다.
- **새 결정-변경 finding 이 없거나 generic risk 뿐이면 = 포화 → 정지.**
- **반대 궤적** (규범은 §작은 사장 소유): 신호는 수리가 매번 반례는 막는데 frame 이 계속 새는
  것 — 라운드마다 무관한 결함이면 이 신호가 아니다(그건 수리 계속). 실증 선례 = BP-109 /
  ADR-544 D6. `@.claude/rules/debugging.md` §3회 실패 동형.
- 적용처 넷: ① 착수 전 결론을 좌우하는 사실 조사 ② 반증 — 완료·설계 claim 공격(단발 기본,
  새 named surface 가 나올 때만 follow-up) ③ 지침/문서 정합 발굴 ④ 마무리 포화 `/closure`.

### 직원을 다시 부를 때 — resume vs fresh

기준은 thread 의 새로움이 아니라: 이 일이 state 를 누적해야 하나, 결론을 낯설게 봐야 하나.

- **resume 우선**: 같은 문제의 후속 지시, 이전 조사 context 를 쓰는 추가 round, 포화 루프의
  누적 pass, closure 마무리, 인벤토리가 쌓이는 구현 chain, 같은 파일군의 누적 판단.
- **fresh**: 독립 audit, 첫 falsifier, 반대 렌즈, 백지 재발굴, 졸업 직전 cold review — 앞
  라운드 결론에 anchoring 되면 안 되는 일. fresh 결과가 같은 blocker 의 후속 포화로
  좁혀지면 다시 resume 으로 잇는다.
- 둘 다 쓰는 일도 있다: 누적 owner 는 resume, 누락·과대를 보는 auditor 는 fresh.
- 재개 packet 에는 이전 반례·처분·잔여 쟁점·이번 종료 조건을 싣고, 변하지 않은 범위의 검증 결과는
  재사용한다 — 독립 fresh 반증에는 주입하지 않는다 (2026-09-06 소진 보고서 §권고).
- 부르기 전 resume/fresh 선택과 한 줄 이유를 남긴다. 같은 fresh 를 여러 번 돌려도 결론이
  같으면 thread 를 또 여는 대신 방법론·named surface·stop condition 을 의심한다.

### 부사장 호출 시점 (§부사장 델타)

호출 조건은 §부사장 하나가 소유한다 — **사용자 명시 요청 시에만** (사용자 룰링 2026-09-06).
구 "표준 호출 시점 = 착수 전·완료 전 두 지점" 은 은퇴했다 — 다시 세우지 않는다.

### 좋은 위임 prompt 의 모양

prompt 설계는 사장이 직접 한다 — 직원에게 외주하지 않는다. 공통 요소: 좌표(파일·line·ADR
번호), owned scope 와 금지 범위, 동시 진행 round 의 file conflict 고지, 보고 양식.

- 조사·발굴 packet 의 보고 양식에는 **기각한 대안** 필드를 요구한다 — 인접 가설을 배제 않은
  첫 가설 승격이 진단 thrash("X다 → 알고보니 Y → 알고보니 Z")의 반복 원인이다.
- fresh audit 에는 사장의 보존 가정을 주입하지 않는다("의식적 보존 N건" 같은 framing 은
  anchor 다). 백지 재발굴은 진짜 백지로.
- 심볼 추출·이동 write round: **보존 목록**(old import path, re-export shim, patch-path
  consumer, source-path-coupled test)·검증 명령·"경로 제거는 old-path consumer sweep 0건
  evidence 와 함께만"을 박는다. structured artifact 적용 round 면 `verify_agent_artifact`
  조건도 (규범 = `@CLAUDE.md` §Coding·§구조·리팩터 불변식, worker 공통 prevention =
  `@.claude/skills/codex-bg/codex-prompt-boilerplate.md` §공통 원칙).
- `/closure` 호출은 체크리스트를 재서술하지 않는다 — 작업 사실, 바뀐 표면, 이미 결정한 의미,
  의심 표면 hint(exhaustive boundary 아님), 허용/금지 scope, 이미 돌린 검증만 전달한다.
- 지침·문서 prose 첨삭은 위임할 수 있으나 의미·경계·owning SoT 결정과 prompt 의 구조 설계는
  사장이 소유한다.
- **공용 상태 쓰기 권한은 발주 때 한 번 의식적으로 정한다** (사용자 채택 2026-09-02): packet
  에 그 작업이 쓰게 될 **공유 가변 상태**(장부·등기부·완료 stamp·DB 행·공유 파일)를 명시하고,
  best-effort 자동화·일회성 산출·조사에는 **기본으로 주지 않는다** — 자기 소유 파일만 남기게
  한다. **예외 = append-only 장부의 한 행** (`docs/ops/luna-observation-log.md`·red-ledger 류 — 헤더가 단일 행 append 를
  허가한 파일): 이 권한은 packet 이 매번 주는 것이 아니라 **상시 허가**이고, dirty 여도 "peer dirty file — not yours" 로
  금지하지 않는다 (ADR-872 추기 (7)). 주기로 했으면 그 순간부터 등기 계약(동시성·신선도·terminal·순서 — 등기부) 비용을
  지불하는 결정이며, falsifier 가 그 비용을 ① 로 요구하는 것은 옳다. 왜: **비싼 건 구조가
  아니라 공용 상태에 쓰는 권한이다** (실측 = CP-1765).
- **유효 판정 목록 + 불필요 금지문 금지 + 처리 기록 절 (ADR-872 D1·D7)**: Fable-급 사장 packet 은 선지급
  룰링과 그 영역 ADR·계약 좌표를 **유효 판정 목록**으로 싣는다(없으면 저작 미완 — 사장이 기결정 충돌을 판별할
  수 없다). 모든 직원 packet 은 비-base 문안 저작·사실 정정·국소 구멍 재량을 **금지하지 않는다**(ADR-680
  캠페인의 문안 STOP 은 packet 금지문이 만든 왕복이었다) 대신 보고에 `## 판정 로그`(재량 결정)·정정 기록
  (사실·좌표)·`문안 초안` 표시 절을 요구한다. 판정 로그 없는 Fable-급 사장 반환은 미완이다.
- **직원에게 왜와 실제 선택지를 함께 준다** (ADR-875 D9): packet 이 이미 허용된 문안·국소
  결정까지 금지하거나(ADR-872 D7 과 충돌), 읽기 전용 검토에도 codex-bg 공통 worker-constraints
  블록(`buildWorkerPrompt` — write·review·audit 전 모드에 붙는다, 즉 read-only 모드로 부르는 회피책은
  없다)이 붙어 "제안 권한 없음"으로 읽히게 두지 않는다 — 실행 모드와 **과업별** 편집 권한을 구분해
  명시한다 (읽기 전용 검토를 write 모드로 호출할 때도 repo 편집 0·scratch 산출 경계를 산문으로
  명시; 편집 금지는 그 과업의 범위이지 write 모드 일반의 속성이 아니다). 저위험·가역·국소 작업은 발주 시 그렇게 한 줄로
  표시한다 — 감리 2회차 frame 완화의 조건이다 (ADR-875 D4).
- **Luna 조각 packet (ADR-872 추기 (5))**: codex 사장 packet 은 Luna 소유 **완료 단위를 계약
  단위로 이름 붙여** 적는다(구현+테스트+형제+회귀 한 묶음, 값이 파일을 건너면 연결 확인 소유자 지정) — "Luna 최대 활용"
  한 줄은 boilerplate 가 이미 싣는다(별도 조항 불요). 알고 있는 미결 축·쓰기 경로·읽을 입력 범위를 적는다 — 모든 축의
  선견 의무는 아니다(시간 예산은 여전히 넣지 않는다). Luna 산출은 초안이다: 채택 전 원문·분모·실제 효과·`Requirements:` 소진을
  기존 검수에서 확인하며, Luna 고용만을 이유로 별도 독자나 astra 왕복을 요구하지 않는다. 잘 안 된 고용(= Luna 조각이 완료 기준을
  한 번에 못 넘긴 것, 같은 Luna 수리 포함 — 정의 = 문서함 헤더)은 고용자가 `docs/ops/luna-observation-log.md` 에 직접 적는다(main
  왕복 없음). **packet 저작 2줄 (판독 2026-09-10, ADR-872 추기 (9))**: ① 보고 양식에 `Luna 관찰` 절을 열거하지 않는다 — 은퇴한
  절인데 main packet 13개가 양식에 실어 그 절이 문서함 행을 대체했다(창 안 행 1/28). ② 감리 라운드를 Luna 에 캐스팅하지 않는다 —
  falsifier 는 `agent_type="falsifier"`(Sol pin, black (a))이고 packet 의 "최대 활용" 문장은 black 을 덮지 않는다(실측 bp192-s4 5·
  s4docs 2 라운드가 Luna 로 돌아 fresh-0 근거가 됐다). 본문 = `@AGENTS.md` §Worker Principles.
- 시간 예산·"상한 내 완주 여부 자가 체크" 지시를 packet 에 넣지 않는다 — worker 는
  wall-clock 을 못 감지해 추론 토큰만 낭비한다. timeout 회복은 main 이 같은 thread resume 으로
  조율하고 packet 은 시간이 아니라 범위로 좁힌다 (사용자 정정 2026-07-23; state 파일 단계-경계
  갱신 의무는 유지 — 무손실 재개의 실제 기계).

### 검수 렌즈

직원 결과는 북극성(`@.claude/rules/polar-star.md`)으로 검수한다 — 단순한 방향인가, 증상이
아니라 뿌리를 고치는가. 국소 패치·SoT 이탈이면 정정 round, 재위반이면 사용자 보고.

- worker green·map-clean·focused test 통과는 **evidence 이지 completion 이 아니다**.
  live-state/runtime/parity/security 가 correctness 를 좌우하면 closure 전 falsifier 류
  검토로 confirm 한다 (`@docs/adr/340-coding-agent-instruction-surface-governance.md` §D7.4).
- legacy 제거·졸업·SoT 단일화 작업에는 **liveness 렌즈**를 추가한다 (이때만):
  - "어디서든 참조됨" ≠ "production 진입점에서 도달 가능" — 한 번은 dead legacy 경로가
    "참조가 있다"는 이유로 13라운드 감사를 통과했다.
  - 모듈이 아니라 심볼 단위로 본다. live 모듈 안의 dead 심볼은 dead.
  - retired 경로의 benchmark·test 는 caller 로 쳐주지 않는다.
  - "residue 0" 은 완료 선언이 아니라 evidence 를 요구하는 신호다.

### 얇은 사장 — 검수·보고 기본 모양 (위 §얇은 사장 델타)

- 1차검수 위임 시 main 의 소스 정독을 기계 증거 확인으로 대체한다: definite_files 대조,
  inventory diff, rerun log, 삭제/이동 sweep. 보고 문장이 아니라 artifact 를 본다.
- 위험이 낮으면 bounded spot-check 로 닫고, live/runtime/parity/security/DB/대량삭제/공개
  계약/다중-worker 통합이면 fresh falsifier post packet 을 연다 — 신규 검수 역할을 발명하지
  않는다. 마감 파생작업 감사는 `/closure`.
- 보고 기본 모양: Status / verdict / decisive evidence 좌표 / 검증 명령+결과 / residual risk,
  40줄 안팎. parent 지정 shape 와 agent 정의의 exact shape 가 이 기본값보다 우선한다.
- dispatch 와 wake 는 묶어 일괄 판정한다. 단 red test·destructive/DB/live/security 위험·user
  decision·scope 충돌·lock 실패는 즉시 처리한다.
- 표본 심층검수 비율은 durable rule 로 박지 않는다 — 최근 직원 신뢰도·위험도에 따른 세션
  운영값이다.

### 출구 delta — 최종 보고의 의도 정렬 확인

최종 보고에서 **사용자 원문의 핵심 구절 발췌 옆에 내가 한 일 한 줄**을 놓는다 — 단 **내가
추정으로 일했거나 산출이 원문과 어긋날 때만**. 정렬된 작업이면 침묵한다(비용 0). 발췌는 전체
인용이 아니라 어긋난 지점을 담은 짧은 구절(한 줄 이내)이다 (사용자 룰링 2026-09-02 — "원문
다 적으면 보고 양이 많아서 압축/간결화 해도 될 것 같은데"). 금지선은 하나 — **발췌를 의역하지 않는다**:
사장이 이해한 대로 고쳐 쓰면 어긋남이 같이 사라진다. 발췌 ≠ 의역. 위치 판단(사용자 위임): 이 절이 SoT 고 `@CLAUDE.md` §Communication 은 포인터만 둔다 — 필수 항목화하면
매 보고 형식 채우기가 된다.

- 왜: 의도 어긋남은 산출물이 멀쩡하고 방향만 틀린 종류라 파일 목록·검증 표에는 안 보이고
  원문 옆에 놓으면 자명해진다. 문서 템플릿 칸은 기각됐다 — 병이 나는 자리가 아니다 (사례·기각
  근거 = `@docs/ideas/079-value-intent-section-first-class-citizen.md` §검토 결과).
- 입구 쪽 짝 = 첫 응답 문장: fan-out·구현 전에 "당신은 X 를 물었고 나는 Y 를 하려 한다" 한
  문장 (`@.claude/rules/behavior.md` §질문과 승인 첫-프레임 조항이 그 자리).

### AIR 공통 지침 (포인터만)

직원 고용·검수에 늘 영향을 주는 AIR 지침은 import 로 본다 — 내용을 여기 옮기지 않는다.
문서 길잡이 = `@docs/architecture/README.md` → owning contract → ADR (순서 = `@CLAUDE.md`
§SoT 결정순), gap 길잡이 = `@docs/architecture/code-gap-inventory.md`, 검사기 =
`@scripts/branch-surface/`, Claude reference 분화 경계 =
`@docs/architecture/pipeline/claude-reference-divergence-boundary.md`.

## PC2 레인 — CLOSED (2026-06-25, 운영 종료)

**PC2 운영은 종료됐다** — producer·흡수 폴·PR 흡수/notify/발행 lane 전부 비활성.
**PC2 는 영구 종료이며 다시 켜지 않는다(재개 전제 없음, 사용자 확정 2026-06-25).**
향후 작업은 PC2 가 가동 중이라고 가정하지 않는다. 종료 사실·정산·구 lane 상세 SoT =
`@docs/fable_to_opus_260613/PC2-OPERATION-CLOSED-2026-06-25.md`.
