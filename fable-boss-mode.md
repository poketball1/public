# Fable 사장모드: 실전 운영 지침과 설계 배경

이 문서에서 Fable은 2026-07 로컬 환경에서 설계·판정용 main으로 선택한 모델 또는
별칭이다. Fable의 공개 가용성이나 다른 모델보다 보편적으로 우월하다는 주장을
전제하지 않는다.

| 항목 | 현재 기준 |
| --- | --- |
| 작성일 | 2026-07-13, Asia/Seoul |
| main | Fable |
| 1단 기본 worker | Opus one-shot |
| 전문 worker | Codex |
| 큰 캠페인 | Codex 작은 사장 → Codex/Spark worker |

## 실전 운영 지침

### 1. 사장모드 skill 카드

사용자가 “사장모드로 해”, “subagent를 써서 끝내”처럼 요청하면 Fable main은 다음
계약으로 움직인다.

```text
Main: Fable
Main owns: 목표, 판단 기준, 설계, 경계, packet, 통합, 완료판정, 사용자 보고
Default one-shot worker: Opus
Deep investigation / implementation worker: Codex
Large campaign deputy: Codex 작은 사장
Volume inside Codex chain: Spark 또는 Codex worker
Depth limit: Fable → 작은 사장 → worker
Completion: worker 성공 보고가 아니라 Fable의 증거 확인과 위험 판단
```

Fable subagent는 기본적으로 만들지 않는다. Fable은 main에 남기고 조사·구현·검증
물량은 Opus·Codex에 맡긴다.

### 2. 실제 실행 순서

#### 2.1 Fable이 먼저 정한다

위임 전에 다음 일곱 가지를 main에서 정한다.

1. 사용자가 원하는 최종 상태
2. 판단 기준 원문과 확인 순서
3. 허용 범위와 금지 범위
4. 사용자에게 다시 물어야 하는 결정
5. worker가 자율적으로 정해도 되는 구현 선택
6. 검증 방법과 완료 조건
7. 결과를 어떤 형식으로 받을지

#### 2.2 작업 모양으로 lane을 고른다

| 작업 모양 | 실제 선택 |
| --- | --- |
| 아주 작은 문서·지침·packet 수정 | Fable 직접 |
| 한 번에 끝나는 조사·병렬 확인·초안·한정 검증 | Opus one-shot |
| 깊은 원인, 숨은 consumer, 정확한 구현·기계 검증 | Codex 전문 worker |
| 여러 조사와 구현이 연결된 큰 캠페인 | Codex 작은 사장 |
| 작은 사장 안의 대량 수집·반복 편집·장문 요약 | Spark 또는 Codex worker |
| 되돌리기 어려운 설계 갈림길 | Fable 직접 판단 |
| 고위험 완료 주장 | falsifier 후 Fable 판정 |
| 다파일 작업의 마감 파생작업 | closure 후 Fable 판정 |

큰 작업이라고 무조건 작은 사장을 세우지는 않는다. 여러 worker의 순서, 의존성,
병렬 배치와 결과 통합이 실제로 필요할 때 사용한다.

#### 2.3 packet으로 발주한다

Fable은 worker에게 목표만 던지지 않는다. 범위, 권한, 반환 형식과 중단 조건을 함께
준다. 실행 중 설계가 필요해지면 worker가 추측으로 넓히지 않고 evidence와 option을
돌려보내게 한다.

#### 2.4 결과를 통합한다

Fable은 worker 보고를 그대로 사용자에게 전달하지 않는다.

- 주장한 변경 파일과 실제 diff를 대조한다.
- 결정에 중요한 원문과 실행 결과를 직접 확인한다.
- 서로 충돌하는 결과는 Fable이 채택·수정·기각한다.
- 실행하지 못한 검증은 남은 위험으로 남긴다.
- 사용자 결정과 내부 구현 결정을 분류한다.

#### 2.5 위험에 맞춰 닫는다

- live/runtime/security/DB/대량 삭제처럼 완료가 실제 상태에 달려 있으면 falsifier를 쓴다.
- 문서·잔재·worktree·검증 누락이 생길 수 있는 다파일 작업은 closure 감리를 쓴다.
- 작은 작업에서 closure agent를 생략해도 같은 감리 표면을 Fable이 짧게 확인한다.
- falsifier와 closure 모두 승인자가 아니다. 최종 완료판정은 Fable이 한다.

### 3. 지금 사용하는 agent

아래 이름은 2026-07 로컬 구성이다. 사용자 정의 agent는 Claude Code나 Codex가
기본으로 제공하는 기능이 아니며, 다른 환경에서는 같은 역할 계약을 가진 worker로
대체할 수 있다.

#### 3.1 핵심 팀

| Agent | 역할 | 사용 방식 |
| --- | --- | --- |
| Fable | main, 설계자, 판정자 | 작업 틀·packet·통합·최종 보고 |
| Opus | 1단 기본 worker | one-shot 조사·초안·범위 점검 |
| Codex | 1단 전문 worker | 깊은 조사·구현·기계 검증 |
| Codex 작은 사장 | 2단 실행 관리자 | 큰 캠페인의 단일 접점 |
| Spark | Codex chain의 물량 worker | source 수집·반복 작업·초벌 결과 |

현재 snapshot에서 Codex 전문 agent는 `gpt-5.6-sol` 계열을 사용하고, Spark lane은
`gpt-5.3-codex-spark`를 사용한다. 모델 ID와 실행 설정은 영구 계약이 아니며 runtime
config에서 확인한다.

#### 3.2 역할별 Codex agent

| 이름 | 실제 질문 |
| --- | --- |
| `evidence_scout` | 판단 기준 원문, 과거 결정, 코드 좌표와 모순은 무엇인가 |
| `implementation_mechanic` | 이미 결정된 범위 안에서 어떤 diff와 검증이 필요한가 |
| `falsifier` | 이 설계나 완료 주장이 틀렸다는 반례가 있는가 |
| `closure` | 문서·잔재·worktree·검증 마감이 빠지지 않았는가 |
| `workflow_rationalist` | 지침과 workflow가 중복되거나 과도하게 복잡하지 않은가 |
| `learning_distiller` | 반복 실패에서 다음 작업에 재사용할 규칙은 무엇인가 |

실제 agent 동작을 분석할 때는 다음 세 specialist를 사용한다.

| 이름 | 확인 대상 |
| --- | --- |
| `agent_flow_observer` | API·DB·log·trace의 첫 divergence 지점 |
| `prompt_input_analyst` | 실제 조립 prompt, tool catalog와 context 충돌 |
| `agent_response_analyst` | model response, tool-call과 output contract |

이 운영 사례에서는 Fable이 설계 책임을 직접 유지하므로 `vp_router`와
`open_cognition_partner` 같은 별도 설계 동료를 사용하지 않는다. 이것은 Fable 기간의
선택이며 다른 main에도 적용되는 보편 규칙은 아니다.

### 4. 일반 worker packet

아래 양식을 작업에 맞춰 채운다.

```text
Goal:
Why this matters:
Decision basis / source of truth:
Owned scope:
Allowed reads, writes and external actions:
Forbidden scope and protected paths:
Decisions already made by Fable:
Questions the worker may answer autonomously:
Questions that must return to Fable or the user:
Expected return:
Verification:
Stop condition:
Remaining-risk format:
```

#### packet 최소 품질

- 목표를 파일 목록이 아니라 결과 상태로 적는다.
- 판단 기준 원문과 확인 순서를 먼저 준다.
- write 범위와 금지 범위를 같이 적는다.
- 성공 확인뿐 아니라 실패를 드러낼 검증을 적는다.
- 범위가 불완전하면 evidence와 option을 반환하게 한다.
- 보고 문장보다 diff, 원문 좌표와 실행 결과를 요구한다.

### 5. Opus one-shot 지침

Opus는 짧고 독립적인 1단 worker의 기본값이다.

- 한 packet을 한 turn 안에서 완료하거나 blocker로 반환한다.
- worker가 다시 worker를 고용하지 않는다.
- persistent teammate나 장기 idle-wait로 운영하지 않는다.
- 독립 조사 여러 개는 한 번에 병렬 발주할 수 있다.
- 작은 설계 초안을 쓸 수 있지만 채택과 최종 문안은 Fable이 판정한다.
- background로 보낼 때는 Fable이 실제로 병행할 판단 작업이 있을 때만 사용한다.

기본 목표는 worker와의 왕복을 늘리는 것이 아니라 완결된 packet 하나와 최종 반환
하나로 끝내는 것이다.

### 6. Codex 작은 사장 skill

작은 사장은 큰 작업의 설계자가 아니다. Fable이 정한 설계와 경계 안에서 여러
Codex worker를 운영하는 실행 대리 orchestrator다.

#### 6.1 언제 쓴다

- 여러 모듈을 같은 기준으로 반복 조사해야 한다.
- 조사 결과에 따라 구현·검증 worker를 순서대로 배치해야 한다.
- 독립 lane을 병렬 처리하고 하나의 보고로 통합해야 한다.
- Fable이 각 worker를 직접 관리하면 판단 context가 물량 관리에 잠식된다.

#### 6.2 반드시 지키는 경계

```text
Fable main
└─ Codex 작은 사장
   ├─ Codex/Spark worker A
   ├─ Codex/Spark worker B
   └─ Codex/Spark worker C
```

- 위임 깊이는 여기서 끝난다. 작은 사장이 또 작은 사장을 만들지 않는다.
- child 고용 권한은 packet에 명시된 경우에만 생긴다.
- child의 write·network·외부 게시 권한은 작은 사장 packet에서 명시적으로 제한한다.
- 설계 변경, scope 확대, 사용자 승인과 최종 위험 수용은 Fable에게 돌려보낸다.
- 작은 사장은 merge, 배포와 최종 완료를 독자적으로 결정하지 않는다.
- Fable은 작은 사장 아래 worker를 하나씩 직접 지휘하지 않는다.

#### 6.3 작은 사장 packet 추가 항목

일반 worker packet에 다음을 추가한다.

```text
Casting: 너는 구현 worker가 아니라 실행 대리 orchestrator다.
Authority: 설계와 최종 판정은 Fable 소유다.
May spawn child workers: yes | no
Depth limit: Fable → 작은 사장 → worker
Concurrent child scope:
Inherited write/network/publication boundaries:
Prepaid design rulings:
Return unresolved design as: evidence + options
Turn/session-limit recovery:
```

#### 6.4 반환 예시

```text
Status: completed | blocked | failed
Campaign verdict:
Child workers used, or short reason for none:
- worker / scope / result / verification
Changed files:
Decisive evidence:
Verification commands and results:
Unresolved design blockers:
Remaining risk:
Recommended next lane:
```

Fable과 작은 사장 사이의 연락은 두 종류로 제한한다.

1. 선지급한 ruling으로 해결할 수 없는 진짜 설계 blocker
2. stop condition에 도달한 최종 보고

진행 상황은 task board나 ledger에 남기고 단순 상태 보고로 Fable을 반복 호출하지 않는다.

### 7. 완료·권한·wake 실전 규칙

#### worker 성공 보고는 완료가 아니다

다음은 증거일 수 있지만 단독 완료판정은 아니다.

- worker가 `completed`를 반환했다.
- 범위를 한정한 test가 통과했다.
- 여러 agent가 같은 결론에 동의했다.
- 검색 결과 residue가 0건이다.
- falsifier나 closure가 즉시 gap을 찾지 못했다.

Fable은 실제 diff, 핵심 원문, 실행 결과와 남은 위험을 보고 완료를 판단한다.

#### Boss Mode는 권한을 넓히지 않는다

- prompt의 “이 파일만 수정”은 filesystem sandbox가 아니다.
- 현재 trusted profile의 넓은 권한은 별도 실행 설정이지 Boss Mode 권한이 아니다.
- 외부 재현은 `read-only` 또는 `workspace-write`에서 시작한다.
- production·외부 시스템·데이터 손실 가능 작업은 사용자 처분을 받는다.
- secret을 prompt, stdout, stderr, log와 result file에 넣지 않는다.
- 다른 session이나 worker의 변경을 되돌리거나 덮어쓰지 않는다.

#### background wake를 추측하지 않는다

- Fable → Opus는 one-shot 반환을 기본으로 한다.
- Fable → Codex는 top-level `/codex-bg` 완료 wake를 사용한다.
- Codex 작은 사장 아래 chain은 전부 Codex로 구성한다.
- Claude background sub-agent가 다시 background 작업을 시작하면 중간 agent가 완료
  wake를 받지 못할 수 있다.
- Codex의 동기 `claude-coder` MCP는 Claude 결과를 기다리는 호출이며 background
  carrier가 아니다.
- 긴 Codex 캠페인은 turn 단위로 나누고 Fable이 같은 작은 사장을 resume한다.

### 8. 시작 전 8개 체크

- [ ] 사용자 결정과 Fable 자율 결정을 나눴는가
- [ ] Fable이 직접 소유할 설계·판정 지점을 적었는가
- [ ] 작업 모양에 맞는 worker 또는 작은 사장을 골랐는가
- [ ] packet에 판단 기준, write 경계와 stop condition이 있는가
- [ ] 작은 사장에게 child 권한과 깊이 제한을 명시했는가
- [ ] worker 결과를 검증할 산출물과 command가 정해졌는가
- [ ] falsifier 또는 closure가 필요한 위험인지 판단했는가
- [ ] background completion과 wake 경로를 확인했는가

## 설계 배경과 상세 기준

<details>
<summary><strong>왜 이런 구조를 쓰는지 펼쳐보기</strong></summary>

이 아래는 실전 지침을 만든 이유와 다른 환경에 이식할 때의 판단 기준이다.

### 9. 추론 고도를 유지한다는 뜻

추론 고도 유지는 숫자형 추론 설정을 뜻하지 않는다. Fable의 context와 판단력을
되돌리기 어려운 결정에 보존한다는 뜻이다.

Fable을 모든 작업에 직접 투입하면 희소한 고추론 context가 검색 결과 정리, 반복
편집, 테스트 대기와 로그 수거에 소모된다. 사장모드는 Fable을 놀게 만드는 방식이
아니다. Fable이 결정 가치가 높은 지점을 직접 잡게 하는 방식이다.

#### Fable이 직접 소유한다

- 사용자의 진짜 목표와 성공 조건
- architecture, module boundary, safety와 permission 경계
- 되돌리기 어려운 trade-off와 durable decision
- lane 분리와 delegation packet
- 충돌하는 evidence의 통합과 최종 판정
- 사용자에게 물을 결정과 main이 흡수할 구현 선택의 분류
- 결정적인 증거의 직접 확인
- 남은 위험과 최종 사용자 보고

#### 기본적으로 위임한다

- 넓은 repository 검색과 source 좌표 수집
- 과거 결정과 변경 이력 조사
- 반복되는 파일별·모듈별 점검
- 이미 결정된 설계의 구현과 기계적 수정
- test, simulation, lint와 build 실행
- log 수거, 결과 분류와 첫 요약
- 숨은 consumer와 잠복 분기 탐색
- 문서 초안과 독립 표면의 병렬 확인

Fable은 worker의 긴 조사 과정을 전부 반복하지 않는다. 결론을 바꿀 원문, diff와
실행 결과를 직접 확인한다. 이것이 **얇은 사장** 운영이다.

### 10. 왜 Opus는 one-shot이고 작은 사장은 Codex인가

Opus는 넓은 조사와 초안을 한 번에 반환하는 1단 worker로 사용한다. 장기 teammate로
두면 idle·resume 과정과 context 유지 비용이 커진다. 그래서 한 packet, 한 반환을
기본으로 한다.

큰 캠페인은 Codex 작은 사장에게 맡긴다.

- Codex는 코드·도구·검증 중심 worker를 직접 운영할 수 있다.
- 작은 사장이 child 결과를 한 atomic campaign 안에서 통합할 수 있다.
- Fable은 작은 사장 한 명과만 접촉해 판단 context를 보존한다.
- Spark 같은 물량 worker도 Codex chain 안에서 사용할 수 있다.
- 중간 Claude/Opus background agent의 wake 마찰을 피할 수 있다.

이 topology는 현재 client에서 관찰한 wake 특성에 맞춘 선택이다. 다른 도구가 nested
wake와 durable result queue를 지원하면 구조를 다시 설계할 수 있다.

### 11. 권한이 아래로 내려갈수록 좁아지는 이유

| 주체 | 소유하는 것 |
| --- | --- |
| 사용자 | 정책, safety, public contract, 큰 dependency, prod·외부 적용, data-loss 위험 |
| Fable | task 순서, architecture, packet, 구현안 채택, 통합, 승인 요청과 최종 보고 |
| 작은 사장 | packet 안의 task 분해, child 배치와 실행 순서 |
| worker | 범위 안의 조사·구현·검증 |
| falsifier / closure | 반증 evidence와 마감 gap 보고 |

Subagent의 합의는 증거를 강하게 만들지만 승인을 만들지는 않는다. Worker가
`decision needed`라고 썼을 때도 Fable이 먼저 분류한다.

- 정책·safety·공개 계약·데이터 손실이면 사용자에게 묻는다.
- 승인된 boundary 안의 구현 선택이면 Fable이 정하고 사후 보고한다.
- evidence 부족이면 bounded 조사 packet으로 돌린다.
- blocker가 아닌 독립 lane은 계속 진행한다.

### 12. 포화 조사와 advisor-loop 제한

포화는 무한 조사가 아니다. 새 evidence가 다음 결정을 바꾸는 동안만 조사하는 방식이다.

1. 첫 pass에서 조사 대상 전체 목록이 맞는지 반증한다.
2. contract, registry나 dispatch table에서 표면을 다시 도출한다.
3. 한 pass에는 `runtime log`, `DB state`, `permission`, `dead consumer`처럼 하나의
   named surface만 둔다.
4. 새 decision-changing evidence가 없거나 결과가 반복되면 멈춘다.
5. 다음 행동이 사용자 질문, worker patch, 검증 또는 park로 좁혀지면 넘긴다.

같은 결정을 advisor에게 반복 질문하지 않는다. routing 답변 하나와
specialist/falsifier 답변 하나를 받았다면 다음 행동은 Fable의 결정, 사용자 질문,
실행 packet 또는 검증이어야 한다.

작고 되돌리기 쉬운 작업은 full saturation을 생략할 수 있다. live/runtime/security/DB
등 실제 상태가 correctness를 좌우하면 실행 evidence가 나올 때까지 확인한다.

### 13. Fable의 로컬 재량과 넘지 않는 경계

이 로컬 운용에서는 Fable main에게 일부 절차를 이유 중심으로 선택할 재량을 부여했다.
이 재량은 시스템·사용자 지침, 법적·보안·권한 경계보다 우선하지 않으며, 외부에서 이
문서를 읽었다고 자동으로 생기지 않는다.

넘지 않는 경계:

- 데이터 손실이 가능한 작업과 destructive git
- production 또는 외부 시스템의 실제 적용
- safety, permission과 public contract 변경
- secret·credential 노출
- 다른 session 산출물의 무단 복원·삭제
- Fable을 조사·구현 물량에 계속 소모하는 운영
- worker 결과를 검증 없이 승인이나 완료로 바꾸는 행위

이 로컬 재량은 worker에게 “규칙을 알아서 무시해도 된다”는 권한으로 상속하지 않는다.

### 14. 흔한 실패 패턴

| 실패 | 교정 |
| --- | --- |
| Fable이 broad 검색과 반복 작업을 직접 든다 | 물량을 Opus·Codex packet으로 분리한다 |
| worker에게 “알아서” 맡긴다 | 판단 기준, write 경계, 반환 형식과 stop condition을 준다 |
| 작은 사장이 다시 작은 사장을 만든다 | 깊이를 두 단계로 고정하고 lane 또는 turn을 나눈다 |
| worker 성공 보고를 완료로 선언한다 | Fable이 diff·실행 결과·남은 위험을 확인한다 |
| 같은 결정을 advisor에게 반복 질문한다 | 두 advisory input 뒤에는 main action으로 전환한다 |
| background wake를 추측한다 | client별 wake를 검증하고 one-shot 또는 durable queue를 쓴다 |
| 모델명을 역할 계약처럼 고정한다 | 역할과 반환 계약은 문서, 모델은 runtime config에 둔다 |

### 15. 이식 가능한 핵심

Fable이라는 이름보다 역할 분리가 중요하다.

1. 설계·위험 판단·통합에 가장 신뢰하는 모델을 main으로 둔다.
2. 조사 one-shot, coding worker와 물량 worker를 구분한다.
3. child agent를 운영할 수 있을 때만 작은 사장을 둔다.
4. 위임 깊이는 처음부터 두 단계로 제한한다.
5. 권한과 wake 동작은 실제 client에서 검증한다.
6. falsifier와 closure는 모델명이 아니라 질문과 반환 계약으로 정의한다.
7. 정확한 모델과 추론 설정은 runtime config에서 관리한다.

Boss Mode 자체는 특정 wake transport나 app-server controller를 요구하지 않는다.
Claude ↔ Codex 호출과 자동 wake 구성은 [README](README.md)에서 별도로 설명한다.

좋은 사장모드의 기준은 Fable이 많은 파일과 명령을 직접 처리한 것이 아니다. Fable이
중요한 판단을 놓치지 않았고, 검증 가능한 물량이 적절한 agent에게 배분됐으며,
최종 책임과 위험 판단이 main과 사용자에게 남아 있는 것이다.

</details>
