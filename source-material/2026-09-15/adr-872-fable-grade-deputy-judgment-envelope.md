# ADR-872: 위임 lane 개정 — Fable-급 codex 사장의 재량 envelope·STOP·판정 로그, VP 모델 dial, Opus 자리

저작 모델: claude-fable-5-1

## 상태
- [x] 확정 (Accepted) — 2026-09-05. VP(gpt-6-astra) 2라운드 후 착지 (사용자 지시 "이거 하고 적용까지 다 해놔").

## 날짜
2026-09-05

## 맥락 (Context)

(초안 2026-09-04 → astra 도달 확인·VP r1 반영 개정 2026-09-05.)

사용자 보고 (2026-09-04): OpenAI gpt-6 (astra) 가 Fable 동급 추론 벤치마크로 출시됐고, codex 구독은
같은 요금제에서 Claude 대비 실효 토큰 총량이 약 3배이며, 계정 구성은 조정 여지가 있다. 질문 =
작은 사장·VP·위임 규칙·작업 방식을 이 구도에 어떻게 맞출 것인가.

현행 위임 구조(`@.claude/rules/delegation.md`)에서 판정 권위는 **main 좌석**(Fable 기본·Opus 병행 —
`@CLAUDE.md` §Tool And Delegation)에 있고, 직원·작은 사장은 선지급 룰링을 집행하며 판단 지점에서 STOP 반환한다.
goal packet 은 "실행자 추론이 저작자보다 한 단계 낮다" 전제로 저작된다 (`@docs/goal_packets/CLAUDE.md`
§실행자 눈높이). 이 비대칭은 모델 고도 하나가 아니라 좌석·사용자 참석·transport·예산이 함께 굳힌 것이다
(VP r1 F06 정정). Fable-급 모델이 codex 풀에 오면 그중 **모델 고도 축**이 사라지고, 판정권 배분의 기준을
다시 물어야 한다.

판단 재료 = 문서축·장부축 두 직원 census (`@docs/report/delegation-lane-evidence-astra-2026-09-04.md`,
좌표 전문) + VP r1 (`/var/tmp/agent-scratch/codex-results/adr872-vp-astra-r1/report.md`, 추기 참조). 결정에
실린 사실:

- **STOP 반환의 다수는 사장 판정 오류가 아니다.** 캠페인 17건(07-20~09-03)에서 STOP 사유 주류 = 모델-가시
  문안 결정(사용자 몫)·packet 이 안 정한 경계·좌표/provenance 오류. main 이 사장 판정을 뒤집은 건 소수
  (BP-125 분류·red-burndown frame·BP-128 adapter; BP-142 R6 선주장은 R7 falsifier 반례로 정정 — main 귀속
  아님). 결정-변경 finding 의 공통 단위 집계는 09-02 nightly census 하나: ① 11건 중 공용 상태 오염 9,
  그중 두 쓰기 권한(ledger resolve·완료 stamp)에서 6 (docs-axis Q2).
- **VP 는 실사용이었다.** checkpoint 14건 (Opus VP 9 · codex VP 5, 07-26~09-02), Opus VP 가 "격침"·설계 변경
  7~9건·당일 재판정을 낸 기록 다수 (CP-1708·1730·1731·1736·1745·1756·1760). 같은 family 가 이만큼 잡았으므로
  "교차 family 라서 값이 있다"는 근거는 지지되지 않는다 — VP 의 값은 fresh 전체-frame 검토 자체다 (Q3).
- **codex 토큰은 2단에 쓰인다.** 최근 21일 codex rollout 38.9B 토큰(97.3% cached) 중 deputy 계열(사장+직원)
  = 분류 가능 delegated total 의 86.9% (전체 선택 토큰 기준 86.5%). 모델 sol 98.5%·luna 1.4% (T3).
- **위임 장부 480행**: 라운드 ≥4 = 174, ≥7 = 70, 최대 16. `findings`·`saturation` 은 자유값이라 finding 부류
  분포를 장부에서 derive 할 수 없다 (T2).
- **codex lane 은 ADR-666 이후 안정**: 주간 cancelled 1.4~4.6% (구 12~15%), launch_failed 0. 잔여 = 외부
  (auth·usage-limit·resume 소실) (T6, Q4).
- **astra 도달 (2026-09-05)**: 정식 slug `gpt-6-astra` (카탈로그 등재, `codex exec -m gpt-6-astra` OK; `gpt-6`
  등 다른 slug 는 400). 지원 effort low·medium·high·xhigh·max·ultra(자동 위임). 09-04 에는 카탈로그 부재·400.
- **요율 (VP r1 F09, 공식 가격표)**: astra 표준 크레딧 = sol 의 **2.5배** (입력 250/캐시 25/출력 1,250 vs
  100/10/500 per 1M). 동일 토큰 구성·동일 예산이면 "Claude 대비 3배" 전제는 astra 에서 **약 1.2배**. 포함
  구독 한도의 실제 소모율은 미측정.
- **사용자 제약·방향 (09-04)**: Fable 은 Claude 사용량의 절반까지 → 나머지는 Opus 가 채운다(놀리지 않는다).
  astra VP 직접 시도 희망. "당장은 Fable 주력 + astra 작은 사장의 권한·판정 범위 확대". STOP 주류(packet
  구멍·문안·사실 오류)는 직원이 알아서 처리하되 "3종 전부 Opus 까지"는 과함 → 층별 세분화.

## 결정 (Decision)

판정권 배분 기준을 **추론 고도에서 문맥 소유로** 옮긴다. packet 에 담기는 결정은 Fable-급 사장이 재량으로
하고, 사용자 의도·세션 대화·기결정 맥락이 필요한 결정만 main 으로 반환된다. lane 지도(1단 Opus one-shot /
2단 codex 사장 / closure Opus)와 단일 최종 권위(main)는 바꾸지 않는다 — 바뀌는 건 2단 사장의 **재량 범위**,
VP 의 모델 dial, Opus 의 자리 목록이다. 문맥 소유는 단일 순위가 아니다: main 은 사용자 목적·금지선·타
캠페인 비용을 더 알고, 사장은 현재 구현·반례·수리 경로를 더 안다 — 그래서 기결정 충돌은 반환이다(VP r1 A).

### D1 — Fable-급 사장 게이트 + 재량 envelope

- **게이트**: 2단 codex 사장이 **사용자가 Fable-급으로 지정한 모델**(현재 `gpt-6-astra`)로 돌 때만 envelope
  이 열린다. wrapper 는 `deputy-*` 출력 이름에 사장 모델을 자동 배정한다 (§영향 dial). 다른 모델의 사장은 현행
  규율(선지급 룰링 + STOP 반환) 그대로.
- **어휘 분리 (VP r1 F01 채택)**: falsifier finding 등급 ①/②(완료를 바꾸는 결함 / 그 자리 수정)와 사장의
  **권한 분류**는 다른 축이다. 사장 scope·검증 기준 안의 ① 결함(예: BP-142 lock 오해제 — 기존 불변식 집행)은
  사장이 **수리하고 반증**한다 — STOP 이 아니다. STOP 은 권한 밖 **결정**이다.
- **재량 결정 (사장 자율)**: 구현 design knob — 모듈 내부 구조·테스트 shape·에러 *표현*(메시지·로그 형태)·규약
  안 명명·보존 일수·allowlist 모양·직원 fan-out·직원별 모델·라운드 수·packet 이 안 정한 **국소** 구현 경계.
  정하고 한 줄 근거를 판정 로그(D2)에 남기고 진행한다. 실패 *의미*(예외→sentinel·retry·rollback 위치·검증
  oracle)는 재량이 아니다 — 의미·safety·검증 계약이라 ⑵⑶ 로 간다 (VP r1 C).
- **STOP 사유 4종** (반환 packet 밀도 규율은 현행 그대로): ⑴ 사용자 몫 4부류·hard wall — 이름·문안(base 표면) /
  외부 입력 / 사용자 룰링 reopen / 차단·승인·prod·데이터 손실·secrets ⑵ **기결정 충돌** — packet 선지급 룰링·
  accepted ADR·owning contract·사용자 룰링을 뒤집을 증거. 뒤집지 않고 증거 + 충돌 좌표를 들고 반환. **판별
  불가**(근거 자료 부재·서로 유효한 지시의 충돌)도 재량으로 증명된 게 아니라 여기로 (VP r1 B) ⑶ **ADR 감
  결정** — `@docs/CLAUDE.md` §ADR 판단 기준(public contract·schema·safety·pipeline 단계·기존 설계 뒤집기)에
  걸리는 결정이 새로 필요해진 경우 ⑷ **수렴 실패** — 라운드 N 미달 시 반환(현행 delegation.md 그대로 — VP r1
  F05 정정); 같은 이음새 변종 반복은 반환 packet 에 구조 수렴 신호로 표기.
- **packet 의무 = 유효 판정 목록**: 선지급 룰링 + 그 영역 ADR·owning contract 좌표. 목록 없이는 ⑵ 를 판별할 수
  없으므로 목록 없는 envelope packet 은 저작 미완. 목록의 존재는 사용자 의도가 다 담겼다는 증명이 아니다 —
  권위 소스 재유도(frame check)와 실제 효과 확인(D2)이 함께 남는다.
- **왜**: STOP 의 다수가 packet 구멍이었다(맥락). 사장은 그 자리에서 멈추거나 조용히 메꾼다 — 후자가 "codex
  위반 = spec gap" 부류의 뿌리다. envelope 은 그 메꿈을 **허용하되 로그로 가시화**한다. 값은 "덜 틀린다"가
  아니라 STOP 을 로그된 결정으로 바꿔 main 왕복을 줄이는 데 있다. 다만 로그 허용이 전역 의도를 자동 보존하지는
  않는다(VP r1 A) — 그래서 D2.

### D2 — 판정 로그 + 검수 (main 의 결정적 증거 spot-check 는 불변)

- **판정 로그**: 재량 결정마다 한 행 — 결정 · 기각한 대안 · 왜 · 정합한 ADR/계약 좌표 · 되돌리기 비용. 사장
  최종 보고(`deputy-*`)의 고정 절 `## 판정 로그` (표). 장부 필드 신설은 하지 않는다 — ADR-583 장부의
  `findings`·`saturation` 이 자유값으로 썩은 실측(T2), 판독자 = main 한 명 (ADR-756).
- **내장 falsifier 는 코드와 판정 로그 둘 다** 공격한다 (frame check round 0 상속 그대로).
- **반환 시 검수 (VP r1 F03 채택 — 선례 ADR-698 D1·delegation.md "decisive-evidence spot-check 불변" 준수)**:
  ① main 은 판정 로그 **전체**를 읽는다 — 짧게 유지하는 것이 사장 의무이고, 길면 그 자체가 재량 과다 신호 ②
  main 의 결정적 증거 spot-check(DB 행·artifact 재확인)는 현행 그대로 ③ **Opus fresh falsifier 1회**가 최종
  반환물의 판정 로그와 **실제 효과**(writer·reader·동시성 반례·원문 대조)를 함께 반증한다 — 로그 정합만 보는
  별도 "1차 검수" 호출은 두지 않는다(같은 오류를 상속하는 요약-재요약; 초안의 Opus 1차 검수 자리 폐지) ④
  closure 현행.
- **envelope dial = 정성 판독**: 캠페인 2~3개 뒤 main 이 (a) 뒤집은 행 (b) falsifier 가 잡은 **로그 밖 효과**
  두 축을 읽는다 — 낮은 뒤집기율 단독은 품질·선별·노출을 구별 못 한다(VP r1 D). 드물면 유지·확대, 특정 부류
  반복이면 그 부류만 STOP 복귀.

### D3 — 풀 안의 모델 선택 = 사장 재량, falsifier 는 사장 모델 상속

> ⚠️ 추기 2026-09-07 (4) 로 개정 — 직원 기본 = Luna/max (`[agents]`), Sol 직원 = 판정 조각·판정 역할 예외(model+effort
> 쌍 명시), falsifier = Sol/xhigh toml pin. 아래 본문은 당시 결정.

- 사장이 난이도를 보고 직원 모델을 spawn 시 지정한다 (공식: 하위 에이전트별 model·reasoning 지원, 미지정 시
  부모 상속): 기계 물량·sweep·재녹화 = luna, 통상 구현 = sol xhigh, 판정 밀도 하위 작업 = Fable-급.
- **Luna 추론 수준 개정 (사용자 결정 2026-09-06, Codex 소진 재조정 대화)**: “luna는 싸서 항상 max 추론
  능력으로 부르면 좋겠어. 앞으로도 그렇게 하게끔 해”. 코딩 직원으로 Luna를 선택하면 신규·재개·재발주 모두
  `max`를 명시한다. 모델 선택 재량과 별개이며 부모·wrapper 기본값으로 낮추지 않는다. 집행 =
  @.claude/rules/delegation.md §작은 사장, @AGENTS.md, @CLAUDE.md, codex prompt boilerplate.
  호출기 집행은 @scripts/codex-mcp-server/lib.mjs의 Luna 추론 정규화이며, 기존 model-config·service-mode-runner
  검사에서 실제 CLI·결과·시작 메타데이터의 `max`를 확인한다.
- **작업별 추론 노력 가변안 기각 (같은 대화, 사용자 결정 2026-09-06)**: “추론 노력을 가변시키는건 기각.
  그냥 추론노력까지 조정하지 않고 model 지정만 생각하면서 쓴다”. 작업마다 선택하는 축은 모델뿐이다.
  Luna는 `max`, 다른 모델은 사용자 재조정 전까지 현행 고정값을 유지한다. 난도·비용에 따른 effort
  승강은 운영 선택지로 두지 않는다. 집행 = 위임 SoT와 AGENTS.md·CLAUDE.md의 모델 선택 규칙.
- **named role 의 TOML pin 은 spawn override 를 받지 않는다** (VP r1 F08). 그래서 `.codex/agents/falsifier.toml`
  의 `model` pin 을 **제거해 부모 상속**으로 바꾼다 (공식 우선순위 = 역할 TOML pin > 명시 spawn 지정 >
  `[agents]` 기본값 > 부모 상속 — 현행 로컬 설정엔 앞 둘이 없어 부모 상속으로 동작, VP r2 R2-01). astra
  사장의 내장 falsifier 는 astra, sol 부모 lane 의 falsifier 는 sol — 단 `~/.codex/config.toml` 최상위 모델이
  2026-09-05 `gpt-6-astra` 로 바뀌어 codex-main 세션의 falsifier 도 astra 다(비용 동반). 이것이 "판정 falsifier ≥ 사장 급"의 시험 기본값 구현이다 — **영구 의무가
  아니다**: Opus VP 가 Fable 설계를 반증한 실적은 "약한 모델은 generic risk 만 낸다"는 일반화를 반박한다(VP r1
  D). 2~3 캠페인 뒤 sol falsifier 대비 비교 가능하면 완화한다. 다른 roster pin(closure 등)은 손대지 않는다.

### D4 — VP 모델 dial (시험 중)

- **호출 조건**: Fable 판단 필요 신호 ②(설계가 갈리고 오래 묶이는 결정) + main 이 고도에서 2차 의견을 원할 때.
  작업마다 부르지 않는다 — 비용은 호출 빈도 문제. 상한 2왕복은 **같은 결정** 기준(ADR-340 advisor cap 정합).
- **모델**: `gpt-6-astra` codex fresh one-shot (`/codex-bg` audit, `vp-*` 출력 이름 → wrapper 가 VP 모델 자동
  배정; QA 어휘 — 공격 프레이밍 packet 은 codex 필터 오탐 실측). 첫 사용 = 이 ADR 의 r1 (추기).
- **기대치**: Opus VP 실적(9건)은 보장 하한이 아니라 **비교 기준**이다. 값은 fresh 전체-frame 검토에서 나오고
  교차 family 는 "다른 오차의 가능성"이지 독립성 증명이 아니다 (VP r1 E). 판독 = 2~3회 서로 다른 결정에서
  "없었으면 어떤 결정을 했고 이 증거로 무엇이 달라졌나"가 구체적인가 — 발견 수 경쟁 금지.
- 설계권·완료 판정 main 단독 불변 — 사실은 적용, 설계 의견은 점별 판정, 통째 뒤집기·deference 금지.

### D5 — Opus 자리 셋 (Claude 몫 절반 원칙)

> ⚠️ 추기 2026-09-07 (4) 로 개정 — Opus 1단 = **작은 크기**(중간 이상·애매 = codex), 절반 원칙은 Fable ≤ 50% 상한만
> 존치(채움 의무 은퇴). 아래 본문은 당시 결정.

1단을 codex 로 내리는 안은 **철회** — Fable 은 Claude 사용량의 절반까지라 나머지는 Opus 가 채워야 한다
(사용자 제약). 09-02 두 병목·두 레버 배치 불변. Opus 의 자리:

1. **1단 one-shot 직원** (현행 default, **중간 규모 구현까지** — 좁혀 읽지 않는다, VP r1 F).
2. **closure·front-closure** (사용자 지시 2026-08-03).
3. **사장 반환물 교차 family 반증 1회 — 판정 로그 + 실제 효과** (D2 ③).

(초안의 "판정 로그 1차 검수" 자리는 D2 로 합병·폐지. + journey-round-boss 예외는 ADR-698 그대로.) 절반
원칙은 **놀리지 말라는 제약**이지 자리를 발명할 근거가 아니다 — 균형은 소진 관측 dial(delegation.md §두
병목)로 본다. 요율 2.5배(맥락)로 "3배" 전제가 1.2배로 줄었으므로 계정 재배분은 astra 의 작업당 실소모·왕복
감소 실측 뒤 사용자 결정.

### D6 — 같은 작업의 낡음 수리 (② 부류, 09-04 반영 완료)

delegation.md "429건 중 7라운드+ 40건" → 480/70 · AGENTS.md 판별선(09-02 이전 문면) twin 동기 ·
`docs/user-agent-communication/boss-mode.md` VP 줄 · ADR-340 D6 낡음 표시 · CP-1765 "9건/10건".

### D7 — 자율 처리 3종의 층별 배분

사용자 관찰: STOP 의 주류인 **packet 구멍·문안·사실 오류**가 멈춤과 양방향 소통을 낳아 토큰·시간을 가장
많이 먹는다 — 직원이 알아서 처리할 권한을 주고 싶다. 단 "3종 전부 Opus 까지"는 과함 → 세분화. 기준 = **그
층에 검수 기계가 어디 있는가**: 1단 Opus one-shot 의 falsifier 는 packet 이 선택해 붙이는 외부 1회(기본)이고,
2단 사장은 내장 포화검수를 가진다; sol 사장은 내장은 있으나 판정 실증이 약하다(docs-axis Q5). 자율 범위 =
되돌리기 싸고 파급이 국소인 것까지가 Opus·sol 몫, 공용 계약을 건드리는 **미결 선택**은 Fable-급 사장까지.

| 부류 | Opus 1단 · sol 사장 | Fable-급 사장 | 항상 STOP |
|---|---|---|---|
| **사실·좌표 오류** (packet 의 좌표·전제가 낡음) | 권위 소스에서 재유도 후 진행, 정정 기록(원문→정정+근거 좌표) | 같음 | 정정이 범위 열거(frame)를 바꾸면 ⑵ |
| **packet 구멍 — 국소** (모듈 내부 구조·테스트 shape·에러 표현·규약 안 명명; 공용 상태 미접촉) | 스스로 정하고 판정 로그 한 줄 | 같음 | 실패 의미·검증 oracle 변경은 국소가 아님 |
| **packet 구멍 — 공용 미결 선택** (공유 어휘·cross-layer shape·공유 상태 기계·public surface) | STOP | 재량 + 판정 로그 (D1) | ADR 감 결정·기결정 충돌 |
| **문안 — 비-base** (오류·거절 reason·안내문·tool result·UI copy) | rubric(ADR-775·777·error-taxonomy §저작 규범) 대로 초안 저작 + `문안 초안` 표시 → Fable 일반 검수 | 같음 | — |
| **문안 — base prompt·agent 지시문·function description·runtime 주입 블록·이름** | STOP | STOP | 사용자·Fable (CLAUDE.md §Fable Prompt 정련) |

- **국소/공용 분류기 = 등기부 양성 판정 + 효과 질문** (VP r1 F02 채택): `@docs/architecture/state-concurrency-classes.md`
  의 부류에 걸리면 공용. **등기부에 행이 없다고 국소가 아니다** — writer·reader·효과가 파일·프로세스·세션
  경계를 넘으면 공용으로 본다 (nightly 실측: 등기 0행이었으나 공용 영향 실재).
- **기존 계약 집행은 이 표의 대상이 아니다**: 이미 허가된 shared primitive 를 정해진 인자로 호출하거나 기존
  계약 위반을 기계 수리하는 것은 "공용 구멍"이 아니다 — 표는 **미결 선택**의 권한표다 (VP r1 C).
- **비-base 문안은 이미 codex·Opus 저작이 정책** (CLAUDE.md §Fable Prompt 정련 2026-08-25). ADR-680 캠페인의
  문안 STOP 은 packet 이 저작을 금지해서였다 — 이 칸은 **packet 저작 규율 수리**(Fable 이 불필요한 금지문을
  쓰지 않는다)이며, 이미 발주된 packet 의 명시 금지를 직원이 스스로 무시하는 규칙은 아니다.
- **사실 오류 처리는 판정이 아니다** — falsifier round 0 의 권위 소스 재유도를 직원에게도 시키고 기록만 남긴다.
  단 사실 정정 권한과 채택 설계 폐기 권한은 다르다 (BP-128: ExpressionRef 사실은 재유도 가능, adapter 폐기는 ⑵).
- 직원의 red-ledger·검증 의무(boilerplate·AGENTS §Testing)는 이 표와 무관하게 그대로 상속된다.

### D8 — 적용 범위: 세션 내 작은 사장·1단 직원만, goal packet 은 현행 (VP r1 F04 채택)

D1·D2·D7 은 **세션 내 codex-bg 작은 사장**(codex 사장 + 그 직원)과 **1단 직원(D7 왼쪽 열)**에 적용된다.
**goal packet**(사용자 발주·무인 소화, `@docs/goal_packets/CLAUDE.md`)은 현행 계약 그대로 — 선지급 완결성
(실측 커버리지), HQ 수신함 경유 규칙 변경, 규칙 밖 = structural(파킹/보고), rulebook 발주 후 불변. 이유: 무인
run 에는 STOP 을 받을 main 이 없어 envelope 의 반환 의미가 성립하지 않고, 판정 로그의 판독자도 없다. 실행자가
Fable-급이어도 §실행자 눈높이의 "선지급" 규율은 유지한다 — 바뀌는 것은 그 절의 "한 단계 낮다"는 이유 문장뿐
(포인터 한 줄로 이 ADR 을 가리킨다).

## 선택지 (Alternatives Considered)

| 선택지 | 장점 | 단점 |
|--------|------|------|
| A. drop-in — 사장 모델만 astra, 규칙 불변 | 가장 싸다; 모델 효과 분리 관찰 | STOP 구조가 그대로라 Fable 왕복이 안 준다 (맥락: STOP 다수 = packet 구멍) |
| **B. Fable-급 사장 + 재량 envelope + 판정 로그 (채택, D1·D2)** | 병목 ①(Fable 판정 왕복)·②(Claude 총량) 동시 완화; 기존 분류기(ADR rubric·등기부) 재사용; "조용한 메꿈" 가시화 | 사장 결정이 main vision 과 어긋날 위험 — main 전체 로그 읽기 + 결정적 증거 spot-check + Opus 교차 반증(로그+효과)으로 관리 |
| C. astra VP 즉시 + Opus VP 폐지 | 사용자 희망 | Opus VP 실적(9건)이 강해 폐지 근거 없음 → dial + 비교 기준 (D4) |
| D. 1단 조사·구현도 codex(astra) 로 | codex 토큰 활용 | **철회** — Opus 절반 원칙; 요율 2.5배로 이득도 1.2배 (D5) |
| E. astra main 세션 병행 + 계정 재배분 | 가장 큰 레버 | codex main 은 memory 자동 주입·hook·front-closure·journey boss·마패 없음(docs-axis Q7); 작업당 실소모 미측정 → B 실측 뒤 재론 |
| F. envelope 을 sol 사장에 지금 개방 | 즉시 가능 | sol-era 과확장 실증 2회(Q5) → 게이트 유지, 사용자 dial |
| G. packet 저작 규율 수리 + D7 왼쪽 열 + 판정 로그만 (게이트 없음) — VP r1 H 비교안 | 부품 최소; 이미 허용된 문안·사실 정정 왕복을 줄임 | **공용 미결 선택을 사장이 즉시 결정하는 범위는 얻지 못함** — 그 범위가 astra 사장의 값이라 B 를 택함; G 는 B 의 부분집합으로 흡수 |
| H. Opus 로그 1차 검수 별도 호출 (초안 D2) | 독립 판독자 +1 | 로그 정합만 보는 검수는 같은 오류를 상속; census 에 그 호출만이 잡는 결함 부류 없음 → D2 ③ 한 호출로 합병 (VP r1 F03·D) |

## 근거 (Rationale)

- **판정권의 기준이 문맥 소유인 이유**: main 의 고유 자산은 사용자와 대화하는 좌석·memory·지침 corpus 다.
  동급 모델은 packet 밖 문맥을 못 가지므로 "packet 에 담기는가"가 유일하게 안정적인 경계다. Fable 은퇴 전제
  없음(사용자 확정 2026-07-21)과 정합 — 역할이 좁아지는 것이지 자리가 없어지는 게 아니다. 문맥은 양방향이라
  (사장 = 구현 문맥 우위) 기결정 충돌은 반환이고 로그는 증거이지 권위가 아니다 (VP r1 A·G).
- **어휘를 새로 만들지 않되 축은 섞지 않는다**: ①/② 는 finding 등급으로만 쓰고 권한 분류는 "재량 / STOP
  사유 4종"으로 적는다 — 섞으면 scope 안의 ① 결함까지 반환된다 (VP r1 F01). 분류기는 기존 것(ADR rubric·
  등기부)을 재사용하고 등기부에는 효과 질문 한 줄만 보탠다.
- **검수는 선례를 축소하지 않는다**: ADR-698 D1 도 main 의 결정적 DB spot-check 를 남겼다. Fable 고도는 "코드
  대신 짧은 로그"로 지키고, 결정적 증거 확인은 그대로 둔다 (VP r1 F03).
- **VP 교차 family 는 시험이다**: Opus VP 9건이 결정-변경 다수를 냈으니 astra 의 값은 실측 전 가설이다. 첫
  실측(r1)은 ① 3건·② 6건 — 채택 전량 (추기).
- **선례**: ADR-698 D1 (Opus 회차 사장 = 1차 판정 / main = spot-check) 이 bounded 재량의 실증 선례이며, 이
  ADR 은 그 모양을 2단 codex 사장에 일반화한다. ADR-340 D6 의 결정 부류(사용자 vs main+VP 자율)를 사장 층으로
  한 단 내린다.

## 영향 (Consequences)

- **dial 현행값 (2026-09-05)**: wrapper `codex-bg.sh` 역할별 모델 기본값 — `deputy-*` → `CODEX_MCP_DEPUTY_MODEL`
  = `gpt-6-astra`, `vp-*` → `CODEX_MCP_VP_MODEL` = `gpt-6-astra`, 그 외 = `gpt-5.6-sol`; `resume` 은 registry 에
  기록된 그 thread 의 모델을 이어받고(closure ①-1 수리), 호출 env 의 비어 있지 않은 명시 `CODEX_MCP_MODEL` 이
  이긴다 (`health | jq .role_models`; 검사 = `scripts/codex-mcp-server/test/service-mode-runner.test.mjs`
  "deputy-*/vp-* outputs inherit their role model"). 착지 2026-09-05.
- **착지 좌표 (2026-09-05 착지 완료)**: `.claude/rules/delegation.md` §작은 사장(재량 envelope·STOP 4종·판정 로그·검수·dial
  — 문안 = 아래 부록)·§Opus 직원(자리 셋)·§부사장(호출 조건·모델 dial)·§좋은 위임 prompt 의 모양(유효 판정
  목록·불필요 금지문 금지·D7 처리 기록 절) · `CLAUDE.md` §Tool And Delegation 요지 1 bullet · `AGENTS.md` §Tool
  And Delegation twin(영문 envelope 단락 — D7 은 단락형 열거 — + VP dial) · wrapper
  `scripts/codex-mcp-server/codex-bg.sh`(`_apply_role_model`·`_thread_model_from_registry`)·`codex-control.mjs`(health
  `role_models`)·`test/service-mode-runner.test.mjs`·`.claude/skills/codex-bg/SKILL.md` §Run 양식 ·
  `.claude/skills/codex-bg/codex-prompt-boilerplate.md`
  §작은 사장 캐스팅(재량 envelope 의미 + D7 — codex 사장이 실제로 읽는 표면) · `.codex/agents/falsifier.toml`
  model pin 제거(부모 상속) + `.codex/agents/README.md` 소유 문장 caveat · `docs/goal_packets/CLAUDE.md`
  §실행자 눈높이 포인터 한 줄(D8) · interventions.jsonl 1행 · memory 갱신.
- **잔여 위험**: ⑴ astra 작업당 실소모·포함 한도 소모율 미측정 — 요율 2.5배라 "3배" 이득은 1.2배 전제; astra
  가 더 적은 토큰으로 끝내는지가 실측 대상 ⑵ 뒤집기율·로그 밖 효과 판독은 정성 — main 이 캠페인 2~3개 뒤
  실제로 읽어야 dial 이 움직인다 ⑶ 판정 로그 없는 반환 = 미완 규율은 packet 저작자(main) 몫 ⑷ falsifier
  상속으로 astra 사장 캠페인의 codex 크레딧이 사장+falsifier 둘 다 2.5배 — 첫 2~3 캠페인에서 sol 대비 실측.
- **재검토 트리거**: 첫 2~3 astra 캠페인 뒤 (뒤집기·로그 밖 효과·소모) · 사용자가 Fable/Opus/codex 소진 속도로
  배분을 재조정할 때 (산정식 재산정 — astra 요율 반영).

## 부록 — 착지 문안 원안 (delegation.md §작은 사장, v2 — 2026-09-05 착지본은 delegation.md 가 SoT)

```text
- **Fable-급 사장의 재량 envelope (ADR-872) — dial: wrapper 역할 기본값 (`deputy-*` → 사장 모델)**: 사장이
  사용자 지정 Fable-급 모델로 돌 때만 연다. 열리면 판정권 기준이 추론 고도에서 **문맥 소유**로 바뀐다 —
  packet 에 담기는 결정은 사장 재량, 사용자 의도·세션 대화·기결정 맥락이 필요한 결정만 main 반환. **어휘**:
  falsifier finding 의 ①/② 는 결함 등급이고 권한 분류가 아니다 — scope 안의 ① 결함은 사장이 수리·반증한다.
  **재량 결정** = 구현 design knob(모듈 내부 구조·테스트 shape·에러 표현·규약 안 명명·직원 fan-out·직원별
  모델·라운드 수·packet 이 안 정한 국소 구현 경계) → 정하고 한 줄 근거를 판정 로그에. 실패 의미(sentinel·
  retry·rollback·검증 oracle)는 재량 아님. **STOP 사유 4종** = ⑴ 사용자 몫 4부류·hard wall ⑵ 기결정 충돌
  (선지급 룰링·accepted ADR·owning contract·사용자 룰링을 뒤집을 증거 — 뒤집지 말고 증거+충돌 좌표로 반환;
  판별 불가도 여기) ⑶ ADR 감 결정(docs/CLAUDE.md §ADR 판단 기준) ⑷ 수렴 실패(라운드 N 미달 — 현행). packet
  의무 = **유효 판정 목록**(선지급 룰링 + 그 영역 ADR·계약 좌표; 없으면 저작 미완). **판정 로그** = 사장 최종
  보고 `## 판정 로그` 표(결정·기각 대안·왜·정합 ADR/계약·되돌리기 비용) — 장부 필드 신설 없음. 내장
  falsifier 는 코드와 판정 로그 둘 다 공격(falsifier 모델 = 사장 상속). 반환 시 검수 = main 이 로그 **전체**를
  읽고(짧게 유지 = 사장 의무) 결정적 증거 spot-check 는 현행 그대로 · Opus fresh falsifier 1회가 로그 + 실제
  효과를 교차 family 로 반증 · closure 현행. **dial 판독** = 캠페인 2~3개 뒤 main 이 뒤집은 행 + falsifier 가
  잡은 로그 밖 효과를 정성 직독 — 드물면 유지·확대, 특정 부류 반복이면 그 부류만 STOP 복귀. 풀 안 직원
  모델은 사장 재량(기계 물량 luna · 통상 sol · 판정 밀도 Fable-급). 적용 = 세션 내 작은 사장(+1단 직원 D7
  왼쪽 열); goal packet 은 현행(ADR-872 D8). 왜: STOP 반환의 다수가 사장 판정 오류가 아니라 packet 구멍·
  문안·사실 오류였다(17 캠페인 census) — envelope 은 "조용한 메꿈"을 로그된 결정으로 바꿔 main 왕복을 줄인다.
```

### 추기 — VP 1라운드 (gpt-6-astra, xhigh, audit, 2026-09-05) 처분표

첫 astra VP 호출. 소요 20분, 반환 = 본문 ①3·②6 + 부록(0라운드 frame diff·축 A~I·기각 대안 12·사장 질문 4).
main 점별 판정:

| VP finding | 판정 | 반영 |
|---|---|---|
| F01 ① ①/② 결함 등급 = 권한 분류 동일시 → scope 안 ① 결함까지 반환 | **채택** | D1 어휘 분리("재량 / STOP 사유"), 부록 v2 |
| F02 ② 등기부 행 없음 ≠ 국소 | **채택** | D7 분류기 = 양성 판정 + 효과 질문 |
| F03 ① Fable 이 표시 행만 읽으면 main spot-check 선례 축소 | **채택** | D2: 로그 전체 + 결정적 증거 spot-check 불변; Opus 1차 검수 → 교차 반증 1회에 합병 |
| F04 ① goal packet 적용 범위 미정 | **채택** | D8 신설 — 세션 사장·1단만, goal packet 현행 |
| F05 ② STOP⑷ 문면이 현행보다 좁음 | **채택** | "라운드 N 미달 시 반환" 로 정정 |
| F06 ② "Fable 만 판정"·"1단 falsifier 없음" 사실 아님 | **채택** | 맥락·D7 근거 문장 정정 (main 좌석·1단 외부 falsifier 1회) |
| F07 ② VP 14건 = Opus 9·codex 5; BP-142 귀속; 86.9% 분모 | **채택** | 맥락 수치 정정 |
| F08 ② roster falsifier 는 sol 고정 — 사장 전환과 별개 | **채택** | D3: falsifier.toml model pin 제거(부모 상속) |
| F09 ② astra 요율 = sol 2.5배 (공식) → 3배 전제 1.2배 | **채택** | 맥락·D5·잔여 위험 반영 |
| VP 질문 1 (scope 안 ① 결함 vs 권한 밖 결정 분리?) | 예 | F01 |
| VP 질문 2 (main spot-check·전체 로그 유지? 별도 Opus 검수의 추가 검사?) | 유지; 추가 검사 없음 → 합병 | F03 |
| VP 질문 3 (goal packet 적용?) | 아니오 | D8 |
| VP 질문 4 (동급 falsifier = 시험값 or 영구?) | 시험값 (상속 구현), 2~3 캠페인 뒤 완화 판정 | D3 |
| VP H 비교안 (게이트 없이 규율 수리+로그) | 부분 채택 — B 의 부분집합으로 흡수, 공용 미결 선택 범위는 B 유지 | 선택지 G |

VP 가 기각한 대안 12건(동등 공동 설계자·spot-check 전폐·교차 family 절대론·공용 상태 전부 STOP·제5 STOP·
Opus 절반 폐기·journey/closure astra 이전·codex main 기능 부재 과장·red-ledger 의무 복제·비율 실증 요구 등)은
main 도 같은 판정 — 재발굴 금지 anchor 로 이 추기가 남는다.

### 추기 — VP 2라운드 (같은 스레드 resume, 2026-09-05) 처분 검증

소요 9분. F01~F09 **전부 해소** 판정(각 개정 좌표 명시), 개정이 들여온 새 ① **0건**, 사장 처분 이견 **없음**
(H 합병 동의 — "독립 판독자 추가 효과 미입증 ≠ 없음 입증" 경계 유지), 착지 판정 **가능**. ② 1건 R2-01 =
D3 상속의 설정 우선순위 조건(TOML pin > 명시 spawn > `[agents]` 기본 > 부모) → D3 본문 보충. 부록 B~E 에서
D3(ADR-570 주입·fresh 독립성과 무관), D2 합병(잃는 것 = 재판독 여유, 필수 검사 부류 소실 증거 없음), D8 경계
사례 4종(세션 bind rulebook·세션→goal 인계·부분 소화·무인 astra), 부록 v2↔본문 대조를 확인. 기각한 새 ①
후보 6건 기록. 원문 = @docs/report/delegation-lane-evidence-astra-2026-09-04/vp-r2.md.

**착지 감리 (codex closure, fresh 라운드, 2026-09-05)**: r2 NOT-READY ①2·②7 (①: resume 시 `--output` 부재면 사장
모델이 base 로 떨어지는 wrapper 결함 → registry 스레드 모델 상속으로 수리 + 회귀 테스트; "VP = Opus" 현행 라우팅
문장 6곳 → dial 문장으로) → r3 NOT-READY ①1·②2 (같은 family 잔여 2문장 + basename 참조·주석) → 같은 family 전수
sweep 후 r4 **CLOSE-READY ①0·②1** (주석 2곳 → 그 자리 수리). 원문 = scratch `adr872-closure-audit-r{2,3,4}/report.md`.

**astra VP 첫 실측 소감 (main)**: r1 은 frame 재유도 → 사례 통과 → 축별 판단 → 기각 대안 12 → 사장 질문 4 의
구조를 스스로 세웠고, ① 3건이 모두 실제 설계 결함(어휘 축 혼동·검수 선례 축소·적용 범위 미정)이었다. 공식 요율
·sub-agent 우선순위 같은 외부 사실을 스스로 가져와 전제를 흔든 점이 Opus VP 실적과 구별되는 지점이다.
비용 실측(크레딧)은 wrapper 가 usage 를 안 실어 이번엔 없다 — 다음 호출부터 rollout 원장에서 derive.

**VP dial 2회차 판독 (2026-09-05, idea 155 종합 검토 — 사용자 지시 "동등 co-thinker" 캐스팅)**: 없었으면 main 은
"예방→회복" 극성·②→①→③ 순서·"라운드 ↓" 판독 지표·69% 전환율 문장을 그대로 착지시켰을 것. VP 가 바꾼 것 = 방향
이름(국소성)·순서·판독 지표·사실 정정 2·소화력 실측(codex 직원 3, read-only). r1 14분·r2 11분, repo 편집 0. 구체적
→ dial 유지. 원문 = @docs/report/vp-idea155-direction-2026-09-05/r2.md, 판정 = idea 155 추기 2. 이번 캐스팅은 D4
"공격 프레이밍" 이 아니라 "전체 입장 + 넌 어때" 였고 write 모드로 돌았다 — VP 호출 형태의 두 번째 선례.
**3회차 (같은 날, idea 157 개발 방향 중력 재검토)**: 없었으면 main 은 "artifact 중력·직원 literal-rule" 두 뿌리
가설을 원인으로 확정하고 "기본값 이탈 = ②" 를 착지시켰을 것. VP 가 바꾼 것 = 설명 frame(알아보기→선택 권한→끝낼
근거→다음 비용 부담, 진단 frame 으로 한정)·두 가설 강등(교정 기록 106건 census + 감리 finding 29건 분류)·캐논 후보
4건 승격 기각·CP-1768 처분 정정. r1 19분·r2 7분, 직원 4(read-only), repo 편집 0. 3회 연속 구체 → dial 유지 확정.
부수 발견 = `buildWorkerPrompt` 가 붙이는 영문 "Coding worker constraints" 공통 블록(write·review·audit 전 모드,
`scripts/codex-mcp-server/lib.mjs:168-175`)이 co-thinker 캐스팅과 충돌(VP r2 C2; "전 모드" 정정 = ADR-875 착지
falsifier 2026-09-05) — wrapper 모드 의미론 정련 후보 (idea 157 §결론 12, CGI-1295). 원문 =
@docs/report/vp-gravity-review-2026-09-05/r2.md. 이 3회차 판독을 흡수·착지시킨 결과 ADR = @docs/adr/875-locality-principle-development-discipline-bundle.md (idea 157 흡수·착지).

### 추기 — 직원 모델 = 설정 기본, VP 사용자 명시 호출, 깊이 3단 (2026-09-06)

**사건.** 09-05 astra 사장 전환 후 하루 만에 크레딧이 터졌다. 토큰량은 그대로인데(09-05 1.90B vs 09-01 1.93B ≈ 0.96배)
1M 토큰당 크레딧이 13.4~14.3 → 29.4~32.6 (약 2.1~2.3배), 일평균 33,877 → 56,457 (1.67배; VP 재집계 dedup 후 1.54배).
자식(sub-agent) 스레드가 창의 크레딧 70.8%(VP 재집계 74.4%)를 썼고, **자식 140개 중 124개가 astra** 였다. 09-05 14:06 에
열린 7일 quota 창은 **18:06 에 100%** — 주간 허용량이 4시간에 소진됐다. 그 벽에서 사장 4개가 29초 안에 죽었고 2개는
보고를 못 냈다(18,099 크레딧 = 창의 24%). VP 는 21회/11결정/8세션, 크레딧의 9.9% 로 주범이 아니었다.

**틀린 전제 (D3).** D3 은 "사장이 직원 모델을 고른다"를 전제했으나, 실제로는 사장이 아무것도 지정하지 않으면 자식이
부모 모델을 상속했다. 상속을 못 바꾼다던 근거("full-history fork 는 model override 불가")는 **구현이 아니라 codex 가
주입하는 지시문 문구**다 — 0.153.4 live probe 에서 fork 에 model 명시가 그대로 먹었다. 같은 probe 가 `[agents]`
`default_subagent_model` / `default_subagent_reasoning_effort` 가 **fork·fresh 자식 둘 다**를 정하는 것을 확인했고
(우선순위 = 역할 TOML pin > 스폰 시 명시 > `[agents]` 기본 > 부모 상속 — 맨 앞 pin 이 명시 지정을 model·effort
두 축 모두에서 이기는 것까지 09-06 fresh 스폰 live 실측으로 확인, 구 소스 독해 추정 해소), 이 repo 의 프로젝트
`.codex/config.toml` 만 carrier 로 둔 재실측에서도 fork·fresh 자식이 모두 `gpt-5.6-sol`/`xhigh` 로 떴다.

**D3 개정.** 직원 모델·추론의 기본값은 **프로젝트 설정 `[agents]`** 이 정한다 — **`gpt-5.6-sol`/`xhigh` 확정**
(사용자 결정 2026-09-06: 비용은 3단 Luna 활용으로 분산하고, Sol 은 그 Luna 직원을 다루는 자리라 더 높은 추론
고도가 필요하다; effort 는 비용 레버가 아니라는 실측 — astra 사장 비용 중 reasoning 출력 4.9%, VP r1 — 과 정합).
예외는 스폰 시 model/effort 명시 + 한 줄 근거. wrapper(`codex-bg.sh`·`lib.mjs`)는
손대지 않는다 — codex 기본 인프라가 이미 하는 일이다 (사용자 룰링). `falsifier.toml` 의 model 무-pin 은 유지 —
이제 상속이 아니라 설정 기본을 따른다. 단 같은 파일의 `model_reasoning_effort = "xhigh"` pin 은 남아 있어, 최종값이
Luna/max 로 정해지면 **Luna 는 항상 max** 결정과 충돌한다 — 09-06 실측상 충돌 시 pin 이 이겨 `xhigh` 로 뜨므로,
그때 재검토 대상이다. astra 작은 사장 자체는 유지한다.
**깊이 3단** (사용자 룰링): astra 사장 → Sol 직원 → Luna/max 직원. Luna 자식에는 스폰 도구가 주어지지 않아 구조적
말단이고, 고용한 Sol 이 분할·검수·통합을 책임진다. **고용 기준** — Luna 에 주는 조각 = ① 대상 목록이 확정돼
있고(파일·행·테스트 이름) ② 완료를 기계로 확인할 수 있다(테스트 명령·diff 모양·건수·스키마). 예: 같은 패턴을
N 파일에 적용·테스트 실행 + 실패 분류·문서↔코드 좌표 대조·추출/표 작성·고정 인터페이스 안 구현. Sol 이 직접
하는 조각 = 원인 탐색·경계 불명·공유 계약/상태 접촉·여러 파일의 의미 보존. packet 이 한 화면(좌표·할 일·증명
방법)을 넘거나 Sol 이 가진 문맥으로 몇 분이면 끝나는 일은 직접 한다. 실패 처리 = 검사가 원인을 가리키면 같은
Luna 가 고치고, 가정이 계속 바뀌면 Sol 이 회수한다. 그리고 **Luna 에 부모 이력 통째 fork 금지**(fresh 또는
작은 `fork_turns`). 견고한 고용 경로 = 새 역할 `.codex/agents/luna-worker.toml`
(`agent_type = "luna_worker"`, model·effort pin). Sol 직원의 fork 정책은 미결이다. **위치 인지는 라벨이 아니라 신호**
(사용자 질문 2026-09-06 "너는 2단·3단 직원이다 식으로 할 건가"): packet 에 층 번호를 쓰지 않는다 — codex 가 스폰된
agent 에 "부모가 있다" 는 developer 메시지를 주고(자식 rollout 실측), 스폰 도구 부재 = 말단, `<multi_agent_mode>` 가
스폰된 agent 의 고용을 "AGENTS.md 명시 시만" 으로 묶으므로 AGENTS.md 의 한 문장("부모가 있는 직원의 고용은
`luna_worker` 뿐")이 깊이 상한의 실효 기전이다. 격리 worktree 주의: trusted project 밖에서는 roster·스폰 도구가
붙지 않는다 (probe P3/P4) — `/codex-bg` `--workdir` 주석. **한시 Luna 관찰 (사용자 결정 2026-09-06, 기간
2026-09-06 ~ 2026-09-20)**: 관찰 기간의 임무 주체는 codex 작은 사장·VP(재료 수집 직원)·그 밑 Sol 직원이다(Claude main 의 직접 고용 아님 — 사용자 정정 2026-09-06); 이들은 Luna 를 **적극 고용**(경계 조각도 먼저 줘 보고 능력 경계를 본다 — 사용자 결정 2026-09-06 "Luna 시범 운영 기간", 3단 미사용 관측 후; 같은 날 저녁 "전 부류 Luna 먼저"·"Sol 없이 astra→Luna 직접" 확장안은 사용자가 과하다고 철회 — 현행 기준으로 어디까지 쳐내는지 관찰)하고 최종 보고 고정 절
`## Luna 관찰`(잘 된 고용 = 한 줄[조각·통과], **잘 안 된 고용만 자세히** = 준 조각·어긋난 점·원인 한 단어[능력/판단 구멍/packet]·고치려면 — 사용자 경량화 2026-09-06; 09-06 중간 9행: 능력 0·판단 구멍 2·packet 3)을 가진다 — 집행 = codex prompt boilerplate
§역할 한 줄, 새 기계 없음. 종료 절차 = 기간 뒤 Fable main 이 관찰 행 전부 + `scripts/codex-mcp-server/codex_usage.py`(Luna 자식 수·크레딧 몫·
자식당 턴·중단률·`agent_type` 누락·fork 사용 + **모델별 astra/sol/luna 사용량·토큰·요율 환산 비교** — 사용자 추가 2026-09-06) 를 읽고 ① 고용 기준 5줄 ② 직원 기본값·3단 구조 ③ 규칙 마찰 부류를
판정해 research(internal) 한 편으로 남기고 필요 시 이 ADR 에 추기, boilerplate 의 관찰 줄은 제거한다. VP 는 사용자
명시 시만.

**D4 개정.** VP 는 **사용자가 그 결정에 VP 검토를 명시 요청했을 때만** 부른다. 구 "표준 호출 시점 = 착수 전·완료 전
두 지점" 문장(`delegation.md` §부사장 호출 시점)은 은퇴 — 그 문장을 읽은 8 세션이 1.3일에 21회를 불렀다. packet =
의도·금지선·현재 쟁점 + 파일 포인터(VP 가 직접 읽는다), **판단은 자기 스레드·재료 수집은 sol/luna 직원 1~2명**
(사용자 정정 2026-09-06 — 당일 초안의 "단일 스레드" 는 astra 상속 비용이 근거였는데 `[agents]` 기본값으로 그 근거가
사라졌다; 설계·구현 직원은 VP 몫이 아니다), 같은 결정 2왕복 상한 유지. 이 결정의 r2 가 그 형태로 돌았다 (VP 1회 ≈
110~135 크레딧 = astra 사장 캠페인의 0.5% — 무거워지는 경로는 재료 수집이 아니라 `vp-*` 이름의 조사 캠페인 fan-out 이었다).

**그 밖.** D1·D2·D5·D7·D8 과 dial 판독 방식은 그대로다. 폭주 상한만 실키로 정정 — `max_concurrent_threads_per_session
= 24` (구 `max_threads` 는 별칭), `max_depth`(v2 무시)·`job_max_runtime_seconds`(no-op)는 삭제.

**VP(astra) 2라운드.** r1 = fork 상속 전제를 뒤집고 census 중복 합산 −9% 를 잡았다. r2 = falsifier 의 effort pin 충돌,
설정 sync 방향(사용자 파일→template), `max_threads` 별칭, 규칙별 소유 표면 지도를 정정했다. 원문·census·probe =
@docs/report/codex-astra-burn-rebalance-2026-09-06/ (`fable-census-2026-09-06.md` · `subagent-model-probe.md` ·
`vp-astra-r1.md` · `vp-astra-r2.md`).

## 관련 문서

- 운영 상태판: @docs/ops/token-dial-ledger.md — 이 ADR 의 추기 1~5 를 계기·기대·사후 실측과 함께 시간순으로 잇는 토큰 dial 원장 (추기 (5) = 09-08 23:30 행)
- ADR: @docs/adr/875-locality-principle-development-discipline-bundle.md — idea 157 흡수·착지 (이 ADR 의 VP dial 3회차 판독이 그리로 흘렀다)
- 근거(evidence): @docs/report/delegation-lane-evidence-astra-2026-09-04.md — 문서축·장부축 census 전문
- 근거(evidence): @docs/report/codex-astra-burn-rebalance-2026-09-06/ — 09-06 소진 census·live probe·VP 2R 원문 (추기 2026-09-06)
- 근거(evidence): @docs/report/vp-idea155-direction-2026-09-05/r2.md — VP dial 2회차 (idea 155 종합, 동등 co-thinker 캐스팅)
- VP 원문 (gpt-6-astra, 2026-09-05): @docs/report/delegation-lane-evidence-astra-2026-09-04/vp-r1.md · @docs/report/delegation-lane-evidence-astra-2026-09-04/vp-r2.md · @docs/report/delegation-lane-evidence-astra-2026-09-04/vp-official-facts.md
- 규칙: @.claude/rules/delegation.md — 위임 운영 SoT (2026-09-05 착지 본문 — §작은 사장·§Opus 직원·§부사장·§두 병목·§좋은 위임 prompt)
- ADR: @docs/adr/698-journey-round-deputy-and-repro-relay.md — bounded 재량 선례 (D1)
- ADR: @docs/adr/340-coding-agent-instruction-surface-governance.md — D6 결정 부류 (사장 층으로 한 단 내림; "VP(Codex)" 는 낡음), advisor cap
- ADR: @docs/adr/583-deploy-ready-session-completion-machine.md — D3·D5 위임 장부 (필드 신설 안 함의 근거)
- ADR: @docs/adr/756-meta-machinery-retirement-discipline.md — 판독자 없는 센서 금지
- ADR: @docs/adr/866-convergence-gravity-promise-altitude-loud-failure.md — 낡음 처우 (D6)
- 스펙: @docs/goal_packets/CLAUDE.md §패킷화 판별·§실행자 눈높이 — D8 적용 범위 밖 (현행 유지)
- 스펙: @docs/architecture/state-concurrency-classes.md — D7 국소/공용 분류기(양성 판정)
- 스펙: @docs/architecture/infra/codex-bg.md — 단일 진입점·wake 계약 (불변); 역할별 모델 기본값 = `/codex-bg` SKILL §Run 양식
- 아이디어: @docs/ideas/179-luna-volume-expansion-firsthand-astra-notes.md
- 운영: @docs/ops/luna-observation-log.md

### 추기 — VP 2건째 실측: idea 161 function meta 천장 (gpt-6-astra, review, 2026-09-06) — dial 판독 재료

- 호출 조건 = Fable 판단 필요 신호 ②(갈림길: 배관 신설 vs 기존 경로 정련, B1 vs B2) + 사용자 명시 "fable + astra 상호 검토". fresh one-shot 1왕복, 40줄 좌표형 반환 (review mode 라 파일 미저작 — main 이 반환문을 `@docs/report/vp-function-meta-enrichment-2026-09-06.md` 로 옮김).
- 결과 = 8축 중 기각 1(①)·수정 6(②③④⑤⑦⑧)·유지 1(⑥) + 좌표 정정 3. main 판정 = 전량 채택 (각 점 개별 판정, 좌표 spot-check 2건).
- **"없었으면 어떤 결정을 했고 무엇이 달라졌나"**: 없었으면 직원 지도의 "공유 hop 하나가 막힘" 을 전제로 ADR-650 parity 키 배관을 1단 구현 항목으로 발주했을 것 — VP 가 기존 합성 경로(`uses` → `req` 상속 → `현재_SESSION_META_조회`)로 이미 닿음을 반증해 구현 항목이 **배관 신설 → 기존 경로의 typed 정련·발견성** 으로 바뀌었고, "기본 추천 = B2" 가 철회됐다. 결정이 바뀐 축 3(①⑤⑦). 판정 본문 = `@docs/ideas/161-function-meta-enrichment.md` §VP 검토 결과·Fable 판정.
- dial 판독 누계: 1건째(2026-09-05, r1 ①3·②6 전량 채택) + 2건째(이 건, 결정 변경 3축). 둘 다 "구체적" — D4 의 유지·확대 쪽 근거. 3건째 뒤 main 판독.

### 추기 2026-09-07 — Luna 고용 기준 정련 (VP 논의 D1·D2·D3, 사용자 채택 "그렇게 가자")

- 계기: 착지 21시간 관찰 62행의 원인 라벨 집계(능력 0 · 명시 지시 미집행 12 · packet 10 — 인과 분해가 아니다)와 VP(astra) 논의
  (`docs/report/codex-astra-burn-rebalance-2026-09-06/vp-luna-delegation-r1.md`; 중간 분석 = 같은 폴더
  `luna-interim-analysis-2026-09-07.md` + 추기). 주축 = **Luna 산출은 초안, 판정은 기존 독자(Sol/astra)** — 부모가
  모든 판정 축을 선견하는 "완벽한 packet" 에 품질을 맡기지 않는다.
- D1 (`AGENTS.md` §Worker Principles): Luna 에는 판정 기준과 검증 근거를 고정한 물량을 주고, 기준이 정하지 않은
  해석·분류는 Luna 가 결론짓지 않고 원문·분모·후보를 보존해 돌려주며 부모가 판정한다. 대체 = "판단이 전혀 없는 조각"
  증명 의무·추출/분류 명칭만의 판별.
- D2 (`.claude/rules/delegation.md` §좋은 위임 prompt + AGENTS 같은 문단): 알고 있는 미결 축과 쓰기 경로를 명시하고,
  채택 전 원문·분모·실제 효과를 기존 검수에서 확인한다. 대체 = 모든 축 선견 의무·고용 1 = 파일 1·고용마다 새 독자.
- D3 (AGENTS 고용 예시): 확정 집합의 재계산(반증 라운드의 재계산 몫 포함)을 Luna 예시로 승격(관찰 6/6); 테스트 저작은
  부모가 bind 대상·fixture 출처·실패해야 할 반례를 정한 조각만(근거 = w4_wait·corpus_cases; 2/6 은 원 분석의 참고 집계). 대체 =
  전역 mock·합성 fixture 금지.
- Luna 측 형태: `.codex/agents/luna-worker.toml` 반환 양식에 `Open Meaning:` 필드 + 한 문장 — D1 의 "보존해 돌려준다"
  를 관측 가능한 자리로 둔다. stop 규칙 복제는 하지 않는다(VP: 효과 미입증 — q3 에 기존 지시가 실제 주입됐음에도 미집행).
- 시범 운영 문단(codex-prompt-boilerplate §역할): 사장·VP 는 Luna 발주문을 파일로 남긴다 — rollout spawn 메시지
  106/106 암호화라 판독 불가(VP census `census-verification.json`). 없으면 09-20 판독에서 packet 누락 vs 인식 실패를
  못 가른다.
- 버린 안: toml stop 복제·고용 1 = 파일 1·전 고용 state 파일·매 고용 fresh 독자·전역 mock 금지·Luna 건수 최적화.
  비용 정정: "astra 1턴 = Luna 58건" 은 가격비이고, 간이 가정의 계산 예시로는 대체 조각 ≈ 3.3건이 상쇄점 — 운영 임계치가 아니다; 방향(astra 턴 증가 금지)은 유지.
- 조용한 오판 감사 결과(같은 폴더 `luna-silent-audit/report.md`, claim 단위 비-blind + blind 2): **2/10** — 승격 claim 123 중
  ① 2 (#3 child_mode: importer 회귀 "통과" claim 이 실 수집자 미실행·누적 명령 exit 1 로 불성립 · #6 operations_evidence:
  "합의된 SLO 미확인" 이 ADR-328 `10분 진단` SLO 를 놓쳐 과대), ② 2, unverifiable 20; blind 2건 Luna ① 0. 처분 = VP r1 §5
  그대로 — 2/10 은 현행 유지 + 드러난 부류·산출만 수리(중대 오류 한 건은 평균으로 상쇄하지 않는다); 이 값을 09-20 운영
  임계치로 일반화하지 않는다. 09-20 판독은 이 추기의 기준으로 D1~D3 의 효과를 본다. 문안 검수 = VP fresh 1회
  (`vp-luna-delegation-r2.md`: ① 4 · ② 3 · 삭제 3 전량 반영).

### 추기 2026-09-07 (2) — D3 dial 되돌림: 기본 사장 = Sol, astra 는 캐스팅·판정 좌석 (사용자 결정 "고고")

- 실측 (`codex_usage.py --since "2026-09-07 09:50" --by kind|campaign`, 09:50~13:49 KST 4시간): 총 15,649 cr 중 astra root
  사장 좌석 ≈9,250 (59%), astra VP 2회 ≈200 (1.3%), Sol 자식 50 스레드 5,545 (35%), Luna 자식 50 스레드 365 (2.3%). astra
  턴당 ≈630 cr — 실패 후 resume 가 200M+ 문맥을 astra 요율로 재독(같은 창 `failed` run 9건). 07:00 누계 30,850 중 astra 54%.
- 판정: astra 의 차별 가치는 **판정**(VP 3회 전부 결정 변경, 문안 검수 ① 4)이고 사장 **운전**(직원 결과 읽기·packet·resume)
  이 아니다. 사장 좌석의 값은 판독된 적이 없고(비교군 없음; Sol 사장 캠페인 `deputy-luna-silent-audit` 은 STOP·resume·
  재검 10명·보고 무결) 비용만 실측됐다 — 값이 안 읽히는 2.5배 좌석은 기본값에서 내린다(polar-star §4 "판독자 없는 센서").
- 착지: `scripts/codex-mcp-server/codex-bg.sh:27` `CODEX_MCP_DEPUTY_MODEL` 기본 `gpt-6-astra` → `gpt-5.6-sol` (VP 기본은 astra
  그대로; 진행 중 thread 는 registry 모델을 이어받아 무영향). **astra 사장 캐스팅** = 발주 시 `CODEX_MCP_MODEL=gpt-6-astra` 명시 +
  한 줄 근거(연속 판정·Fable 왕복 다수 예상) — 그때만 D3 재량 envelope 이 열린다. **Sol 사장의 판정 보강** = STOP 4종 중
  ⑵ 기결정 충돌 의심·⑶ ADR 감 판별에 astra 판정 직원 1회(`model="gpt-6-astra"` 명시 스폰, 판정만) — 결과는 판정 로그.
  Opus 자리(1단·closure·교차 반증)는 불변 — 다른 가족의 눈은 astra 로 대체되지 않는다(실측: Sol 재검자가 astra 독자 둘이 놓친
  claim 2건, Opus 교차 falsifier 가 낡은 E2E fixture).
- 기대: 같은 창 기준 절감 ≈5,500 cr (35%). 소진 속도의 주범은 동시 캠페인 수(시간당 스레드 7배)라 이 dial 은 보조다.
- 판독: 판정 로그 census(캠페인당 "Sol 이면 못 내렸을 재량 판정" 수) 로 캐스팅 기준을 조정한다; 표면 = codex-bg.sh 주석·
  boilerplate §작은 사장·delegation.md §작은 사장·CLAUDE.md §Tool And Delegation·AGENTS.md §Worker Principles·SKILL §Run 양식.

### 추기 2026-09-07 (3) — dial 판독 재료: 회복력 묶음(ADR-892) astra 사장 2 cycle 연속 round-0 STOP⑵

- 실측 (main 3d4c8527, 캠페인 = `deputy-resilience-bundle-2026-09-07` cycle 1·2, 각 26·32분): astra 사장이 두 cycle 모두 구현 0 으로
  STOP⑵ 반환. cycle 1 의 BI-01(고정 SHA green 이 더 새 red 를 CAS 해소)은 **진짜 결정 구멍** — main 룰링 R1(commit 시각 컷오프)로
  닫혔고 D3 재량 envelope 이 값을 한 자리다. cycle 2 의 사유는 **좌표 오류**(폭주 케이스의 R 표면을 catalog reject-log 로 잘못 지목;
  실제 = dispatch `FAILED`→`GIVEUP`/DLQ) — D7 "사실·좌표 오류 = 권위 소스 재유도 후 진행 + 정정 기록" 대상인데 사장이 캠페인
  **전체** STOP 을 골랐다(I-1·I-2 는 그 오류와 무관). 같은 packet 구조에 "좌표 오류는 STOP 아님·STOP 은 case 별" 두 문장을 명시한
  Sol 사장 cycle 3 는 착지했다(3h timeout 1회 → resume 1회, falsifier 3라운드 ① 0).
- 판독: astra 의 STOP 판별이 "결정 vs 사실" 경계를 packet 문면으로 읽는다 — D7 은 boilerplate 에 있지만 packet 본문에 다시 쓰지
  않으면 캠페인 STOP 으로 기운다. 처방은 모델 교체가 아니라 **packet 문장 2개**(D7 명시 + 증분별 STOP)이며, 같은 날 (2) 의 기본
  사장 Sol 전환과 정합. 부수 실측: astra thread `resume` 이 `thread/resume … list_turns is not supported (-32601)` 로 결정적 거부
  (2회) — 사장 죽음 회복은 fresh + 디스크 재구성으로 갔다(ADR-600 외부화가 무손실이었음).
- 좌표: packet `/tmp/codex-prompts/deputy-resilience-bundle-2026-09-07{,-c2}.txt` · 반환 `/var/tmp/agent-scratch/codex-results/
  deputy-resilience-bundle-{,cycle2-,cycle3-}2026-09-07/report.md` · 착지 = ADR-892.

### 추기 2026-09-07 (4) — 직원 기본 = Luna/max, Sol 직원 = 예외 · Opus 1단 = 작은 크기 (사용자 룰링, astra VP r1 반영)

- **사용자 룰링 (2026-09-07 저녁)**: "luna 를 예외처럼 두지말고 sol 직원을 예외처럼 만드는 frame" · "opus 직원은 작은 크기 구현·
  조사까지 — 중간 → 작은 정도로만 어휘 바꾸자, 중간 크기 이상은 codex 로" · "codex 는 최대한 luna 활용쪽으로" · "지침 다이어트" ·
  `[agents]` 기본값 자체를 Luna 로 — "직원의 직원 정도면 이미 영역이 좁힐대로 좁혀졌을 것".
- **실측 (계기)**: Claude 7일 가중 비용 Opus $16.4k vs Fable $4.1k, Opus 지출의 97% 가 Fable 이 띄운 직원, 그중 closure+front-closure
  5.9%(이름 휴리스틱 falsifier 포함 24%), ≥100턴 run 243개 = 직원 턴의 53% (`docs/report/claude-usage-opus-vs-fable-2026-09-07.md`,
  도구 `scripts/claude-usage/claude_usage.py`). codex 는 Sol 사장 전환 뒤(09-07 13:50~20:40) Sol 부모 → Sol 78·Luna 40·astra 11
  스레드, Luna 토큰 17%·크레딧 1.2% (`codex_usage.py --by parent-model`, VP r1 재집계). 뿌리 = `[agents]` 기본 sol/xhigh(추기
  2026-09-06) + roster 12 중 Sol pin 10 — "Luna 에 주는 조각" 이 예외 목록이라 사장이 구현·반증을 roster 역할로 고용하면 Sol 이었다.
- **결정**: **D3 개정** — 직원 기본 = **Luna/max** (`.codex/config.toml` `[agents]`; 우선순위 = 스폰 명시값 > 역할 toml pin > 기본).
  Sol 직원 = 예외 — 판정이 필요한 조각(미결 의미·경계·검증 기준을 정해야 하는 것: 원인 탐색·경계 불명 다파일 변경·집합 정당성
  반증)과 판정 역할(falsifier·closure·분석 roster); 스폰 시 `model="gpt-5.6-sol", reasoning_effort="xhigh"` **쌍** 명시 + 판정 로그
  사유(model 만 명시하면 effort 가 새 기본 max 로 뜬다 — VP r1 ①). `falsifier.toml` = Sol/xhigh 명시 pin, `implementation-mechanic.toml`
  = pin 제거(기본 Luna, Sol 은 스폰 명시) + `Open Meaning` 반환, 나머지 판정 roster pin 유지, `evidence_scout` Sol 유지(권위 분류·충돌
  처분). 정규 Luna 호출 = `agent_type="luna_worker"` + `fork_turns="none"`(생략 = all = 부모 이력 통째). 부모 의무(완료 증거 명명·
  초안 검수·테스트 저작은 bind/fixture/반례 확정 시만·미결 축·쓰기 경로)는 builtin 역할(default/worker/explorer)이 Luna 로 떠도 동일.
  깊이 = 사장 → Luna 또는 사장 → Sol(예외) → Luna. **D5 개정** — Opus 1단 = **작은 크기**: 감리(closure·front-closure)·교차 반증은
  전용 lane, 구현·조사는 발주 시 좌표가 확정된 한 국소 수정 또는 고정 목록의 단일 실행·대조로 끝나고 추가 경계 탐색·반복 수리·
  재분할이 예상되지 않을 때만; 중간 이상·애매 = codex 작은 사장. 절반 원칙 = Fable ≤ 50% 상한만 존치, "Opus 로 채운다·놀리지
  않는다" 의무 은퇴. 다이어트 = "Luna 시범 운영 적극 고용" 문단 삭제(기본이 됐다), Luna 조각 목록 → Sol 예외 원칙 하나, boilerplate
  Luna 항목 13줄 → 8줄; `## Luna 관찰` 한 줄은 09-20 판독까지 유지(추기 2026-09-06).
- **VP r1 (gpt-6-astra, review, 14분, Luna/max 재료 직원 1 — 발주 원문 VP 보고 부록)**: 방향 수용 + 수정: ① Sol 예외 model-only
  명시는 effort 를 바꾼다 → 쌍 명시 · ① builtin 역할 Luna 화는 모델만 바뀐다 → 부모 의무를 모든 Luna 스폰에 · ① 다이어트가 채택된
  검증 조건(bind·fixture·반례·미결 축·쓰기 경로)을 지웠다 → 복원 · Q2 `fork_turns` 생략 = all, `[agents]` 는 fork/fresh 구별 없음 →
  "none" 명시(문장 규칙, 기계 차단 아님) · Q3 implementation_mechanic 양 pin 제거(Luna pin 이면 Sol override 가 막힌다), evidence_scout
  Sol 유지 · Q4 "one-shot" 만으로는 100턴 run 도 통과 → 판별 문장 교체 · Q5 산술(15B×0.8=12k / ×13=195k) 수용, 예산 보장 기각 —
  Sol 비중 10/20/50% 면 30/49/104k cr, 착지 첫 캠페인부터 부모별 토큰 비중·cr/1M·총 소진 판독 · Q6 CLAUDE.md·roster README·SKILL·두
  병목 절 누락 지적 → 전부 반영 · Q7 사유 5종 → "판정이 필요한 조각" 한 원칙(공유 계약 접촉·다파일이 포괄 예외가 되는 것을 막는다).
  ② census 정정(Sol pin 10·Luna 1·무pin 1) · ② 깊이 표기(3 hop 필수처럼 쓰지 않는다). 전량 채택. VP 가 기각한 대안: TOML 변경
  0(falsifier 가 Luna 로 떨어진다) · 모든 Sol pin 유지 + 설명만(통상 구현 Sol 경로 잔존) · Luna 스레드 과반을 성공 판정으로(작은 고용만
  늘어도 큰 Sol 작업 비용 잔존) · 모든 판단 구멍의 packet 선견(기존 감사가 기각한 전제). 원문 = `/var/tmp/agent-scratch/codex-results/
  vp-luna-default-frame.json`, packet = `/tmp/codex-prompts/vp-luna-default-frame.txt`.
- **판독 (착지 뒤 첫 캠페인부터, 판독자 = 다음 codex 사장 발주 세션)**: `codex_usage.py --since <KST> --tz local --by parent-model
  --by role` 의 Sol 부모 → Luna 토큰 비중·cr/1M·총 소진 속도 + 통상 구현이 Sol 로 간 행의 판정 로그 사유; `claude_usage.py --by agent`
  의 Opus 직원 몫·≥100턴 run 수. 목표는 방향(Luna 다수·Opus 직원 몫 하락)이지 수치 게이트가 아니다.
- **잔여 위험**: Luna 의 열린 판정 자기 메꿈(claim 감사 2/10)은 부모 검수(Open Meaning·초안)가 막는다 — 2단 첫 hop 에도 같은 의무;
  Luna 장문 회수 41%; builtin 역할에는 luna_worker 계약이 자동 주입되지 않는다; live spawn 검증은 VP 도 main 도 하지 않았다(소스·
  기존 probe 근거) — 첫 codex 사장 캠페인의 `codex_usage.py` §3 flag 가 실검증. 표면: `.codex/config.toml` ·
  `.codex/agents/{falsifier,implementation-mechanic}.toml` · `.codex/agents/README.md` · `AGENTS.md` §Worker Principles·Tier line ·
  `CLAUDE.md` §Tool And Delegation · `.claude/rules/delegation.md` §판별선·§Opus 직원·§작은 사장·§두 병목 · boilerplate §역할 ·
  codex-bg SKILL §Run 양식 · 공지 `docs/user-agent-communication/notice-2026-09-07-luna-default-opus-small.md`.

### 추기 2026-09-08 (5) — 최대 활용 강도의 운영 형태: 완료 단위 = 계약 · 회수 단위 = 판정 · 관찰 문서함 (Fable 판정, idea 179·U1 착지)

- **계기**: 사용자 룰링 2026-09-08 22:20 "Luna 최대 활용 강도, 기존 지침 초과 허용"(총괄 세션이 AGENTS·boilerplate·CLAUDE·delegation 에
  bullet 로 선착지, dial 원장 23:0x 행) + idea 179 의 두 Codex main 직접 경험(A = ADR-899 결과 보존 작업, B = idea 174 한도 알림)과
  사용자 추가 아이디어 U1("Luna 기본 + 경험으로 black 영역 추가") + 같은 밤 사용자 결정 "관찰은 main 왕복 없이 고용자가 문서함에
  직접, 내가 비정기로 열어 판정시킨다". 이 추기가 그 bullet 과 (4) 의 "Sol 예외 = 판정이 필요한 조각" 을 한 문단으로 합친 **운영
  형태**다 — 결정 SoT 는 이 추기, 문안 SoT 는 `AGENTS.md` §Worker Principles.
- **판정 (Fable)**: A·B 가 서로 읽지 않고도 함께 본 것은 Luna 의 능력 부족이 아니라 세 자리다 — ① 완료·부재·인과·동일성에 대한 **문장**을
  부모가 그대로 채택한 순간(A: false-green live test·wrapper 우회 "공식 실행"·"무관" 귀속) ② **명시 요구의 미소진을 완료로 보고**(B;
  09-07 관찰 62행의 최다 라벨 "명시 지시 미집행 12" 와 같은 부류 — Open Meaning 만으로 안 잡힌다) ③ main 쪽 조율 낭비(끝난 직원에
  `send_message`·긴 결과 재독·검수 지연). 셋 다 처방은 고용 축소가 아니라 **채택 전 확인을 싸게 만드는 반환 모양 + 회수 범위의 축소**다.
- **D-a 완료 단위 = 계약 하나**: 같은 계약·같은 완료 기준 안의 구현·테스트·형제·회귀·문서·조사·보고 초안을 한 Luna 의 소유 범위로.
  값이 파일을 건너면 전달 끝까지 한 묶음, 연결 확인 소유자는 부모 지정. 새 계약의 첫 조각은 효과 확인 뒤 형제로 확대(A 안 1·B "전달
  끝까지 책임지는 묶음"). 판정 섞인 조각도 Luna 초안 먼저(사용자 룰링) — (4) 의 예시 3종(원인 탐색·경계 불명 다파일·집합 정당성 반증)은
  "Sol 직접" 에서 "Luna 초안 + 부모/Sol 판정" 으로 이동.
- **D-b 회수 단위 = 판정, 물량은 되돌린다**: Sol/부모가 의미를 정하면 형제 적용·회귀·확정 수리는 같은 Luna 로 돌아간다(A 안 2·B "확정
  수리도 Luna"). Sol 이 조각을 쥐는 것은 가정·판정 기준이 라운드마다 바뀌는 동안뿐. **Sol 예외 문장 = black 목록(U1)**: 관측된 판정
  조건(조건→실패 형태)으로만 늘고, 구체 피드백 뒤 Luna 가 처리한 조건은 뺀다; 업무 종류(테스트·문서·다파일·JSONL)로 적지 않는다(A·B
  공통 — "wrapper 누락을 이유로 테스트 전체를 black 으로 보내면 고칠 수 있던 물량까지 잃는다").
- **D-c 반환 모양**: `luna-worker.toml`·`implementation-mechanic.toml` 에 `Requirements:`(명시 요구 항목별 착지 좌표 또는 `not done: 사유`;
  미소진 = Blocker, Risk·잔여 금지) + `Completion Evidence` = 원문 명령(공식 wrapper 포함)·exit·효과 좌표("통과" 문장 금지). 09-07 추기가
  기각한 "toml stop 규칙 복제" 와 다르다 — 행동 지시가 아니라 `Open Meaning` 과 같은 **관측 가능한 자리**다. 부모 의무에 "요구 목록 소진
  확인" 과 "Sol·falsifier 의 정정도 같은 대조"(A: Sol 이 Luna 보고를 오독) 추가; 테스트 저작 조건에 "정상 경로와 분리한 예상 실패"(A)
  명시; packet 에 읽을 입력 범위(B — 시간 예산은 여전히 금지, delegation.md §좋은 위임 prompt).
- **D-d 관찰 문서함 = `docs/ops/luna-observation-log.md`** (사용자 결정 2026-09-08): 잘 안 된 고용만 고용자(사장·Sol 직원)가 표 한 행
  단일 append(조각·조건→실패·원인 한 단어·처분). 사장 보고 `## Luna 관찰` 절은 은퇴(추기 2026-09-06·(4) 의 "09-20 판독까지 유지" 를
  대체). 판독자 = 사용자(비정기) → 그 세션이 Sol 예외 문장 개정안을 낸다. 09-20 판독(project memory)은 정량 축(`codex_usage.py --by
  parent-model`·Sol 사유 census·`claude_usage.py --by agent`)만 남고 정성 축은 이 문서함으로 이동. 등기 = 단일 행 append 전용(여러 세션
  동시 쓰기; 등기부 행 신설은 착지 캠페인 몫).
- **D-e 조율**: 끝난 직원은 `send_message` 로 재개되지 않는다 — `followup_task`(A 실측; `~/.codex/sessions` rollout 에 5,462 호출로 도구 실재
  확인). 호출 수 규율은 boilerplate(dial 원장 09-08 12:00 행) 그대로.
- **짓지 않음**: black registry·라우터(A·B 모두 기각 — Sol 예외 문장이 목록) · 영수증 시스템/JSON schema(B 기각 — 반환 필드 하나) · Luna
  고용 건수 최적화·매 고용 새 독자·고용 1 = 파일 1(09-07 기각 유지) · Luna 독립 검토로 falsifier/closure 대체(B 사고) · packet 별 "Luna
  최대 활용" 조항 의무(boilerplate 가 싣는다 — 있어도 무해).
- **잔여 위험**: 큰 완료 단위는 조용한 오판의 반경도 키운다 — 완화는 단위 축소가 아니라 첫 조각 효과 확인 + `Requirements:`/증거 원문
  대조. 사용자가 문서함을 오래 안 열면 black 목록이 낡는다(의도된 비정기; 센서의 종착 판독자 = 사용자). 비용·절감률은 재지 않았다(A·B
  모두 미측정) — 판독 = dial 원장 §3.
- **표면**: `AGENTS.md` §Worker Principles(통합 문단) · `.codex/agents/{luna-worker,implementation-mechanic}.toml` · boilerplate §역할 ·
  `CLAUDE.md` §Tool And Delegation · `.claude/rules/delegation.md` §좋은 위임 prompt · `docs/ops/luna-observation-log.md`(신설) · dial 원장
  09-08 23:30 행 · 공지 `docs/user-agent-communication/notice-2026-09-08-luna-unit-and-wake.md` · idea 179 승격 배너. 짝 결정(같은 밤) =
  ADR-619 추기 2026-09-08(`--no-wait`, idea 171).

### 추기 2026-09-09 (6) — 판별선 재조정: 1단 직원 = Opus 기본(압력 = Opus), codex 는 작은 사장·VP 좌석 (사용자 룰링)

- **계기**: idea 179 후속 판독 세션에서 사용자 질문 — "idea 179 가 기존 Opus 좌석역할(1단 조사·감리)까지 소화하고 있나? 난 별론데".
  확인 결과 (5) 는 codex 풀 안의 Luna/Sol 배분만 바꿨고 Opus 좌석은 무변경이나, (4) 의 09-07 판별선 하향("중간 이상·애매 = codex")이
  조사를 **크기 기준**으로 codex 로 보내고 있었다 — 이 세션의 첫 발주(`codex_usage.py` 축 확장 + Sol 사유 census·정독 조각을 codex
  사장에 묶음, `bg_1788906733159219652_320146_18456`)가 그 예라 취소했다. 사용자 룰링(원문): "조사의 질이 설계 판정의 질과 연결될수
  있을거같아서 … 1단 직원은 opus 쓰는걸로 압력을 좀 줄까싶은데 작은 사장, VP는 codex 자리. 중규모 이상 조사로 작은 사장 자리가
  좋을정도면 codex 보내는거 정도는 괜찮을거같고".
- **결정 (D5 재개정)**: **1단 직원 = Opus 기본, 압력 = Opus** — 조사·census·정독·교차 검토·감리(closure·front-closure)·교차 family
  반증·좌표 확정된 작은 구현은 1단 Opus one-shot. **codex 는 좌석 둘 — 작은 사장(2단)·VP** 이지 1단 직원이 아니다. 조사·구현이
  **작은 사장 자리를 둘 만큼** 중규모 이상(다라운드 — 2단 전형 3종: 합성·재발주 직원 5+ · 공용 상태 쓰기 · 무인 수시간)일 때만
  codex 로; 애매하면 1단 Opus 로 시작하고 2단 필요가 드러나면 올린다(09-07 "애매 = codex" 철회). Luna/Sol 배분((4)·(5))은 무변경 —
  codex 사장 밑 직원 기본은 여전히 Luna/max.
- **맞바꾼 것**: (4) 의 비용 근거(7일 Opus 지출 97% 가 직원, 2/3 가 구현 물량) — Opus 직원 몫 상승을 감수한다. 판독 = dial 원장 §3
  주 1회 `claude_usage.py --since <착지> --by family --by agent` (Opus:Fable 비 · general-purpose 직원 몫 · ≥100턴 run 수). 기준선
  (09-07 00:00 → 09-09 07:32 KST) = Opus $4,404 / Fable $1,420 가중(3.1:1), 직원 general-purpose 48% + unspecified 44%, closure 5.2%.
- **표면**: `.claude/rules/delegation.md` §판별선·§Opus 직원·§두 병목 · `CLAUDE.md` §Tool And Delegation(판별선·Opus 자리 셋) ·
  `AGENTS.md` §Worker Principles dividing line · 공지 `docs/user-agent-communication/notice-2026-09-09-tier1-opus-pressure.md` · dial 원장
  09-09 행 · 구 문면 전파 census = `docs/report/luna-post-idea179-readout-2026-09-09/lane-reset-propagation.md`(Opus 직원) · 메모리
  `feedback_opus_investigation_audit_only_codex_impl_luna_max`.
- **짓지 않음**: 크기 임계 숫자·라우터(2단 전형 3종은 판단 신호 유지, Fable 재량 그대로).

### 추기 2026-09-09 (7) — (5) 첫 판독: Sol 예외 문장 무변경, 기록 경로 이음새 둘 수리 (Fable 판정, 사용자 발주 idea 179 후속)

- **판독 재료**: 문서함 15행 + `codex_usage.py --since "2026-09-08 23:31" --tz local --by parent-model --by role` + Opus 직원 census
  `docs/report/luna-post-idea179-readout-2026-09-09/friction-census.md` (cohort = root 시작 기준 before/gray/after; 착지 = 23:04 boilerplate ·
  23:31 toml). 사용자 caveat 반영 — 착지 때 살아 있던 codex 세션은 옛 방식, 그 뒤 새로 뜬 세션만 새 방식.
- **판정**: 착지 후 8.3h 창 Luna 스레드 180 전부 luna/max, 비-판정 Sol 스폰 0(Sol 자식 = falsifier pin 20, astra 판정 자식 1); 문서함
  원인 `능력` 0, 착지 후 Sol 회수 0(부모 직접 5·같은 Luna 수리 4) → **Sol 예외 문장 변경 없음** (D-b 의 "관측된 판정 조건" 으로 늘릴
  조건이 아직 없다). 표본 얇음 — fresh root 2~3, 나머지는 착지 전 root 의 resume.
- **이음새 ① D-d append 가 packet 문면에 막혔다**: main 저작 packet 2건이 문서함을 "공용 상태 기본 불허·peer dirty file — not yours"
  로 금지(`deputy-p8b-t6-packet.md:37-40`, seat-mode-r11-x7 후속 packet) → 착지 후 root 12 중 append 3, 보고서에 마찰이 있는데 행 없는
  root 6/11. 수리 = **상시 허가** 명문화: `.claude/rules/delegation.md` §좋은 위임 prompt 권한 bullet + boilerplate §공통 원칙 (append-only
  장부의 한 행은 dirty 여도 허가). `## Luna 관찰` 절 은퇴는 9/10 보고서에서 안 먹혔다 — **버림**(ADR-875 D5: 왕복이 아니라 중복 절이라
  손실 0; append 가 살아나면 자연 소멸 예상, 다음 판독에서 재확인).
- **이음새 ② D-c `Requirements:` 가 packet 의 "N줄만 반환" 지시에 덮였다**: 새 toml 자식 65/160 에만 실림(캠페인 편차 22/27 ↔ 0/19). 뿌리 =
  호출 수 규율 ③(3줄 반환)과 toml 반환 모양의 충돌. 수리 = 모양의 거주지 = **산출 파일**, 메시지 = 3줄 포인터 — `luna-worker.toml`·
  `implementation-mechanic.toml` 반환 절 + boilerplate ③. 덤 = codex 쪽에 없던 **시간 예산 금지문** twin(boilerplate; 실측 p8b packet
  "hard limit 5 minutes").
- **표면**: 위 5개 + 문서함 `## 판독` 1행 + dial 원장 09-08 23:30 행 사후 실측 셀 + interventions 행 + idea 179 §재개 조건 1행. 판독 도구
  확장(`codex_usage.py` cohort·return-shape 축)은 **짓지 않음** — 사용자 재조준(정성 마찰 판독)으로 취소·원복, 필요해지면 그때.
- **정정 (사용자, 같은 날 오후) — black 목록은 비어 있지 않다, 한 목록이다**: 배정 판단은 "Luna 가 안 되는 자리 빼고 전부 Luna" 한
  목록으로 하며, 그 목록의 첫 항이 판정 역할 pin(closure·falsifier·분석 roster)이다 — 판독 보고의 "black 0건" 은 역할 pin 과 관측
  조건을 두 목록처럼 가른 오독. 같은 뿌리로 **Sol 스폰의 "왜 Luna 로 안 되는가" 산문은 은퇴** — 목록이 하나면 사유 = 목록 항
  한 단어(a/b/c)이고, (b) 초안 미달은 정의상 문서함 `Sol 회수` 행이라 두 자리에 같은 사실을 적는 두-우주였다. 판독 루틴도
  "판정 로그 사유 census" → "비-pin Sol 자식 vs 문서함 `Sol 회수` 행 대조"(행 없는 Sol 자식 = 설명 없는 Sol). 표면 =
  AGENTS.md §Worker Principles 목록 문단 · boilerplate §역할 · CLAUDE.md §Tool And Delegation · delegation.md §Fable-급 사장 ·
  dial 원장 §3.

### 추기 2026-09-09 (8) — codex roster 압축 12 → 6: "Luna 가 안 되는 자리" (a) = 감리(falsifier·closure) 둘만 Sol pin (사용자 룰링)

- **계기 (사용자, 같은 날 오후)**: "evidence_scout 를 좁히면 luna 자리가 없다" · "4번(prompt_input)·5번(response)은 묶어라, 5번이 왜 luna
  가 안 되나" · "7번(workflow_rationalist)도 4·5 와 묶으면 된다" · "10개로 흩어뜨리지 말고 설계 동업도 압축" · "감리(falsifier,
  closure) 라고만 쓰면 된다". 정정 (7) 이 만든 한 목록의 (a) 항이 역할 10개를 pin 째 나열하는 것이 문제였다 — 배정은 "안 되는 자리
  빼고 전부 Luna" 인데, 그 자리에 증거 수집 역할 6개가 Sol pin 으로 끼어 있었다.
- **결정 (D3 roster 개정)**: roster = `luna_worker` · `implementation_mechanic` · `evidence_scout`(**Sol pin 제거 → Luna 기본**; 권위
  분류·충돌 처분은 scout 의 일이 아니라 부모 판정 — `Open Meaning` 으로 올린다) · **`air_analyst`(신설·병합 = prompt_input_analyst +
  agent_response_analyst + agent_flow_observer + workflow_rationalist; Luna 기본; 반환 = 표면별 절 — 주입 prompt / 응답 / 흐름 / 저작
  지시문, packet 이 볼 표면 지정)** · `falsifier`(Sol pin; open_cognition_partner 의 "구현 전 설계 가정 공격" 흡수 — 이미 falsifier 정의
  의 앞반부) · `closure`(Sol pin; codex-main 자기감리만). **은퇴** = learning_distiller(그 일 = 문서함·dial 원장 + 판독 세션) ·
  vp_router("안 되는 자리 빼고 다 Luna" 한 목록이면 라우팅 판단 자체가 없다) · open_cognition_partner(falsifier 흡수). 설계 동업은
  roster 에서 0 — VP 는 이미 wrapper `vp-*` fresh one-shot. 응답 품질 판정이 Luna 로 못 가는 이유는 없다 — 그 판정은 원래 main 몫
  (LLM 출력 품질 = main 이 sample 직독)이고 analyst 는 좌표 추출이다.
- **경계 보존**: 은퇴·병합된 7개 toml 은 **alias 로 존치**(헤더 retired 표기 + Sol pin 제거 → 스폰되면 Luna 로 옛 본문 실행) — in-flight
  캠페인·goal packet 이 옛 `agent_type` 으로 스폰해도 깨지지 않는다. 파일 삭제 = 소비자 sweep 0 + in-flight run 0 확인 뒤 별도 증분.
- **잃는 것**: 살아있는 분석 3종의 개별 dispatch(→ 한 역할에 표면 지정; 표면마다 독립 눈이 필요하면 같은 역할 3 스폰) · open_cognition
  의 "동업" 프레이밍(공격은 falsifier 에 남음) · distiller 의 규칙 증류(판독 세션 몫으로 이미 이동) · vp_router 의 no-call 기본(목록
  규칙이 대체).
- **표면**: `.codex/agents/air-analyst.toml`(신설, Fable 저작) · 7개 toml 헤더·pin · `evidence-scout.toml`(pin 제거 + Open Meaning 문장) ·
  `.codex/agents/README.md` §Invocation Policy · `AGENTS.md` §Worker Principles (a) 문장 · boilerplate §역할 · `docs/agent-infra-registry.md`
  roster 등기 · delegation.md §codex roster 항 · 역할명 포인터 문서(observability·error-chain·docs-graph·boss-mode) · 공지
  `notice-2026-09-09-codex-roster-compression.md` · dial 원장 09-09 행 · 테스트(`full-capability-default.test.mjs`·
  `test_agent_scratch_contract.py`·`test_codex_usage.py`).
- **정정 (사용자, 같은 날 저녁) — 위 결정문 재작성, 아래가 현행**: 사용자 원문 "지침·학습 이거 black 유지해야 되잖아. 설계 동업도
  마찬가지고, live 분석도 마찬가지" · "내가 이 문서에 의도 정렬 안 했나? luna 를 최대한으로 활용하기 위해서 black 빼고 다 luna 해서
  black 만 관리하자고" · "luna 자리를 만들지 말라고, luna 를 쓰면 안 될 자리 개념만 두라고. 그럼 알아서 빼고 다 luna 보낼 거잖아".
  Fable 오독 = "감리(falsifier, closure) 라고만 쓰면 되지 않나" 를 **문안 압축**(범주 용어로 적기)이 아니라 **black 축소**로 읽어 live
  분석·학습·설계 동업을 Luna 로 내리거나 은퇴시켰다. **현행 roster = black 5 + `luna_worker` 1**: black(Sol/xhigh pin, Luna 를 쓰면 안 될
  자리) = 감리 `falsifier`·`closure` · live 분석 **`air_analyst`**(prompt_input_analyst+agent_response_analyst+agent_flow_observer+
  workflow_rationalist 병합 — 겹치는 역할 묶기만, black 유지) · 학습 `learning_distiller`(복원) · 설계 동업 **`open_cognition_partner`**
  (복원, `vp_router` 의 라우팅 질문 흡수 — Codex-led lane 전용, Claude main 기용 안 함). **Luna 자리는 따로 두지 않는다** — 목록 밖은
  전부 `luna_worker` 이며, `evidence_scout`·`implementation_mechanic` 도 별도 Luna 역할이 아니라 `luna_worker` packet 이다(alias
  존치 → luna_worker). alias 7 = 위 4 analyst/rationalist → air_analyst · vp_router → open_cognition_partner · evidence_scout ·
  implementation_mechanic → luna_worker. 앞 결정문의 "12→6, Sol pin 둘, evidence_scout Luna 기본, distiller·partner 은퇴" 는 이
  정정으로 대체된다(파일 수는 같은 13: live 6 + alias 7).

### 추기 2026-09-10 (9) — (5)·(8) 둘째 판독: 문서함 단위 정의 + packet 저작 2문장, black 무변경 (Fable 판정, 사용자 발주 "luna 사용 이력 남은 거 꼼꼼히 살피고 조정할 거 있나")

- **창**: 09-09 07:50 → 09-10 15:20 KST (31.5h). 재료 = Opus 1단 직원 둘의 census(조사 = Opus, 추기 (6)) —
  `docs/report/luna-post-idea179-readout-2026-09-09/return-shape-census-2026-09-10.md`(Luna 자식 312) ·
  `deputy-log-compliance-2026-09-10.md`(사장 root 8). 판정 = main.
- **실측**: Luna 자식 312 전부 luna/max, `luna_worker` 자리를 Sol 로 override 0, leaf 위반 0. (7) 의 toml 반환 수리는 효과 있음 —
  3줄 포인터 271/312, `Requirements:` 산출 파일 275/312(수리 전 65/160). Sol 자식 44 = falsifier 42 · air_analyst 1 · `default`+Sol/xhigh
  명시 1; 비-pin 2 는 approval-truth 한 사장(09-09 08:18 시작 장수 스레드) — r23 constructor recovery = **(b) 한 단어 명시·스폰 모양
  정확**(`agent_type="default"` + 쌍 명시 + `fork_turns="none"`) / turn22 = `air_analyst` 를 Luna 의 STOP 후보 판정석으로 쓴 산문(산출물
  자신이 live 3표면 "Not requested" — 그 자리는 사장 자신 또는 astra 판정 직원, delegation.md). 문서함 신규 1행(gag4) vs 사장 보고·
  state 로 재유도한 있어야 할 행 **조각 28 / 고용 21** — 원인 미집행 11·판단 구멍 14·packet 2·조율 1·**`능력` 0**(두 창 연속), 처분
  같은 Luna 수리 16·부모 직접 8·Sol 회수 2·부모 STOP 2. → **Sol 예외 문장·black 5 무변경, (c) 추가 없음.**
- **미기입 뿌리 셋 (판정)**: ① "잘 안 된 고용" 의 **단위**가 어디에도 정의돼 있지 않았다 — approval-truth 는 8 turn 연속 "고쳐 채택 =
  성공 고용"·"별도 문서함 예외 조건을 신설하지 않았다" 로 읽었고, 5 root(converge·r2fix·s4docs·samecall·bp192-s4)는 boilerplate 로
  의무를 매 턴 받고도 고려 자체가 0(samecall 은 packet 이 append 권한을 명시했는데도). ② 은퇴한 `### Luna 관찰` 절이 **main 저작
  packet 13개**(approval-truth r17~r29)의 보고 양식 열거로 살아남아 문서함 자리를 차지했고, adr887 packet 은 "do not extend" 만 반복 —
  packet 이 문서함을 언급한 것은 0. ③ **AGENTS.md 가 09-09 18:10 전까지 codex 기본 `project_doc_max_bytes` 32 KiB 에서 잘려
  주입**됐다(§Worker Principles 한가운데 절단 — 문서함 bullet·black 목록은 절단선 뒤; 사장 rollout 의 주입 블록 34.5KB 실측) — ADR-900
  D7 이 같은 날 `.codex/config.toml` `180224` 로 닫았다(commit `336f0840f`). (7) 첫 판독이 잰 root 도 전부 잘린 판이었다 — 그 창의
  "append 3/12" 는 이 사실과 같이 읽는다.
- **역방향 이탈 (고용자 쪽)**: main packet 이 bp192-s4 5·s4docs 2 감리 라운드를 `luna_worker` 로 캐스팅했고("workers = luna_worker …
  falsifier rounds" · "one fresh Luna review round") 그 결과가 `falsifier_thread`·fresh-0 근거에 실렸다 — black (a) 를 packet 이 덮은
  모양. 그 두 캠페인의 마감 판정은 Sol falsifier 근거가 아니다(재감리 여부 = 그 캠페인 owner·사용자 몫, 여기서 재실행하지 않음).
- **결정 (Fable — 기존 결정 (5)·(8) 의 정의·경계 명문화, 극성 변경 아님)**: (가) 문서함 헤더에 단위 정의 — "Luna 조각이 완료 기준을
  한 번에 못 넘긴 것(falsifier ① 초안·부모 재작업·미집행/오분류 회수·Sol 회수); 같은 Luna 가 고쳐 채택돼도 한 행; 성공 = 첫 반환이
  그대로 채택" — AGENTS.md §Worker Principles·boilerplate §역할 같은 구절. (나) delegation.md §Luna 조각 packet 에 packet 저작 2줄:
  보고 양식에 `Luna 관찰` 절을 열거하지 않는다(문서함 행이 그 자리) · 감리 라운드를 Luna 에 캐스팅하지 않는다(`agent_type="falsifier"`;
  packet 의 최대 활용 문장은 black 을 덮지 않는다) — AGENTS.md·boilerplate 에 "black 이 packet 을 이긴다" 한 구절. (다) **짓지 않음** =
  Luna 반환 신호(Open Meaning 비어있지 않음 147/312, 강한 신호 37)로 문서함 행을 자동 생성하는 기계 — 유일한 실재 행(gag4)의 Luna 반환은
  여섯 신호가 전부 꺼져 있어 반환-신호 축과 고용자 판정 축이 겹치지 않는다는 실측; 행은 고용자의 판정이다. (라) air_analyst 판정석
  오용은 1건이라 표면 무변경 — 두 번째면 toml 에 "live 표면 0 = 이 역할 아님" 한 줄. (마) 측정 주의: `codex_usage.py --by role` 의
  role `none` luna(66)는 시뮬 persona `codex exec` root·사용자 CLI 라 고용 분모 아님(분모 = `luna.summary.children`).
- **기대·판독**: 다음 창 문서함 행/고용 ≥ 과반, Luna 감리 라운드 0(재유도 = `deputy-*/report.json` `falsifier_thread` 스폰 agent_type).
  표면 = 문서함 헤더·`## 판독` · AGENTS.md §Worker Principles · boilerplate §역할 · delegation.md §Luna 조각 packet · dial 원장 09-09 오후
  행 사후 셀 + 09-10 행 · 공지 `docs/user-agent-communication/notice-2026-09-10-luna-log-unit-and-packet-casting.md` · idea 179 §재개 조건.

### 추기 2026-09-10 (10) — 관찰 문서함 은퇴 **예약**: 다음 release 뒤 아키텍처 정상 구동 관찰 → 흔적 없는 삭제 (사용자 결정)

- **계기**: (9) 판독 뒤 사용자 질문 "luna 관찰 결과 계속 보고하고 남기게 하는 거 아직 유의미할까?" — Fable 판정 = 아니오에 가깝다: 두 창 미달 43조각에서 `능력` 0, black 두 번 무변경, 기록률 1/21(경로를 두 번 고친 뒤에도), 판독 재료는 사장 보고·falsifier 파일에서 20분에 재유도됨 — 울려도 아무도 안 움직이는 센서(polar-star §4). black 에 실제로 닿는 사건(Luna 조각이 Sol 로 넘어감)은 판정 로그 a/b/c 한 단어 + `codex_usage.py --by role` 비-pin Sol 로 이미 잡힌다.
- **결정 (사용자 원문)**: "다음 release 후에 아키텍처 정상적으로 구동되는거까지만 관찰한다음에 은퇴하자. 은퇴 의사결정 미리 올려놓자. 은퇴 방식은 지침에 지저분하게 luna를 관찰했었는데 이제는 안해도되요 이런식으로 하지말고 처음부터 그런게 존재하지 않았던거처럼 깔끔하게 해줘. 지침은 가볍게. 어차피 이런 이력은 문서에 남아있을거니까."
- **시점·주체**: 다음 release 가 나가고 Luna 물량으로 지은 아키텍처가 운영에서 정상 구동됨을 사용자가 관찰한 뒤 — 판정 = 사용자, 실행 = 그때 사용자가 지시하는 세션(총괄 또는 Fable main). 그 전까지는 (5)·(9) 현행(문서함 의무·단위 정의) 그대로다. 09-06 의 "관찰 창 ~09-20" 은 이 시점으로 대체된다.
- **은퇴 방식 원칙**: 지침 표면에서 관찰 장치를 **삭제**한다 — "관찰했었는데 이제 안 한다" 류 대체 문장·은퇴 표기·포인터를 남기지 않는다. 이력의 집은 이 ADR (5)·(7)·(9)·(10) · dial 원장 · `docs/report/luna-post-idea179-readout-2026-09-09/` · dated 공지 · idea 179 이고, 그 문서들은 손대지 않는다.
- **남기는 것 (관찰 장치가 아니라 위임 규칙)**: "기본은 Luna 다 … black 빼고 다 Luna" · black (a) 판정 역할 5 · (b) Luna 초안 미달 재작업 · Sol 스폰 = 쌍 명시 + 판정 로그 a/b/c 한 단어 · "black 이 packet 을 이긴다"(감리 라운드 Luna 캐스팅 금지) · 완료 단위 = 계약 · 회수 단위 = 판정 · `Requirements:`/`Open Meaning` 반환 · append-only 장부 한 행 상시 허가 규칙 자체(예시는 red-ledger 로).
- **지우는 것 (실행 세션의 목록 — 실행 시 `rg` 로 재유도해 이 목록보다 우선)**:
  - `AGENTS.md` §Worker Principles: black 문장의 **(c)** 항 + "목록은 (c) 로만 늘고 … 뺀다" 문장(→ black = (a)+(b)) · "(사유의 집은 이 목록과 문서함 `Sol 회수` 행)" → "(사유의 집은 이 목록)" · **관찰 문서함** 문단 전체.
  - `.claude/skills/codex-bg/codex-prompt-boilerplate.md` §역할: black 괄호의 "+ 문서함이 실증한 조건" · **관찰 문서함** 문장 전체; §공통 원칙 append-only 예시에서 문서함 경로 제거(red-ledger 예시만).
  - `.claude/rules/delegation.md`: §작은 사장 "잘 안 된 고용은 고용자가 … 직접 append 한다" 문장 · §좋은 위임 prompt 권한 bullet 의 문서함 예시 · §Luna 조각 packet 의 "잘 안 된 고용(…)은 고용자가 … 적는다" 문장과 packet 저작 ①(`Luna 관찰` 절) — ②(감리 Luna 캐스팅 금지)는 남긴다.
  - `.codex/agents/README.md` "Observation inbox" 줄 · `docs/ops/token-dial-ledger.md` §3 판독 루틴의 문서함 대조 구절(→ 판정 로그 a/b/c 한 단어와 대조).
  - `docs/ops/luna-observation-log.md` → `docs_archive/ops/luna-observation-log.md` (헤더에 "은퇴 = ADR-872 추기 (10)" 한 줄은 아카이브 문서라 허용) · 등기부 `docs/architecture/state-concurrency-classes.md` 행 142 = 등기부 은퇴 관용구대로 처리 + manifest 엔트리 `scripts/branch-surface/report_state_contract_bindings.py` (`title="Luna 관찰 문서함 …"`) 동반 → `python scripts/branch-surface/report_state_contract_bindings.py --lint` · `tests/test_state_contract_manifest_parity.py` green.
  - memory: `project_luna_observation_window_2026_09_20.md` 삭제 + `MEMORY.md` Luna 운영 줄의 문서함 구절 제거(두 디렉토리).
- **검증 (실행 시)**: `rg -n 'luna-observation-log|관찰 문서함|Luna 관찰|잘 안 된 고용' AGENTS.md CLAUDE.md .claude .codex scripts docs/architecture docs/ops --glob '!docs/ops/token-dial-ledger.md'` = 0 hit(원장·ADR·report·공지·idea 는 이력이라 우주 밖) · `python scripts/docs-graph/check.py --paths <변경 문서>` NG=0 · `python scripts/instruction-surface/injection_budget.py` · interventions.jsonl 1행 · 공지 1통(무엇이 사라졌나 3줄, 이유 = 이 추기 포인터).
