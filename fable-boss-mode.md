# Fable 사장모드: 2026-07 운영 사례와 이식 가능한 패턴

이 문서에서 Fable은 2026-07 로컬 환경에서 설계·판정용 main으로 선택한 모델 또는
별칭이다. 공개 가용성이나 다른 모델보다 보편적으로 우월하다는 주장을 전제하지 않는다.
이식 가능한 핵심은 신뢰하는 고추론 main에 결정 책임을 남기고, 검증 가능한
조사·구현·검증 물량을 다른 agent에게 분리하는 방식이다.

| 항목 | 기준 |
| --- | --- |
| 작성일 | 2026-07-13, Asia/Seoul |
| 현재 main | Fable |
| 기본 팀 | Opus one-shot worker + Codex worker/작은 사장 |
| 적용 상태 | Fable 운용 기간의 현재 기준이며 영구 모델 규격은 아님 |

이 문서에서 말하는 **추론 고도 유지**는 숫자형 추론 설정을 뜻하지 않는다.
Fable의 context와 판단력을 되돌리기 어려운 결정에 보존한다는 뜻이다.

## 1. 사용자 요약

- Fable 사장모드는 Fable을 main agent이자 최종 판정자로 두는 운영 방식이다.
- 사람 사용자는 목표, 정책, 승인과 위험 수용의 최종 권한자다.
- Fable은 문제 정의, 설계, 경계, 완료 기준과 사용자 보고를 소유한다.
- 넓은 조사, 자료 수집, 반복 구현과 테스트 실행은 worker에게 맡긴다.
- 짧고 독립적인 1단 작업은 주로 Opus one-shot worker가 수행한다.
- 깊은 코드 조사와 기계 검증은 Codex 전문 worker가 수행한다.
- Codex 작은 사장 아래의 대량 수집·반복 작업에는 Spark 같은 물량 worker를 활용한다.
- 여러 작업을 순서대로 지휘해야 하면 Codex 작은 사장을 세운다.
- 작은 사장은 여러 Codex worker를 관리하지만 설계권과 완료판정권은 갖지 않는다.
- 위임 깊이는 `Fable → 작은 사장 → worker`까지만 허용한다.
- Worker의 성공 보고와 여러 agent의 합의는 증거이지 승인이 아니다.
- Fable은 결정적인 증거를 직접 확인하고 최종 위험을 판단한다.
- 고위험 완료 주장에는 falsifier를, 마감 파생작업에는 closure를 사용한다.
- Boss Mode는 filesystem, network, production 권한을 자동으로 확대하지 않는다.
- 좋은 사장모드는 agent 수가 많은 상태가 아니라 Fable의 판단력이 중요한 결정에 보존된 상태다.

## 2. 핵심 용어

| 용어 | 뜻 |
| --- | --- |
| 사용자 | 목표와 최종 처분 권한을 가진 사람 |
| main / 사장 | 목표·설계·경계·판정·최종 보고를 소유하는 Fable |
| worker / 직원 | 정해진 범위 안에서 조사·구현·검증을 수행하는 agent |
| one-shot | 한 번의 요청 안에서 완료 또는 blocker를 반환하고 장기 대기하지 않는 방식 |
| 작은 사장 / deputy | 여러 worker를 운영하는 2단 실행 관리자 |
| lane | 독립적인 범위와 완료 조건을 가진 작업 단위 |
| delegation packet | 목표·범위·권한·산출물·중단 조건을 적은 작업 지시서 |
| evidence | main의 판단에 쓰는 근거. 승인이나 완료판정 자체는 아님 |
| falsifier | 설계나 완료 주장이 틀렸다는 증거를 찾는 반증 agent |
| closure / 감리 | 문서·검증·잔재·worktree 등 마감 파생작업을 확인하는 agent |

## 3. 전체 구조

```text
사람 사용자
└─ Fable main — 설계·판정·통합·위험 수용·최종 보고
   ├─ Opus one-shot worker — 조사·병렬 확인·초안·범위 한정 검증
   ├─ Codex 전문 worker — 깊은 원인 조사·구현·기계 검증
   ├─ falsifier / closure — 반증과 마감 감리
   └─ Codex 작은 사장 — 큰 캠페인의 단일 실행 접점
      ├─ Spark 또는 evidence worker — 조사·수집·반복 물량
      ├─ implementation worker — 이미 결정된 구현
      └─ verification worker — 테스트·로그·결과 검증
```

위 구조에서 권한은 아래로 내려갈수록 좁아진다. Worker가 많아져도 설계권,
사용자 승인 요청, 최종 완료판정과 위험 수용은 Fable main에 남는다.
여기서 Fable의 위험 판단은 사용자가 맡긴 작업 범위 안의 통합 판단이다. 정책, 안전,
공개 계약, 데이터 손실, production·외부 적용처럼 사용자 처분이 필요한 결정은 사람에게
돌려보낸다.

## 4. Fable의 추론 고도를 유지한다는 뜻

Fable을 모든 작업에 직접 투입하면 희소한 고추론 context가 검색 결과 정리,
반복 편집, 테스트 대기와 로그 수거에 소모된다. 사장모드는 Fable을 놀게 만드는
방식이 아니다. Fable이 **결정 가치가 높은 지점만 직접 잡게 하는 방식**이다.

### Fable이 직접 소유하는 일

- 사용자의 진짜 목표와 성공 조건 정의
- 현재 문제의 판단 기준 원문(SoT)과 판단 순서 결정
- architecture, module boundary, safety와 permission 경계
- 되돌리기 어려운 trade-off와 durable decision
- 어떤 작업을 한 lane으로 묶거나 분리할지 결정
- worker와 작은 사장에게 줄 delegation packet 작성
- 서로 충돌하는 worker 결과의 통합과 최종 판정
- 사용자에게 물어야 할 결정과 main이 흡수할 구현 결정을 분류
- 결정적인 증거의 직접 확인
- 남은 위험 수용과 최종 사용자 보고

### 기본적으로 위임하는 물량

- 넓은 repository 검색과 source 좌표 수집
- 과거 결정, 문서, issue와 변경 이력 조사
- 반복되는 파일별·모듈별 점검
- 이미 결정된 설계의 구현과 기계적 수정
- 테스트, simulation, lint와 build 실행
- 로그 수거, 결과 분류와 첫 번째 요약
- 숨은 consumer, 테스트·mock이 참조하는 import 경로와 잠복 분기 탐색
- 첫 번째 문서 초안과 표·목록 정리
- 독립된 여러 표면의 병렬 확인

Fable은 worker의 긴 조사 과정을 다시 전부 반복하지 않는다. 대신 결론을 바꿀 수
있는 원문, diff, 실행 결과와 실패 경로를 직접 확인한다. 이것이 **얇은 사장**
운영이다.

## 5. 로컬 재량과 넘지 않는 경계

이 로컬 운용에서는 Fable main에게 일부 작업 절차를 이유 중심으로 선택할 재량을
부여했다. 이 재량은 시스템·사용자 지침, 법적·보안·권한 경계보다 우선하지 않으며,
외부 사용자가 이 문서를 적용했다고 자동으로 생기지 않는다. 절차 변경도 해당
프로젝트가 main에게 명시적으로 맡긴 범위 안에서만 가능하다.

- 데이터 손실이 가능한 작업과 destructive git 명령
- production 또는 외부 시스템에 대한 실제 적용
- safety, permission과 public contract 변경
- secret, token과 credential의 노출
- 다른 session이나 worker가 만든 변경의 무단 복원·삭제
- Fable을 조사·구현 물량에 지속적으로 소모하는 운영
- worker 결과를 검증 없이 승인이나 완료로 바꾸는 행위

이 로컬 재량은 Fable main의 판단 방식이다. Worker에게 “규칙을 알아서 무시해도 된다”는
권한으로 상속하지 않는다.

## 6. 작업 모양에 따라 팀을 고른다

| 작업 모양 | 기본 선택 | 이유 |
| --- | --- | --- |
| 문제와 좌표가 이미 분명한 아주 작은 문서·지침 수정 | Fable 직접 | 위임 비용이 작업보다 클 수 있음 |
| 한 번에 끝나는 조사·범위 점검·초안·한정 검증 | Opus one-shot | 넓게 읽고 한 번에 결과를 반환 |
| 깊은 원인, 숨은 consumer, 테스트·mock import 경로, 정확한 구현 | Codex 전문 worker | 코드·도구·검증 중심 작업에 적합 |
| Codex 작은 사장 내부의 대량 수집·반복 편집·장문 요약 | 작은 사장 → Spark worker | 판단보다 처리량이 중요한 작업 |
| 여러 lane이 의존하며 조사와 구현이 이어지는 캠페인 | Codex 작은 사장 | Fable과의 접점을 하나로 유지 |
| 되돌리기 어려운 설계 갈림길 | Fable 직접 판단 | Fable 기간에는 별도 설계 동료를 두지 않음 |
| live/runtime/security/DB 등 고위험 완료 주장 | falsifier + Fable | 성공 확인이 아니라 반례 탐색 필요 |
| 다파일 작업의 문서·잔재·검증 마감 | closure + Fable | 파생작업 누락을 별도 표면으로 확인 |

작업이 크다는 이유만으로 작은 사장을 세우지는 않는다. 여러 worker의 순서,
의존성, 반복 배분과 통합이 실제로 필요할 때 사용한다.

## 7. 현재 사용하는 agent와 역할

모델과 agent 이름은 2026-07 로컬 배치다. 역할 계약이 핵심이며 정확한 실행 설정은
실행 시점의 config에서 확인한다.

### 7.1 핵심 실행 팀

| Agent | 현재 역할 | 사용 시점 |
| --- | --- | --- |
| Fable | main, 설계자, 판정자 | 모든 사장모드의 작업 틀·통합·최종 보고 |
| Opus one-shot | 1단 기본 worker | 조사, 병렬 범위 점검, 작은 설계 초안, 문서 실무, 한정 검증 |
| Codex worker | 1단 전문 worker | 깊은 원인 조사, 구현, 숨은 경로 탐색, 기계 검증 |
| Codex 작은 사장 | 2단 실행 관리자 | 조사+구현 물량이 큰 캠페인 |
| Spark | Codex 계열 물량 엔진 | source 수집, 장문 요약, 반복 수정, 초벌 구현, 병렬 검증 |

현재 snapshot에서 Codex 전문 agent는 `gpt-5.6-sol` 계열을 사용하고, Codex chain
안의 Spark 물량 lane은 `gpt-5.3-codex-spark`를 사용한다. 이 모델 ID는 현재 배치를
설명할 뿐 공개 가용성이나 영구 계약을 뜻하지 않는다.

### 7.2 Codex 전문 agent 구성

아래 이름은 이 로컬 환경의 사용자 정의 agent 예시이며 Claude Code나 Codex의 기본 제공
기능이 아니다. 외부 환경에서는 같은 질문과 반환 계약을 가진 일반 worker로 대체한다.

| Agent | 맡기는 일 | 권한 성격 |
| --- | --- | --- |
| `evidence_scout` | 현재 SoT, 과거 결정, 코드·문서 근거와 모순 수집 | read-only 조사 |
| `implementation_mechanic` | 이미 결정되고 범위가 고정된 코드·테스트·도구 수정 | 제한된 쓰기 |
| `falsifier` | 착수 전 가정 또는 완료 주장의 반례 탐색 | read-only 반증 |
| `closure` | 문서, SoT, 잔재, worktree, 오래된 표현, 검증 gap 감리 | 제한된 마감 실무 |
| `workflow_rationalist` | prompt·지침·workflow의 중복과 과잉 복잡도 점검 | read-only 합리화 |
| `learning_distiller` | 반복 실패와 재작업을 다음 작업 규칙으로 증류 | 드문 회고 작업 |

### 7.3 실제 동작 분석용 전문 agent

| Agent | 맡기는 일 |
| --- | --- |
| `agent_flow_observer` | API·DB·log·trace를 따라 첫 divergence 지점 찾기 |
| `prompt_input_analyst` | 실제 조립된 prompt, tool catalog, context 충돌 분석 |
| `agent_response_analyst` | 실제 model response, tool-call과 output contract 분석 |

이 세 agent는 일반 코드 리뷰용이 아니다. 실제 실행 증거가 있는 행동 이상을
진단할 때 사용한다.

### 7.4 Fable 기간에 사용하지 않는 설계 partner

이 로컬 사용자 정의 agent 구성에는 `vp_router`와 `open_cognition_partner` 역할도 있지만
Fable 기간에는 사용하지 않는다. 이 운영 사례에서는 Fable main이 설계 책임을
유지했기 때문에 별도 설계 co-thinker를 두지 않았다. 이는 다른 main 모델에도 적용되는
보편 규칙이 아니다. Sonnet도 현재 사례에서는 routine worker가 아니라 Opus와 Codex를
사용할 수 없을 때의 제한된 fallback이다.

## 8. Opus one-shot worker와 일하는 법

Opus worker는 **한 번 받아서 한 번에 끝내는 1단 직원**이다.

- 한 packet에 목표와 범위를 완결해 준다.
- 독립된 조사 여러 개는 동시에 보낼 수 있다.
- worker가 다른 worker를 다시 고용하게 하지 않는다.
- 장기 idle 상태로 남겨두거나 persistent teammate로 운영하지 않는다.
- 완료, blocker와 근거를 한 번의 반환에 담게 한다.
- background로 보낼 때는 main이 실제로 병행할 판단 작업이 있을 때만 사용한다.
- 결과가 빠지면 idle worker를 반복해서 깨우기보다 packet을 고쳐 새로 발주한다.

Opus에게 작은 설계 초안을 맡길 수는 있다. 하지만 초안의 채택·수정과 최종 의미는
Fable이 직접 판정한다.

## 9. Codex 작은 사장과 일하는 법

작은 사장은 큰 작업을 대신 결정하는 agent가 아니다. Fable이 미리 정한 설계와
경계 안에서 여러 worker를 배치하고, 의존 순서를 관리하며, 결과를 한 번에 통합하는
**실행 대리 orchestrator**다.

### 9.1 언제 세우는가

- 여러 모듈이나 표면을 같은 기준으로 반복 조사해야 할 때
- 조사 결과에 따라 구현 worker를 순서대로 투입해야 할 때
- 서로 독립적인 두 개 이상의 lane을 병렬로 처리할 가치가 있을 때
- Fable이 각 worker를 직접 지휘하면 판단 context가 물량 관리에 잠식될 때
- 진행 상태와 검증 결과를 하나의 ledger로 유지해야 할 때

### 9.2 권한 구조

```text
Fable main
└─ Codex 작은 사장
   ├─ Codex worker A
   ├─ Codex worker B
   └─ Codex worker C
```

- 깊이는 여기서 끝난다. 작은 사장이 또 다른 작은 사장을 만들지 않는다.
- 작은 사장은 packet이 허용한 경우에만 child worker를 고용한다.
- 작은 사장 packet에는 child가 parent보다 넓은 write, network, 외부 게시 권한을
  갖지 않도록 명시한다.
- protected path, 금지 범위, stop condition은 모든 child에게 그대로 내려간다.
- 설계 변경, scope 확대, 사용자 승인과 최종 위험 수용은 Fable에게 돌려보낸다.
- 작은 사장은 merge, 최종 배포와 완료 선언을 독자적으로 결정하지 않는다.

### 9.3 Fable과 단일 접점을 유지한다

Fable은 작은 사장 아래의 worker를 하나씩 직접 관리하지 않는다. 작은 사장이
task 분해, worker 배치, 결과 수집과 1차 통합을 맡는다. Fable이 받는 연락은 다음으로
제한한다.

1. 선지급한 판정 규칙으로 해결할 수 없는 진짜 설계 blocker
2. 정해진 stop condition에 도달한 최종 보고

진행 상황은 task board나 ledger에 남기고, 단순 상태 보고를 위해 Fable을 반복 호출하지
않는다.

### 9.4 작은 사장 packet에 반드시 들어갈 것

- “설계와 최종 판정은 Fable 소유”라는 문장
- “너는 순수 구현 worker가 아니라 실행 대리 orchestrator”라는 casting
- child worker를 고용할 수 있는지 여부
- 최대 위임 깊이와 동시에 운영할 child 범위
- 각 child가 물려받을 write·network·외부 게시 경계
- Fable이 이미 내린 architecture와 구현 ruling
- 남은 불확실성을 설계하지 말고 evidence와 option으로 돌려보내는 규칙
- 사용한 child worker, 각 범위와 검증 결과
- 검증 명령, 실패 판정과 중단 조건
- session 또는 turn 한도에 닿았을 때 상태를 보존하는 방법

### 9.5 작은 사장의 반환 예시

```text
Status: completed | blocked | failed
Campaign verdict:
Child workers used, or short reason for none:
- worker / scope / result / verification
Changed files:
Decisive evidence:
Verification commands and results:
Unresolved design blockers:
Residual risk:
Recommended next lane:
```

Child를 사용하지 않았다면 작은 사장 역할이 실제로 필요했는지 Fable이 다시 확인할 수
있도록 간단한 이유를 덧붙인다.

## 10. 왜 작은 사장은 Codex인가

현재 구성에서는 작은 사장과 그 아래 chain을 모두 Codex로 둔다.

- Claude background sub-agent가 다시 background 작업을 시작하면 완료 wake가 중간
  sub-agent로 돌아오지 않아 조용히 멈출 수 있다.
- Codex가 detached Claude를 호출하는 방향도 현재 안정적인 idle wake가 없다.
- 동기 `claude-coder` MCP는 Codex가 Claude 결과를 기다리므로 독립적인 background
  carrier가 아니다.
- 장기 Claude sub-agent는 resume 과정에서 의도한 worker model이 유지되지 않을 수 있다.

따라서 Fable은 top-level에서 Codex 작은 사장을 한 번 호출한다. 작은 사장은 자기
Codex subagent를 같은 atomic campaign 안에서 운영하고, 끝날 때 한 번 결과를 돌려준다.
긴 작업은 turn 단위로 나눠 Fable이 같은 campaign을 순차 resume한다.

이것은 모든 도구에 적용되는 보편 법칙이 아니다. 사용하는 client가 nested wake와
durable queue를 실제로 지원하면 topology를 다시 설계할 수 있다.

## 11. delegation packet 작성법

좋은 packet은 worker에게 “알아서 잘해”라고 하지 않는다. 판단에 필요한 구조를 먼저
주고, 아직 결정되지 않은 부분을 worker가 임의로 제품 결정으로 바꾸지 못하게 한다.

```text
Goal:
Why this matters:
Architecture / source-of-truth basis:
Owned scope:
Known aliases or neighboring hypotheses:
Allowed reads, writes and external actions:
Forbidden scope and protected paths:
Decisions already made by Fable:
Questions the worker may answer autonomously:
Questions that must return to Fable or the user:
Expected return shape:
Verification signal:
Stop condition:
Residual-risk format:
```

### packet 품질 기준

- 목표가 파일 목록이 아니라 결과 상태로 적혀 있어야 한다.
- 판단 기준 원문(SoT)과 판단 순서를 먼저 준다.
- write 가능 범위와 금지 범위를 함께 적는다.
- 결과가 틀렸음을 보여줄 수 있는 verification을 적는다.
- 범위가 불완전하면 확장하지 말고 evidence와 option을 반환하게 한다.
- known alias와 기각해야 할 이웃 가설을 적어 첫 가설 고착을 막는다.
- 보고 문장보다 확인할 산출물, diff와 실행 결과를 요구한다.

## 12. 기본 실행 흐름

```text
Frame
  → Lane classify
  → Packet design
  → Delegate
  → Evidence integration
  → Falsify when risk requires
  → Closure when derivative work exists
  → Fable final judgment and user report
```

### 12.1 작업 틀 정하기

Fable이 목표, 범위, 판단 기준 원문(SoT), 금지 경계, 사용자 결정과 완료 조건을 정한다.
조사 범위를 손으로 대충 열거하지 않고 contract, registry, dispatch table 같은 권위
source에서 가능한 전체 표면을 도출한다.

### 12.2 작업 lane 분류

다음 작업이 한 번에 끝나는 조사인지, 이미 결정된 구현인지, 반복 물량인지,
작은 사장이 필요한 campaign인지, Fable의 직접 설계 판단인지 분류한다.

### 12.3 Delegate

각 worker에게 owned scope, write boundary, expected return, stop condition과 verification을
준다. 서로 같은 일을 중복시키지 않는다. 두 worker를 병렬로 쓸 때는 독립된 결과가
실제로 다음 결정을 바꿀 수 있어야 한다.

### 12.4 Integrate

Fable은 worker 보고를 그대로 전달하지 않는다. 원문 근거, diff, test 결과와 불일치를
확인하고 채택·수정·기각한다. Worker의 `completed`는 실행 상태일 뿐 최종 완료가 아니다.

### 12.5 Falsify and close

완료가 live state, runtime, security, parity, DB 또는 대량 삭제에 달려 있으면
falsifier로 반례를 찾는다. 다파일·구조 변경처럼 문서와 잔재가 생기는 작업은 closure로
마감 파생작업을 확인한다. 두 agent 모두 Fable을 대신해 완료를 승인하지 않는다.

## 13. 조사와 포화 루프

포화는 조사량을 무한히 늘리는 방법이 아니다. **새 증거가 다음 결정을 바꾸는 동안만**
조사를 계속하는 방법이다.

### 13.1 먼저 frame을 반증한다

첫 pass에서는 발견 내용보다 조사 대상의 전체 목록이 맞는지 확인한다. 권위 source에서
표면을 다시 도출하고, 누락된 sibling, alias, legacy path와 dispatch branch가 없는지 본다.
틀린 frame 안에서 여러 번 검사해도 누락은 발견되지 않는다.

### 13.2 한 pass에는 하나의 named surface

예를 들면 `runtime log`, `DB state`, `permission boundary`, `dead consumer`,
`documentation alignment`처럼 한 표면만 정한다. 같은 질문을 표현만 바꿔 advisor에게
반복하지 않는다.

### 13.3 종료 조건

- 새 decision-changing evidence가 더 이상 나오지 않는다.
- finding이 generic하거나 이미 확인한 근거를 반복한다.
- 다음 행동이 user ask, worker patch, verification 또는 명시적 park로 좁혀졌다.
- 작은 reversible 작업이라 full saturation의 비용이 더 크다.

한 결정에 routing 답변 하나와 specialist/falsifier 답변 하나를 썼다면 다음 행동은
Fable의 결정, 사용자 질문, worker packet, 검증 또는 park여야 한다. 세 번째 advisor에게
같은 질문을 반복하지 않는다.

## 14. 권한과 결정 분류

| 주체 | 소유하는 결정 | 소유하지 않는 결정 |
| --- | --- | --- |
| 사용자 | 정책, scope 확대, safety, public contract, 큰 dependency, prod/외부 적용, data-loss 위험 | 내부 구현의 사소한 선택 |
| Fable main | task 순서, architecture, packet, 구현안 채택, 통합, 승인 요청, 최종 위험판정과 보고 | 사용자만 처분할 수 있는 변경 |
| 작은 사장 | packet 안의 task 분해, child 배치와 실행 순서 | architecture 변경, scope 확대, 최종 완료와 위험 수용 |
| worker | 범위 안의 조사·구현·검증 | 승인, 거부, merge, 배포와 완료판정 |
| falsifier / closure | 반증 evidence와 closing gap 보고 | veto, 승인과 최종 close |

Worker가 `decision needed`라고 썼다고 바로 사용자에게 전달하지 않는다. Fable이 먼저
다음처럼 분류한다.

- 사용자 결정이면 근거와 선택지를 정리해 직접 묻는다.
- 승인된 boundary 안의 구현 knob이면 Fable이 결정하고 결과를 사후 보고한다.
- worker가 evidence를 더 모으면 해소되는 문제면 새 bounded packet으로 돌린다.
- hard blocker가 아니면 독립된 다른 lane을 계속 진행한다.

## 15. 검수와 완료판정

다음은 모두 **완료 증거**일 수 있지만 단독으로 완료판정은 아니다.

- worker가 `completed`를 반환함
- 범위를 한정한 test가 통과함
- 여러 agent가 같은 결론에 동의함
- 검색 결과에서 residue가 나오지 않음
- falsifier가 즉시 반례를 찾지 못함
- closure가 큰 gap을 찾지 못함

Fable은 위험에 맞춰 결정적 경로를 직접 확인한다.

- 변경 파일과 worker가 주장한 파일 목록 대조
- 실제 diff와 최종 실행 경로 확인
- test command와 전체 output 또는 실패 signature 확인
- 삭제·이동 시 old path consumer와 테스트·mock import 경로 점검
- live/runtime 주장 시 실제 endpoint, log, DB state와 restart 경로 확인
- 실행하지 못한 검증을 남은 위험으로 명시

### falsifier와 closure의 차이

| 역할 | 핵심 질문 |
| --- | --- |
| falsifier | “이 설계나 완료 주장이 틀렸다는 반례가 있는가?” |
| closure | “결정 뒤에 따라오는 문서·잔재·검증·worktree 정리가 모두 끝났는가?” |

Falsifier는 위험에 따라 사용한다. Closure는 다파일·구조 변경과 같이 파생작업이 생기는
작업에서 기본적으로 사용한다. 작은 작업에서 agent 호출을 생략해도 Fable이 같은 감리
표면을 짧게 직접 확인한다.

## 16. context와 token을 아끼는 법

- Fable이 broad source dump를 직접 읽지 않게 worker가 좌표와 결정 증거를 압축한다.
- 단순 source 수집과 긴 요약은 Codex worker나 작은 사장에게 넘기고, 그 chain 안에서
  Spark를 우선 활용한다.
- Main은 이미 잘 요약된 source를 중복해서 다시 읽지 않는다.
- Worker에게 report shape를 미리 줘 불필요한 장문 결과를 막는다.
- Fable은 worker 결과 중 결정에 필요한 원문만 직접 확인한다.
- 완료된 agent는 닫고 passive context storage로 남겨두지 않는다.
- 같은 결정을 advisor에게 반복 질문하지 않는다.
- 진행 보고는 batch하되 red test, destructive/DB/live/security 위험과 user decision은 즉시 올린다.

Fable subagent를 추가로 띄우는 것은 기본 선택이 아니다. Fable은 main에만 두고,
물량은 Opus·Codex·Spark에 맡긴다. 그렇지 않으면 가장 희소한 판단 예산을 worker 작업에
중복 지출하게 된다.

## 17. 권한·보안·worktree 안전

Boss Mode는 자동 권한 상승 기능이 아니다.

- Prompt의 “이 파일만 수정”은 filesystem sandbox가 아니다.
- 현재 로컬 trusted profile은 일부 bounded write lane에서 넓은 filesystem 권한을
  사용할 수 있지만, 이는 Boss Mode가 자동으로 부여하는 권한이 아니라 별도 실행 설정이다.
- 외부 재현에서는 `read-only` 또는 `workspace-write`로 시작하고, 필요한 작업에 한해
  사람의 권한 정책에 따라 명시적으로 넓힌다.
- shell, write, network와 external service 권한을 실제 tool 설정에서 제한한다.
- prompt, stdout, stderr, log와 result file에 secret을 넣지 않는다.
- production, external system, destructive DB와 data-loss 작업은 사용자 승인을 받는다.
- 공유 worktree에서는 다른 session 변경을 되돌리거나 덮어쓰지 않는다.
- `git status`만 보고 모든 dirty file을 현재 worker의 변경이라고 단정하지 않는다.
- 외부 게시, merge와 배포 권한은 packet에 명시된 경우에만 부여한다.
- Child worker의 권한이 자동으로 제한된다고 가정하지 않는다. 작은 사장 packet에서
  parent의 경계보다 넓지 않게 명시한다.

## 18. 흔한 실패 패턴

### Fable이 물량까지 직접 수행한다

설계자가 broad grep, 긴 log, 반복 테스트와 기계 편집을 계속 들고 있으면 추론 고도가
낮아진다. Fable은 frame과 판정으로 돌아가고 물량을 worker packet으로 분리한다.

### worker에게 범위 없이 “알아서” 맡긴다

Worker가 제품 판단까지 추측하거나 무관한 cleanup으로 범위를 넓힌다. 목표, source of
truth, write boundary, stop condition과 report shape를 먼저 준다.

### 작은 사장이 또 작은 사장을 만든다

책임과 실패 지점이 보이지 않고 context가 여러 층에 흩어진다. 깊이는 두 단계에서
멈추고 더 큰 작업은 lane을 나누거나 Fable이 turn 경계에서 resume한다.

### worker 성공 보고를 완료로 선언한다

테스트 범위가 좁거나 실제 runtime이 다를 수 있다. Fable이 결정적인 경로와 residual
risk를 직접 판정한다.

### 같은 결정을 advisor에게 반복 질문한다

답변 수는 늘지만 다음 행동은 바뀌지 않는다. 두 번의 advisory input 뒤에는 Fable이
결정하거나 사용자에게 묻거나 실행 packet을 만든다.

### background wake를 확인하지 않고 chain을 만든다

중간 agent가 child 완료를 받지 못해 조용히 멈출 수 있다. client별 wake semantics를
먼저 검증하고, 지원되지 않으면 one-shot 동기 호출이나 durable result queue를 사용한다.

### 모델명을 역할 계약처럼 고정한다

모델 availability와 성능은 바뀐다. 문서에는 역할과 완료 계약을 남기고 실제 모델은
실행 config에서 선택한다.

## 19. 예시

### 예시 A: 넓은 문서 조사

1. Fable이 질문과 판정 기준을 정한다.
2. 두 개의 독립된 Opus one-shot worker에게 서로 다른 source 범위를 준다.
3. Fable이 근거 좌표와 모순만 통합한다.
4. 결과가 정책을 바꾸면 사용자에게 묻고, 아니면 Fable이 결론을 쓴다.

### 예시 B: 깊은 버그와 구현

1. Fable이 owning contract와 재현 조건을 정한다.
2. `evidence_scout` 또는 Codex 전문 worker가 원인과 숨은 consumer를 찾는다.
3. Fable이 원인을 판정하고 patch boundary를 확정한다.
4. `implementation_mechanic`이 수정과 범위 한정 검증을 수행한다.
5. Fable이 diff와 결정적 실행 경로를 확인한다.

### 예시 C: 여러 모듈을 바꾸는 캠페인

1. Fable이 architecture, 금지 경계와 완료 기준을 작은 사장 packet에 선지급한다.
2. Codex 작은 사장이 조사·구현·검증 lane을 나눈다.
3. Spark와 전문 worker가 반복 물량을 처리한다.
4. 작은 사장이 child 결과와 검증을 하나의 보고로 통합한다.
5. Fable이 중요한 근거를 직접 확인하고 필요하면 독립된 falsifier를 부른다.
6. Closure가 문서·잔재·worktree와 남은 검증을 확인한다.
7. Fable이 최종 위험을 판정하고 사용자에게 보고한다.

### 예시 D: model-facing prompt 변경

1. Worker는 현재 prompt 원문, 조립 경로와 실제 주입 결과를 수집한다.
2. Fable이 최종 문구를 직접 작성한다.
3. Worker는 확정된 문구를 그대로 적용하고 관련 검증을 실행한다.
4. Fable은 문장 단위로 결과와 실제 주입 전문을 확인한다.

## 20. 다른 환경에 적용하기

Fable이라는 이름보다 역할 분리가 중요하다.

1. 사용할 수 있는 모델 중 설계·위험 판단·결과 통합에 가장 신뢰하는 모델을 main으로 정한다.
2. 넓은 조사에 적합한 one-shot worker를 정한다.
3. 구현·검증에 강한 coding worker를 정한다.
4. 반복 물량을 처리할 저비용·고처리량 lane을 정한다.
5. Child agent를 관리할 수 있는 orchestrator가 있을 때만 작은 사장을 둔다.
6. 처음에는 `main → 작은 사장 → worker` 두 단계로 제한한다.
7. 각 tool의 write, network, sandbox와 wake 동작을 실제로 검증한다.
8. 자동 wake가 없으면 foreground one-shot이나 durable queue를 사용한다.
9. Falsification과 closure 역할은 모델명이 아니라 질문과 report contract로 정의한다.
10. 정확한 model과 추론 설정은 문서에 고정하지 않고 runtime config에서 관리한다.

## 21. 시작 전 체크

- [ ] 사람 사용자와 Fable이 각각 결정할 범위를 구분했는가
- [ ] Fable이 직접 소유할 고도 판단을 명명했는가
- [ ] 조사·구현·검증 물량을 worker lane으로 분리했는가
- [ ] 한 worker인지 작은 사장인지 작업 모양으로 선택했는가
- [ ] packet에 판단 기준 원문(SoT), write boundary와 stop condition이 있는가
- [ ] 작은 사장에게 child 권한과 깊이 제한을 명시했는가
- [ ] worker 결과를 검증할 산출물과 command가 정해졌는가
- [ ] falsifier 또는 closure가 필요한 위험인지 판단했는가
- [ ] background completion과 wake 동작을 실제 client에서 확인했는가
- [ ] 남은 사용자 결정과 위험을 보고할 자리가 있는가

Fable 사장모드의 성공 기준은 Fable이 많은 파일을 직접 읽고 많은 명령을 실행한 것이
아니다. Fable이 중요한 판단을 놓치지 않았고, 검증 가능한 물량이 적절한 agent에게
배분되었으며, 최종 책임과 위험 판단이 main과 사용자에게 남아 있는 것이다.

Boss Mode 자체는 특정 wake transport나 app-server controller를 요구하지 않는다.
Claude ↔ Codex 호출과 자동 wake 구성은 [README](README.md)에서 별도로 설명한다.
