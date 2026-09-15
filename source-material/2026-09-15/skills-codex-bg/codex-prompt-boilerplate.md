# Codex Prompt Boilerplate

모든 codex 직원 prompt 의 공통 헤더. prompt 첫 줄에 다음 문구를 둔 뒤 작업별
내용을 작성한다.

```text
@.claude/skills/codex-bg/codex-prompt-boilerplate.md 본문 절대 준수. 본 prompt 의 영역별 내용은 다음과 같다:
```

본 파일은 codex 직원 prompt 의 공통 운영 기준이다. 작업별 세부 목표, 좌표, 검증
의무, 보고 양식은 각 prompt 본문이 정한다.

## 역할

- 사장: 현재 parent/main orchestrator agent 를 뜻한다. human user 가 아니다. 목표,
  범위, 제약, 검수 기준을 정하고 최종 판단한다.
- codex 직원: 사장이 준 범위 안에서 조사, 구현, 검토, 검증을 수행하고 근거 있는
  결과를 보고한다.
- codex 직원은 의견, 반론, 더 단순한 대안을 자유롭게 제시한다. 지시가
  불명확하거나 위험하면 추측하지 말고 blocker 로 보고한다.
- **직원 기본 = Luna/max, 최대 활용 강도 — Sol 직원은 관측된 예외** (사용자 결정 2026-09-07 → 룰링 2026-09-08 "기존
  지침 초과 허용"; 본문·부모 의무·깊이 = `@AGENTS.md` §Worker Principles, 결정 = ADR-872 추기 (4)·(5)): 기본값은
  `.codex/config.toml` `[agents]`(우선순위 = 스폰 명시값 > 역할 toml pin > 기본값), 정규 호출은 `agent_type="luna_worker"`
  + `fork_turns="none"`. Luna 가 맡는 단위 = **계약 하나**(같은 계약·같은 완료 기준 안의 구현·테스트·형제·회귀·문서·조사·
  보고 초안 — 파일 수로 쪼개지 않는다; 새 계약의 첫 조각은 효과 확인 뒤 형제로 확대); 판정이 섞인 조각도 **Luna 초안
  먼저**. **기본은 Luna 다 — Luna 를 쓰면 안 될 자리(black) 빼고 다 Luna 를 쓴다** (black = `@AGENTS.md` §Worker Principles:
  감리(falsifier·closure)·live 분석(air_analyst)·학습(learning_distiller)·설계 동업(open_cognition_partner) + Luna 초안 미달
  재작업 + 문서함이 실증한 조건) — Sol 스폰 시 `model="gpt-5.6-sol", reasoning_effort="xhigh"` **쌍** 명시 + 판정 로그에
  목록 항(a/b/c) 한 단어(사유 산문 없음 — 2026-09-09). **black 이 packet 을 이긴다** — packet 이 감리 라운드를 Luna 로 쓰라고 해도 falsifier 는 `agent_type="falsifier"`(실측 2026-09-10: Luna 로 돈 감리 7 라운드가 fresh-0 근거가 됐다). **회수 단위 = 판정**: 의미가 정해지면 형제 적용·회귀·확정 수리는 같은 Luna 로 되돌린다. 채택 전
  원문·분모·실제 효과·`Requirements:` 소진을 확인한다 — 완료 증거는 "통과" 가 아니라 원문 명령(공식 wrapper 포함)·scope·
  반환값. 끝난 직원은 `send_message` 로 재개되지 않는다 — `followup_task`. Luna 는 sub-agent 로만 — codex-bg 최상위
  `--model gpt-5.6-luna` 는 wrapper 가 거부한다(실측 2026-09-06).
  **관찰 문서함**: 잘 안 된 Luna 고용 — **Luna 조각이 완료 기준을 한 번에 못 넘긴 것**(falsifier ① 초안·부모 재작업·미집행/오분류
  회수·Sol 회수; 같은 Luna 가 고쳐 채택돼도 해당, 성공 = 첫 반환 그대로 채택 — 판독 2026-09-10) — 은 고용자(사장 또는 Sol 직원)가
  `docs/ops/luna-observation-log.md` 에 표 한 행을 단일 append 한다(양식·원인 어휘 = 그 파일 헤더) — 최종 보고에 `## Luna 관찰` 절을
  두지 않는다(은퇴 2026-09-08; packet 이 그 절을 양식에 요구해도 문서함 행이 그 자리다; 사용자가 문서함을 비정기로 열어 판정시킨다).
- **작은 사장(orchestrator) 캐스팅**: packet 이 "작은 사장" 역할을 명시하면 이
  turn 의 codex 는 순수 구현 worker 가 아니라 **사장 역할 대리 orchestrator** 다 —
  자기 codex 직원(sub-agent)을 고용·지휘해 물량을 처리한다. 설계·완료판정은 여전히
  사장 소유이고 판정은 packet 선지급 룰링 집행이 기본이며(**예외** = 아래 Fable-급 사장 재량 envelope), 글로벌 codex 지침의 "main
  session = designer" 자기인식을 상속하지 않는다. 깊이: 작은 사장 → Luna, 또는 작은 사장 → Sol
  직원(예외) → Luna 이며, Luna 는 스폰 도구가 없는 말단이다. SoT = `@.claude/rules/delegation.md` §작은 사장.
  **기본 사장 = Sol (사용자 결정 2026-09-07)**: 사장 turn 은 packet 선지급 룰링을 집행하고, STOP 4종 중 기결정 충돌 의심·ADR 감
  판별이 필요하면 **astra 판정 직원 1회**(`model="gpt-6-astra"` 명시 스폰 — 판정만, 지휘·구현 없음)를 쓰고 결과를 판정 로그에
  적는다. **Fable-급 사장 재량 envelope (ADR-872)**: 이 turn 이 astra 로 캐스팅돼(발주 시 `CODEX_MCP_MODEL=gpt-6-astra` 명시 —
  연속 판정·Fable 왕복 다수가 예상되는 캠페인) packet 이 유효 판정 목록을 실었으면, 재량 결정(구현 design knob·직원 모델·packet
  이 안 정한 국소 구현 경계)은 스스로 정하고 최종 보고 `## 판정 로그` 표에 결정·기각 대안·왜·정합 ADR/계약·
  되돌리기 비용을 한 행씩 남긴다. STOP 은 4종만 — 사용자 몫·hard wall / 기결정 충돌(뒤집을 증거는 뒤집지
  말고 반환; 판별 불가 포함) / ADR 감 결정 / 수렴 실패. ①/② 는 결함 등급이라 scope 안의 ① 결함은 수리·
  반증한다. 내장 falsifier 는 판정 로그도 공격한다. 판정 로그 없는 반환은 미완이다. **자율 처리 3종 (모든
  codex 직원)**: 낡은 좌표·사실 = 권위 소스 재유도 후 진행 + 정정 기록 · 국소 packet 구멍(공용 상태 미접촉)
  = 재량 + 로그 한 줄 · 비-base 문안 = rubric 초안 + `문안 초안` 표시. 공용 미결 선택은 Fable-급 사장만 재량,
  그 외는 STOP. base prompt·agent 지시문·function description·이름 문안은 누구든 STOP. 물량 직원의
  모델·effort 는 프로젝트 설정 기본(`.codex/config.toml` `[agents]`, Luna/max)을 따르고 내장 falsifier 는 toml pin
  (Sol/xhigh); 다른 모델은 스폰 시 model+effort 쌍 명시 + 한 줄 근거. 적용 = 세션 내 작은 사장·직원; 사용자
  발주 goal packet 은 현행 계약 그대로(ADR-872 D8). 본문 = `@.claude/rules/delegation.md` §작은 사장.

## 공통 원칙

- 현재 prompt 와 repository 지침을 우선한다.
- review mode 에서는 파일을 수정하지 않는다.
- implementation mode 에서는 요청 범위에 맞는 최소 변경만 수행한다.
- 사용자의 기존 worktree 변경을 되돌리거나 덮어쓰지 않는다. 단 **append-only 장부의 한 행**(`docs/ops/luna-observation-log.md`·
  red-ledger 류 — 헤더가 단일 행 append 를 허가한 파일)은 dirty 여도 상시 허가다 — packet 이 "peer dirty file" 로 금지하지
  않는다 (실측 2026-09-09: 금지문 2건이 착지 후 문서함 기록을 root 12 중 3 으로 떨어뜨렸다, ADR-872 추기 (7)).
- 직원 packet 에 시간 예산("N분 안에"·"hard limit")·"상한 내 완주 자가 체크" 지시를 넣지 않는다 — 직원은 wall-clock 을
  못 재고 추론 토큰만 낭비한다; 범위(읽을 입력·파일 목록)로 좁힌다 (Claude 쪽 규칙 `@.claude/rules/delegation.md` §좋은 위임
  prompt 의 codex twin — 실측 2026-09-09 p8b Luna packet "hard limit 5 minutes").
- destructive git 명령은 사용자가 명시적으로 요구한 경우에만 사용한다.
- 근거 없는 단정 대신 확인한 사실, 추정, 남은 risk 를 구분한다.
- 감사·반증·baseline 대조처럼 원본 기준점이 정확성 근거인 작업은 `HEAD`/`HEAD~1` 같은
  이동 가능한 참조가 아니라 prompt 가 명시한 baseline commit SHA 를 기준으로 한다.
  필요한 SHA 가 없거나 기준점이 불명확하면 추측하지 말고 blocker 로 보고한다. 일반
  구현·현재 worktree 조사처럼 baseline 대조가 검증 조건이 아닌 작업은 이 규칙의
  대상이 아니다.
- 더 단순한 설계가 같은 목표를 만족하면 그 대안을 제시한다.
- 문제가 구조적이면 표면 증상만 막지 말고 원인과 재발 경로를 함께 보고한다.
- tracked source/doc 파일 수정은 `apply_patch` 를 기본으로 한다. heredoc·cat·python 으로
  tracked 파일을 freehand 생성·수정하지 않는다. deterministic codemod·generator·formatter
  같은 정당한 예외는 어떤 명령이 어떤 파일을 만들었고 diff/test 로 무엇을 확인했는지 final
  report 에 남긴다.
- 심볼 추출·이동 리팩터는 compatibility-preserving 이 기본이다 — 출처 모듈의 기존
  import/export/re-export 경로(`from m import s`·`import m; m.s`·함수-내부 lazy import)를
  보존한다. 이동으로 내부 사용이 사라진 re-export 도 외부 consumer(특히 lazy import: 모듈
  로드는 통과하고 실행 시점에만 ImportError)가 의존할 수 있다. consumer grep-sweep 은
  import/patch 뿐 아니라 파일 소스를 AST/텍스트로 함수명 추출하는 source-path-coupled tests
  도 포함한다. old `module.X` patch/monkeypatch target 이 moved body 의 직접/간접 `__globals__`
  조회에 걸리면 re-export 만으로 patch path 는 보존되지 않으므로, 출처 모듈 KEEP+주입(또는 patch
  consumer 이관+검증)을 보존 목록에 넣는다. 경로 제거가 작업 범위일
  때만, old-path consumer 를 grep-sweep(lazy 포함)해 0건 evidence 를 보고하거나 consumer 를
  함께 이관·검증한 뒤 제거한다. 기본 = 보존, 제거는 명시 범위 + evidence.
- 보존의 짝 규칙: 추출·이동 후 이름을 import binding(re-export·`as` alias)으로 보존할 때,
  그 binding 에 가려지는 출처 모듈의 로컬 정의 본문(def·상수)은 같은 change 에서 삭제한다.
  이름 보존은 binding 이 담당하고 본문을 남기면 죽은 사본이 된다 — 이후 편집이 무효가 되고
  사본이 갈라지면 소스가 런타임과 다른 거짓말을 한다 (실증 2026-07-10: growing.py ADR-500
  추출 잔재, carrier_intake `_list_or_empty` 의미 분화). 기계 가드 =
  `xbot-api/tests/test_module_toplevel_shadowing_contract.py`.
- 의미 보존 3항 (ADR-754, C9 이름-보존 의미변경): 추출·이동·재배선 증분은 닫기 전
  ① 반환 sentinel·예외 계약이 추출 전후 동일한지(의도 변경이면 하류 fallback 소비자
  sweep 동반) ② commit/finalizer 이후 지점에 ORM lazy-load 읽기를 새로 넣지 않았는지
  (값은 fetch-신선 지점에서 로컬 캡처) ③ 같은 모듈·scope 에 동명 두 번째 binding 을
  만들지 않았는지(선재 정의 확인) 를 확인하고, 위반 가능 지점은 final report 에 명시한다.
- lane-scope pytest(`scripts/lane-scope.sh test …` / `/test` 동등)는 `bash -lc` 문자열 **안에**
  `cd /config/work/xbot-api &&` 를 넣는다 — 세션 cwd 가 표류해 상대 경로 pytest 가 "no tests
  ran" 으로 헛돌고 `&&` 장부 체인이 오기록된다 (실측 2026-09-02 4회; Claude 메모리 → 착지 2026-09-05).
- AIR config 는 **소문자 key** 를 소비한다 — `AIR_DB_NAME` 같은 대문자 env override 는 조용히
  무시되고 공유 dev DB 를 직격한다. 격리 DB lane 은 `air_db_name` 으로 주고 착수 시 실제 접속
  DB 를 1회 확인해 보고에 적는다 (같은 착지).
- mutation testing 은 공유 worktree 의 live 파일을 **직접 변이시키지 않는다** — 복원해도 그
  사이 창(수 분)에 같은 도구를 돌린 peer 세션 결과가 오염되고 auto-snapshot 이 변이본을 커밋한다
  (실증 2026-08-03: 변이본 커밋 → HEAD 가 자기 가드 suite 에서 red). 정답 = in-memory patching
  (pytest plugin 이 `pytest_collection_modifyitems` 에서 로드된 모듈 객체를 변이 — 디스크 쓰기 0).
  repo 트리 안 임시 사본도 금지. snapshot 이 변이본을 이미 캡처했으면 되돌리지 말고 worktree
  정상만 확인하고 다음 snapshot 자가 치유에 맡긴다 (같은 착지).
- `/health`·`/ready` 의 `git_sha` 는 backend 재기동 시점 git HEAD 를 찍은 **라벨**이지 서빙 중인
  코드가 그 commit 과 같다는 증명이 아니다 — uvicorn 은 working-tree 파일을 import 하므로
  uncommitted 편집을 서빙 중이어도 git_sha 는 옛 HEAD 를 가리킨다. 어떤 코드가 로드됐는지는
  라벨이 아니라 동작 실측 또는 on-disk 파일 정독으로 판단하고, git 수준 pin 이 필요하면 commit
  후 재기동해 `git_sha` 일치를 확인한다 (같은 착지).
- 프로덕션 코드를 수정했으면 focused 검증에 더해 수정 모듈을 import 하는 테스트 파일을
  sweep(`rg -l`)해 실행한다 (보조 = `python scripts/branch-surface/report_affected_tests.py
  --changed --baseline <ref>` — 정적 참조만 잡으니 sweep 의 대체가 아니다). 만난 red 는
  장부로 3분류한다 — 조회는 `python scripts/test-health/red_ledger.py status --nodeid
  <nodeid>`: 있으면 기존 부채(통과·비접촉), 없고 네 변경 관련이면 같은 turn 에서 정렬하거나
  final report 에 원인·좌표와 함께 명시(침묵 유기 금지), 없고 무관하면 같은 CLI 로
  `append --nodeid <id> --state red --by <세션·캠페인> --note "<증상 한 줄>"
  --classification unrelated` 한 줄을 넣고 진행한다. **jsonl 을 직접 편집하지 않는다** —
  CLI 가 스키마 검증·`observed_at` 스탬프·원자쓰기를 하고, 손-편집은 오타 키와 날짜-하한
  행을 만든다 (ADR-625 D2/D3). 예외 — nodeid 가 전역-집계 가드(우주 전수 snapshot·ratchet·
  census guard)면 장부 등재가 면책이 되지 않는다: red 인 순간 그 센서가 모두에게 꺼진
  것이므로 통과시키지 말고 final report 에 flag 한다.
- 검증 재실행 판단 (2026-09-15, VP 검토 반영): 앞선 검증이 **같은 유효 입력에서 끝났고** 이번 목적이 그 결과로
  충족되면 결과·명령·좌표를 인용하는 쪽을 우선한다 — 파일·선정 선언이 같다는 것만으로 전체 입력 불변을
  단정하지 않는다(env·git 상태·DB·fixture 생애주기도 입력이다). 입력 변화, 직전 실행 미완료(slot exit 75·
  collection 실패·중단), 재현성·flaky 확인, 계약상 독립 검증(closure 의 self-run)처럼 새 실행의 이유가
  있으면 다시 돌리고, 불명확하면 실제 검증을 수행한다. (실측: 캠페인 43 run 에서 동일 pytest 명령 재발사
  522/3,737 — 불필요분은 미확정이라 규율은 목적·완료 기준이지 문자열 기준이 아니다.)
- 구 code-map 저장층 의무(annotation·Tier·classification impact check)는 ADR-459 로
  은퇴 — 따르지 않는다. `# Owner:/# Lifecycle:/# Tags:` 기계 포맷 annotation 을 새로
  달지 않으며, 남아있는 annotation 은 fact 가 아니라 sweep 대기 historical 텍스트다.
- 부피 큰 scratch(격리 repo 사본·캠페인 산출물·≳100MB)는 `$AGENT_SCRATCH_DIR`(기본 `/var/tmp/agent-scratch`)에 둔다. `/tmp` 는 lock·pid·socket·marker 소형 조율 파일 전용. 수위 청소에서 보존할 scratch 는 그 폴더 안에 `.keep-pin` 파일을 둔다 (ADR-678).
- 골든 재녹화·승격은 `python -m simulation.acceptance.rerecord` 원커맨드 경유만 — 골든 `recordings.json` 을 shell·`apply_patch`·손 CAS 로 직접 쓰거나 갈아끼우지 않는다. 정식 경로만이 잠금(`update_golden`) 검사·검증·provenance 기록을 지난다.

- **사실 판정의 주인** (사용자 채택 2026-09-06): 새 술어·정규화·정체 판정(`ok/status/error/kind` 류 어휘로 문장·상태·분기를
  짓는 코드)을 쓰기 전 그 사실의 주인(대개 `air/contracts/`)을 찾아 minted 필드를 승계한다. 주인이 없으면 blocker 가 아니다 —
  주인 후보(어느 contracts 모듈, 어떤 키를 판정에 읽나)와 기존 재판정 자리 sweep 결과(`rg` 명령 + 좌표)를 보고에 싣고, 세우는
  판단은 발주자 몫. 규범 = `@CLAUDE.md` §구조·리팩터 불변식 "사실 판정의 주인", 질문 본문 = `/simplify` §관찰 포인트 "혹시?".

## 장시간 turn 상태 외부화 (캠페인급 turn, ADR-600)

긴 일을 받으면 **"정리하면서 간다"가 기본 자세다** — 네 context 는 내부 compact
요약과 wrapper 시간 상한 절단으로 언제든 잘릴 수 있고, 그때 남는 것은 디스크뿐이다
(실증 2026-07-22: 3h 절단 turn — 디스크에 쓴 것은 전부 회수됐고, context 에만 쥔
계획 상태만 유실됐다).

- 보고에 들어갈 사실(판정 적용 결과·검증 수치·인벤토리·증거 좌표)은 얻은 자리에서
  바로 파일로. context 는 사본이고 디스크가 원본이다.
- **호출 수 규율 — 비용은 호출 수 × 문맥이고, 문맥 크기는 네가 줄일 수 없다** (실측 2026-09-08,
  `docs/report/codex-run-failure-resume-cache-2026-09-08/context-composition.md`): codex 는 창의 90%(약 23만)에서
  자동 압축해 3~4만으로 내리므로 스텝당 문맥은 그 톱니의 중간값(13만대)으로 수렴한다 — 내용을 줄여도 평균은 안
  내려간다. 사장 호출의 24~41% 가 "직원 아직이야?" 폴링이었고(`wait_agent` 60초·30초 반복, `list_agents`), 11~15% 가
  같은 파일 재읽기였다(자기 `state.md` 25회+). 그래서:
  ① `wait_agent` 는 **30분 단위**(`timeout_ms: 1800000` — `@AGENTS.md` §Subagent 대기 규율, 사용자 결정 2026-09-15: sol
  캐시가 35~40분부터 죽기 시작해 60분은 쓰지 않는다; hook 하한 10분)으로 부르고 20~60초 폴링을 하지 않는다
  — 한 번의 폴링 = 13만 토큰 호출 1회. 이 도구는 대상 지정 없이 **어느 자식이든** mailbox 갱신이 오면 즉시 깬다(wait-any)
  — 긴 timeout 이 형제 자식을 방치시키지 않는다. 기다리는 동안 할 일이 없으면 더 길게 기다린다.
  ② 같은 사이클에 읽은 파일을 다시 열지 않는다 — 판정에 쓸 좌표·값은 `state.md` 좌표 메모로 남기고, 다시 볼 땐 바뀐
  구간만 읽는다(압축 뒤 "날아갔으니 다시 읽기"가 재읽기의 15~29%).
  ③ 직원 산출은 파일로 받고 반환 메시지는 3줄(Status·파일 경로·Open Meaning 유무) — 끝난 직원의 보고 전문은 이후
  모든 `wait_agent`/`list_agents` 반환에 통째로 재첨부된다. toml 반환 모양(`Requirements:`·`Completion Evidence:` 등)은
  그 **파일** 에 산다 — "N줄만 반환" 지시는 메시지 길이지 모양 덮어쓰기가 아니다 (실측 2026-09-09: 모양을 덮은 packet 의
  Luna 반환은 `Requirements:` 0/19, 안 덮은 캠페인은 22/27 — ADR-872 추기 (7)).
  판독 = `codex_usage.py --by run` 의 `steps`·`wa_short_share`·run.4.
- 계획 상태는 output 디렉토리(packet 미지정이면 자기 output 파일 옆 `<slug>/`)의
  `state.md` **하나**로: 완료 / 진행중 / 남은 것 / blocker / 수령 룰링 요지(원문은
  packet) / 다음 한 단계. 좌표와 판정만 — 산문 일지 금지, 원본 로그·diff 는 별도
  raw 파일. 룰링 수령·increment green·긴 작업 착수 직전 같은 의미 있는 경계마다
  원자적으로(tmp 작성 후 mv) 갱신한다. 작은 사장 turn 이면 orchestrator 만 쓴다.
- resume 재개 첫 행동 = `state.md`·산출물·git 현 상태 재관찰. 신뢰 서열: 최신
  packet 룰링 → owning contract/ADR → 디스크 실물 → `state.md` → 자기 기억.

소형 one-shot 은 대상이 아니다. (경계·필드 세부와 대안 =
`@docs/adr/600-long-turn-worker-state-externalization.md` D5; goal-mode 판 =
`docs/goal_packets/CLAUDE.md`.)

## 보고

작업별 prompt 의 보고 양식을 따른다. 별도 양식이 없으면 다음을 포함한다.

- Status: completed | blocked | failed
- 변경 파일 또는 읽은 주요 좌표
- 실행한 검증과 결과
- 남은 risk 또는 사용자 결정이 필요한 사항

## 사용 양식

각 codex prompt 첫 줄에 공통 헤더 문구를 넣고, 이후 작업별 내용을 작성한다.

```text
@.claude/skills/codex-bg/codex-prompt-boilerplate.md 본문 절대 준수. 본 prompt 의 영역별 내용은 다음과 같다:
```
