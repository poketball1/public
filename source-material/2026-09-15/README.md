# 원문 스냅샷 — 2026-09-15

- 스냅샷 날짜: **2026-09-15** (Asia/Seoul)
- AIR repo commit: **`84e63c231`**
- 여기 파일은 AIR 저장소 원문 그대로다. 발췌로 표시된 셋(CLAUDE.md · AGENTS.md · luna-observation-log.md)과
  `claude-settings-excerpt.json` 만 범위를 잘랐고, 그 밖은 byte 동일 사본이다.
- 해설은 [`../../delegation-stack.md`](../../delegation-stack.md) 에 있다. 같은 원문이 그 글 §9 에도 접힌 블록으로 들어 있다.

| 파일 | 무엇인가 | AIR repo 원본 경로 |
|---|---|---|
| `claude-rules-delegation.md` | 위임 운영 규칙의 SoT — 좌석 지도·판별선·작은 사장 계약·사장 운영 감각 | `.claude/rules/delegation.md` |
| `claude-rules-polar-star.md` | 북극성 지침 — 착수 전 강제 확인과 fresh-0 완료 판정 | `.claude/rules/polar-star.md` |
| `CLAUDE.md-delegation-sections.md` | main 좌석 정책·Fable 자유도·사장모드 극성·보고 규범 (4개 절 발췌) | `CLAUDE.md` |
| `AGENTS.md-tool-and-delegation.md` | 같은 규칙의 Codex-audience twin — 직원 원칙·Luna/Sol 배분 (1개 절 발췌) | `AGENTS.md` |
| `claude-agents/closure.md` | 마감 파생 표면 감리자 정의 (Opus pin) | `.claude/agents/closure.md` |
| `claude-agents/front-closure.md` | FE 실화면 마감 감리자 정의 (Opus pin) | `.claude/agents/front-closure.md` |
| `claude-agents/journey-round-boss.md` | Claude 쪽 유일한 예외 사장 — 여정 관찰 회차 소유 | `.claude/agents/journey-round-boss.md` |
| `codex-agents/README.md` | codex roster 역할 목록과 호출 brief | `.codex/agents/README.md` |
| `codex-agents/luna-worker.toml` | 말단 직원 Luna — 스폰 도구 없는 leaf | `.codex/agents/luna-worker.toml` |
| `codex-agents/falsifier.toml` | 반증 역할 (Sol pin) — frame check round 0 | `.codex/agents/falsifier.toml` |
| `codex-agents/closure.toml` | codex-main lane 의 마감 감리 역할 | `.codex/agents/closure.toml` |
| `codex-agents/air-analyst.toml` | prompt·응답·흐름 live 분석 역할 | `.codex/agents/air-analyst.toml` |
| `codex-agents/learning-distiller.toml` | 라운드 마감 뒤 규칙 증류 역할 | `.codex/agents/learning-distiller.toml` |
| `codex-agents/open-cognition-partner.toml` | 설계 동업 역할 (Claude main 은 기용 안 함) | `.codex/agents/open-cognition-partner.toml` |
| `codex-config.toml` | codex 런타임 기본값 — 직원 기본 Luna/max, 동시 스레드 상한 | `.codex/config.toml` |
| `claude-settings-excerpt.json` | subagent 기본 모델 강제 + fork 스폰 차단 (발췌) | `.claude/settings.json` |
| `skills-codex-bg/SKILL.md` | codex 호출 단일 진입점 — 제출·완료 wake·Run 양식 | `.claude/skills/codex-bg/SKILL.md` |
| `skills-codex-bg/codex-prompt-boilerplate.md` | 모든 codex packet 첫 줄이 참조하는 worker 공통 규율 | `.claude/skills/codex-bg/codex-prompt-boilerplate.md` |
| `skills-boss-mode-SKILL.md` | 사장모드 stub (본문은 delegation.md 로 흡수) | `.claude/skills/boss-mode/SKILL.md` |
| `adr-872-fable-grade-deputy-judgment-envelope.md` | 작은 사장 재량 envelope·STOP 4종·Luna 운영 결정문 | `docs/adr/872-fable-grade-deputy-judgment-envelope-astra-vp.md` |
| `docs-ops-token-dial-ledger.md` | 위임 dial 변경의 시간순 원장 | `docs/ops/token-dial-ledger.md` |
| `docs-ops-luna-observation-log-header.md` | Luna 고용 관찰 문서함의 규칙부 (헤더 발췌, 관찰 행 제외) | `docs/ops/luna-observation-log.md` |

> 참고: `.codex/agents/` 의 은퇴 alias toml 7개(agent-flow-observer · agent-response-analyst · evidence-scout ·
> implementation-mechanic · prompt-input-analyst · vp-router · workflow-rationalist)는 현행 좌석이 아니라 제외했다.
