# Luna 고용 관찰 문서함

> **이 문서를 여는 사람 = 사용자(비정기)와, 사용자가 그때 판정을 시키는 세션.** Luna 를 직접 고용한 자리(codex 작은
> 사장·Sol 직원)가 **잘 안 된 고용만** 표 한 행으로 직접 append 한다 — main 보고 왕복 없음 (사용자 결정 2026-09-08,
> idea 179 U1 착지 = `@docs/adr/872-fable-grade-deputy-judgment-envelope-astra-vp.md` 추기 2026-09-08 (5); 등기 =
> `@docs/architecture/state-concurrency-classes.md` 행 142).
> 판정의 산출 = `@AGENTS.md` §Worker Principles 의 Sol 예외 문장 개정(관측된 **판정 조건**을 더하거나, 구체 피드백
> 뒤 Luna 가 처리한 조건을 뺀다) — 여기서 결정하지 않고, 업무 종류(테스트·문서·다파일)로 적지 않는다.
>
> - 쓰는 규칙: 한 고용 = 한 행. `printf '%s\n' '| … |' >> docs/ops/luna-observation-log.md` 로 **단일 행 append 만**
>   (편집·정렬·삭제 금지 — 여러 세션이 동시에 쓴다). **관찰 표가 이 파일의 마지막 절**이라 EOF append 가 곧 표의 다음
>   행이다 — 표 뒤에 절을 만들지 않는다. 잘 된 고용은 쓰지 않는다
>   (분모 = `python scripts/codex-mcp-server/codex_usage.py --by parent-model --by role`).
- **잘 안 된 고용 = Luna 조각이 완료 기준을 한 번에 못 넘긴 것** — falsifier ① 이 난 초안, 부모가 다시 한 조각, 미집행·오분류
  회수, Sol 회수. **같은 Luna 가 고쳐서 채택됐어도 한 행이다** (성공 = 첫 반환이 그대로 채택된 고용). 사장 보고의 `Luna 관찰` 절은
  이 행을 대체하지 않는다 (판독 2026-09-10: 있어야 할 행 28 중 실재 1 — 두 오독 = "고쳐 채택 = 성공" · "예외 조건 제안할 때만").
> - 원인 어휘(한 단어): `능력` / `판단 구멍`(packet 이 정하지 않은 해석을 스스로 채움) / `미집행`(명시 요구를 빼고
>   완료 보고) / `packet`(완료 증거·경계·성공 판정점 미명시 — 고용자 쪽 결함) / `조율`(재개·메시지·wrapper 우회 등
>   고용자 쪽 운용).
> - 처분 어휘: `같은 Luna 수리` / `Sol 회수` / `부모 직접` — 뒤에 괄호 한 줄 보충 가능. Sol 회수는 "왜 Luna 로 안 되는가"
>   를 그 괄호에 적는다.
> - 보존 규칙 (ADR-667 D6): 판독 전 행은 상한 없음. 판독 세션이 읽은 행까지를 `## 판독` 한 줄로 접은 뒤, 접힌 행이
>   100행을 넘으면 그 판독 세션이 표에서 잘라 `docs_archive/ops/luna-observation-log-<판독일>.md` 로 옮긴다
>   (쓰는 쪽의 편집 금지는 그대로 — 자르기는 판독 세션만).
> - 종결: 없음(의도적 무종결).

## 판독

사용자가 열어 판정시킨 세션이 `날짜 · 읽은 마지막 행 · Sol 예외 문장 변경 여부(무엇을 더하고 뺐나)` 를 한 줄 남긴다.
이 절은 표 **위**에 있다 — 표는 append 가 닿아야 하므로 마지막 절이다.

- 2026-09-09 (Fable main, 사용자 발주 idea 179 후속) · 읽은 마지막 행 = 15행(ADR-887 stage2 turn8 / R21) · **Sol 예외 문장
  변경 없음** — 15행 중 원인 `능력` 0, 착지 후 9행 처분 = 부모 직접 5·같은 Luna 수리 4·Sol 회수 0; 착지 후 창(09-08 23:31→
  09-09 07:50) Luna 스레드 180 전부 luna/max, 비-판정 Sol 스폰 0. 발견은 Luna 가 아니라 **기록 경로 둘**: ① 문서함 append 를
  main 저작 packet 2건이 "peer dirty file" 로 금지 → 착지 후 root 12 중 append 3, 보고서엔 마찰이 있는데 행 없는 root 6/11
  (수리 = delegation.md §좋은 위임 prompt·boilerplate 에 상시 append 허가 명문화) ② `Requirements:` 반환이 packet 의 "N줄만
  반환" 지시에 덮여 새 toml 자식 65/160 에만 실림 (수리 = toml·boilerplate ③: 모양은 산출 파일에, 메시지는 3줄 포인터).
  표본 얇음(fresh root 2~3, 나머지 착지 전 root 의 resume). 원자료 = `docs/report/luna-post-idea179-readout-2026-09-09/friction-census.md`,
  결정 = ADR-872 추기 2026-09-09 (7).
- 2026-09-10 (Fable main, 사용자 발주 "luna 사용 이력 남은 거 꼼꼼히") · 읽은 마지막 행 = 16행(ADR-899 GAG4 / G2) · **Sol 예외 문장
  변경 없음** — 창(09-09 07:50→09-10 15:20) 문서함 신규 1행, 그러나 사장 8명의 보고·state 로 재유도한 "있어야 할 행" 은 조각 28 / 고용
  21(원인 미집행 11·판단 구멍 14·packet 2·조율 1·`능력` 0; 처분 같은 Luna 수리 16·부모 직접 8·Sol 회수 2·부모 STOP 2) — 기록 1/28.
  미기입 뿌리 = ① "잘 안 된 고용" 단위 미정의(approval-truth 가 8 turn 연속 "고쳐 채택 = 성공"·"예외 조건 신설 시에만" 으로 읽음, 5 root
  는 boilerplate 로 의무를 받고도 고려 0) ② main packet 13개가 은퇴한 `### Luna 관찰` 절을 보고 양식에 열거해 문서함 자리를 차지 ③
  AGENTS.md 가 09-09 18:10(ADR-900 D7 `project_doc_max_bytes`) 전까지 32 KiB 에서 잘려 §Worker Principles 뒤쪽(black·문서함)이 codex
  에 닿지 않음(boilerplate 로는 닿음; 첫 판독 창의 root 도 전부 잘린 판). 수리 = 위 헤더의 단위 정의 + delegation.md §Luna 조각
  packet 두 문장(`Luna 관찰` 절 열거 금지 · 감리 라운드를 Luna 에 캐스팅 금지 — 실측 bp192-s4 5·s4docs 2 라운드가 Luna 로 돌아
  fresh-0 근거가 됨). 비-pin Sol 자식 2(둘 다 approval-truth: (b) 한 단어 명시 1 · air_analyst 를 STOP 후보 판정석으로 쓴 산문 1,
  `Sol 회수` 행 0). toml 반환 수리 효과 = 3줄 포인터 271/312, `Requirements:` 산출 파일 275/312(수리 전 65/160). 원자료 =
  `docs/report/luna-post-idea179-readout-2026-09-09/{deputy-log-compliance,return-shape-census}-2026-09-10.md`, 결정 = ADR-872 추기 (9).

## 관찰 (append only — 파일의 마지막 절)

| 날짜 | 고용자 (캠페인/역할) | 조각 한 줄 | 조건 → 실패 형태 | 원인 | 처분 |
|---|---|---|---|---|---|
