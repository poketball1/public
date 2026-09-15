---
name: codex-bg
description: "Claude main agent 가 codex 를 호출하는 단일 진입점. `run … --no-wait` 를 foreground 로 제출하고 완료 wake 1회(runner D3 배달)로 받는다 — 파수꾼 없음(ADR-619 D6). bridge(`--print`) 세션 회수 = 단발 ScheduleWakeup + status. status/tail/changes/cancel control surface 를 제공한다."
argument-hint: "run|resume|health|status|tail|changes|cancel [--prompt-file file|--prompt text] [--output file] [--no-wait] [--reasoning max|xhigh|high|medium|low] [--sandbox danger-full-access|workspace-write|read-only] [--mode write|review|audit] [--model gpt-5.6-sol] [--approval never|on-request|on-failure|untrusted] [--network|--no-network] [--ephemeral] [--thread-id id] [--timeout-ms ms]"
allowed-tools: Bash, Read, Write, TaskCreate, TaskUpdate
---

# /codex-bg

<!-- bash-skill-marker: # /codex-bg -->

`/codex-bg` 는 Claude main agent 가 codex 를 호출하는 유일한 진입점이다.
wrapper 는 `/config/work/scripts/codex-mcp-server/codex-bg.sh` 이다. **interactive
세션은 `run … --no-wait` 를 foreground Bash 로 제출하고 turn 을 끝낸다** — 완료는
`[codex-bg 완료 HH:MM]` wake 1회로 온다 (ADR-619 추기 2026-09-08 · 09-09 파수꾼 은퇴). 제출 뒤 main 터미널에
오는 신호와 그 처분은 아래 §신호 교통표 한 곳이 소유하고, "알림 인프라 wake 1회 · 이중 장치
0 · Monitor 금지(codex-bg 처럼 이중 장치인 자리는 예외 없음)" 원칙은 `@.claude/rules/behavior.md` §Monitor And Polling 이 소유한다
— 이 파일은 그 원칙을 재서술하지 않는다.

이 completion wake 는 background job 을 시작한 **harness-tracked launcher(=
top-level main 세션)에만** 붙는다. Claude/Opus background sub-agent 가 `/codex-bg`
를 실행하고 자기 turn 을 대기로 끝내면 완료 시 **자동 wake 되지 않는다**(조용한
stall — 실측 2026-07-05). 다단 위임은 codex 작은 사장이 자기 codex sub-agent 로
한 turn 안에서 지휘한다 (작은 사장 carrier = codex 단일 — 2026-09-02 이원화 철회,
`@.claude/rules/delegation.md` §작은 사장) — SoT = 같은 파일 §Tool And Delegation.

깊은 운영/장애 대응은 @docs/architecture/infra/codex-infra-ops.md 를 본다.
구현 SoT 는 @docs/architecture/infra/codex-bg.md 이다.

## 신호 교통표 — 제출 뒤 main 에 오는 것과 처분

한 run 이 main 터미널에 만들 수 있는 신호는 아래가 전부다. 처분 열 밖의 행동(Monitor·폴링
Bash·`status` 반복)은 이중 장치다. 상세는 각 절이, 원칙은 behavior.md §Monitor And Polling 이 소유한다.

| 신호 (터미널 모양) | 발신 | 뜻 | 처분 |
|---|---|---|---|
| `[codex-bg 완료 HH:MM] <invocation> <status> — <결과 경로>` | runner completion-wake (D3 배달, ADR-619) | run 종료 — `<status>` 가 completed/failed/cancelled 를 말한다 | 결과 JSON 을 읽고 검수. failed 면 같은 thread `resume` 을 자동 재시도 포함 최대 2회 (§Run / Resume mechanics). |
| `[codex-bg keep-warm HH:MM]` (`#seq`·` - retry` 접미 가능) | runner keep-warm — main 52분+ idle (ADR-595·604) | 캐시 warm 유지용 자동 turn. 오류·개입 요청 아님 | **무행동** — 한 줄 확인 후 turn 종료 (§Keep-warm). |
| `[codex-bg idle-warn HH:MM]` | runner — run 60분 무활동 (ADR-898) | 경고. runner 는 취소하지 않는다 | `status` 1회(quiet_min·last_activity_at), 필요시 `tail`. 취소는 증거 있을 때만 (§Idle-warn). |
| `[HH:MM] Codex Limit <세션 제목>` 노란 팝업 | wrapper — `error_class=usage_limit` (ADR-895) | 한도 도달로 run 실패 | 재개 여부는 같은 thread `resume` 1분 간격 2~3회로만 확인 (§사용량 판독). |
| `codex 주간 NN% 남음, …` 알림 | statusline usage-pace hook (wrapper 무관) | 잔량 속도 정보 | 정보 — 행동 없음. |
| `[keep-warm HH:MM] <arm>#<seq> …` | `/keepwarm` skill 의 세션 arm (codex-bg 무관) | 세션 warm 유지 자동 turn | 무행동 (양식 = keepwarm SKILL). |
| harness "background Bash 종료/killed" 통지 | 구 형태(`run_in_background=true`)로 띄운 과도기 run | 호출 Bash 만 끝났다 — runner 는 unit 에서 계속 돈다 (파수꾼은 ADR-619 D6 로 은퇴) | **아무것도 붙이지 않는다.** 완료는 첫 행으로 온다. |
| 단발 ScheduleWakeup 도착 | bridge(`--print`) 세션이 launch 때 스스로 예약 | D3 가 닿지 않는 세션(`undeliverable` 행만 남음)의 회수 지점 | `status` 1회. interactive 세션은 이 예약을 만들지 않는다. |

wake 유실 의심(첫 행이 안 옴) = 다음 자연 wake(사용자 메시지·직원 task-notification·keep-warm
turn)에서 `status` 1회 + `logs/delivery.jsonl` 의 `codex-bg-complete` 행 대조. 확인하려고 새 wake 를
만들지 않는다.

## Keep-warm 자동 신호

장시간 run 대기 중 main 세션이 52분+ idle 이면 bg-runner 가 wake-request relay 로
`[codex-bg keep-warm HH:MM]` 한 줄 메시지를 main 터미널에 자동 주입한다 — 프롬프트
캐시(1h 슬라이딩 TTL)가 식기 전에 짧은 turn 을 한 번 돌려 warm 을 유지하는 자동
신호다 (ADR-595).

- 이 메시지를 받으면 **새 작업을 시작하지 않는다**. 한 줄 확인만 하고 turn 을
  끝낸다. 오류·개입 요청이 아니다 — `status` 조회는 이 신호의 몫이 아니라 idle-warn 의
  몫이다 (behavior.md §Monitor And Polling "keep-warm 은 무행동").
- 신호 부재 ≠ 문제: kill switch(`CODEX_BG_KEEPWARM=0`)·watcher 부재 시 신호가
  없고, 완료 wake 는 그와 무관하게 동작한다.
- 메시지의 `#{seq}` 접미와 ` - retry` 접미는 전달 확인·재시도 표식이다 (ADR-604). 병합 도착(원본+retry 가 한 줄)도 같은 자동 신호 1건으로 취급한다 — 한 줄 확인만 하고 대기를 계속한다.
- 발행·제출확인·재시도·실패는 `logs/delivery.jsonl`(전달 원장, sender 공통)로,
  armed/종료/cache 역채록은 `logs/keepwarm.jsonl`(도메인 원장)로 관측한다
  (ADR-604 D7 + ADR-605 D3 분층).
- 새 run에 적용될 설정은 `codex-bg.sh health | jq .keepwarm`으로 확인한다.
  특정 run의 실제 상태는 `codex-bg.sh tail --invocation-id <id> | jq
  .lifecycle_tail`로 확인한다. `keepwarm_armed`는 타이머 장착,
  `keepwarm_disabled`는 kill switch/세션 ID 부재, `keepwarm_unavailable`·
  `keepwarm_emit_failed`는 운영 실패, `keepwarm_emit`은 wake-request 발행이다.
  `tail`의 lifecycle 행은 요청한 invocation만 포함한다.

## Idle-warn 자동 신호

run 이 **60분간 아무 활동도 없으면** bg-runner 가 같은 wake-request relay 로
`[codex-bg idle-warn HH:MM]` 한 줄을 main 터미널에 보낸다 (ADR-898). 활동 = codex
child 의 `--json` 이벤트 또는 그 run 의 rollout JSONL 증가 — 둘 중 하나만 있어도
활동이다. keep-warm 틱은 활동으로 치지 않는다 (wrapper 자기 타이머라, 그걸 활동으로
세면 감시가 무의미해진다). **사장이 자식을 기다리며 도는 `wait` 폴링 이벤트도 활동이 아니다** —
그 폴링은 이벤트를 계속 내서 시계를 붙잡았고(bp192 ④-docs hang 72~90분 무경고, 2026-09-09) 자식이 실제로
일하면 자식 rollout 증가가 활동으로 잡힌다 (ADR-898 추기 2026-09-10 D5).

경고에 실리는 자식(sub-agent) 활동 표시는 세션 파일에서 읽은 사실만 담고 상태를 추론하지
않는다 — 판독 창·필터 정의는 구현 SoT `@docs/architecture/infra/codex-bg.md` §7 "Mid-run
liveness warning" 이 소유한다 (이 파일에 복제하지 않는다).

- **경고일 뿐 조치가 아니다. runner 는 절대 취소하지 않는다** — run 은 그대로 계속된다.
- 받으면 `status`(quiet_min·last_activity_at) 와 필요시 `tail` 로 확인한다.
  **취소는 증거가 있을 때만** — 과거 age 기반 `suspected_hung` 오판으로 살아있는 run 을
  되돌릴 수 없게 취소한 사고가 3건 있었다.
- 60분은 실측 기준이다: 2026-09-07 rollout 66 run 에서 **하위 agent 가 도는 동안** 부모
  쪽 무이벤트 최장 구간이 9.42분(p90 4.55분)이었다 — 30분 넘는 구간은 run 사이(재개 간격)
  에만 있었다. 즉 하위 agent 대기는 이 경고를 발화시키지 않는다.
- `status` 의 `suspected_hung` 도 나이가 아니라 **같은 quiet 임계**로 판정한다
  (`quiet_ms`·`quiet_min`·`last_activity_at`·`idle_warn_ms` 필드 동봉).
- 신호 부재 ≠ 정상: kill switch(`CODEX_BG_IDLE_WARN=0`)·비-interactive 호출 세션(bridge)
  에서는 전달되지 않고 `idle_warn_undeliverable` lifecycle 행만 남는다.
- 새 run 에 적용될 설정은 `codex-bg.sh health | jq .idle_warn`, 특정 run 의 실제 상태는
  `codex-bg.sh tail --invocation-id <id> | jq .lifecycle_tail` 의 `idle_warn_armed` ·
  `idle_warn` · `idle_warn_disabled` 행으로 본다.

## 완료 wake 경로

- **모든 세션 공통**: wrapper 는 unit 을 제출하고 즉시 반환한다 — 파수꾼(폴링 Bash)은 없다
  (ADR-619 D6, 2026-09-09; `--no-wait` 는 호환용 no-op). runner 가 run_end 에 완료 메시지를
  session-delivery client 로 배달한다 (D3) — caller 세션이 live interactive 면 정확히 1회.
- **bridge(`--print`)·죽은 세션**: 터미널이 없어 D3 가 닿지 않는다 — runner 는 `undeliverable`
  사유 행만 남긴다. bridge 세션은 launch 시점에 **예상 완료 시각 1회분 단발 ScheduleWakeup** 을
  예약해 `status` 1회로 회수한다. 구 10~12분 폴링 체인은 불필요 — runner 는 별도 unit 에서
  생존한다.
- 구 형태(`run_in_background=true`)로 띄운 과도기 run: 호출 Bash 가 즉시 끝나 harness 가 "완료"
  통지를 한 번 낼 수 있다 — 결과는 D3 로 온다, 아무것도 붙이지 않는다.
- **cancel 한 run** 도 wake 를 1회 보낸다 — unit stop 유예(30s) 안에 짧은 확인만 하고, 미확인이면 lifecycle 에
  `unconfirmed_cancelled` 로 남긴다(ADR-604 추기 2026-09-10). 바쁜 세션에 넣은 알림은 큐 착지를 발견한 poll 에서 바로
  확인된다(D10) — 10분 창은 상한이지 대기 시간이 아니다.
- 설계 = @docs/adr/619-codex-bg-detached-runner-thin-waiter.md (D3 · 추기 2026-09-08 `--no-wait` ·
  추기 2026-09-09 D6~D8 파수꾼 은퇴·관측 수리), docs/big_plan/137-session-delivery-notify-infra.md P13.

## Runner 격리 (transient service) 와 cancel

codex-bg runner 는 호출 세션의 Bash 와 분리되어 생존한다 (ADR-619 → spawn 층 ADR-666
개정). `codex-bg.sh` 는 runner 를 `systemd-run --user` **transient service**
(`codex-bg-<invocation>.service`) 로 제출한다 — runner 의 ppid 는 user systemd manager 이고
cgroup 은 자기 unit 이라 호출 세션의 프로세스 트리·`agent-claude-*.scope` 양쪽에서 빠진다.
호출 세션이 어떻게 끝나든(`--print` 의 input-close 유예·세션 종료·idle reaper) runner 는 계속
돌아 정상 완료한다 (구 `setsid` 층은 session/pgroup 만 바꿔 이 두 문을 못 막았다 — 실측 =
docs/report/codex-runner-kill-census-2026-07-29.md, 포렌식 =
docs/research/283-claude-bg-sigterm-root-cause.md).

`cancel` 은 CLI 표면 그대로이며(`codex-bg.sh cancel --invocation-id <id>`) 내부
정본이 `systemctl --user stop <unit>` 이다. 취소 직전 lifecycle 원장에
`cancel_requested` 행이 찍히고 runner 의 `sigterm_forensics` 행이 그걸 되읽으므로,
**의도된 취소와 동거 사상자가 원장에서 구분된다** (`cancel_requested_seen`). 설계 =
@docs/adr/666-codex-bg-service-mode-runner-isolation.md.

그 구분은 종료 판정까지 간다 — `cancel_requested` 행이 있으면
`status: cancelled` + `error_class: cancelled`, 없으면(재부팅·`systemctl --user stop`
같은 외부 정지) `status: failed` + `error_class: killed_external` + `next_step`(같은
thread resume) 이다. 즉 **`cancelled` 는 누가 요청한 죽음만**이고, 밖에서 죽은 run 은
실패로 읽힌다 (ADR-895 추기 2026-09-09; census 의 "cancelled by a caller" 도 같은 선).

## Codex Turn Mental Model

codex turn 은 atomic 하다. prompt 하나를 받으면 turn 이 끝날 때까지 codex 가
자율 실행하며, turn 내부 reasoning/tool-use 사이에 외부 지시를 끼워넣는 통로는
없다. `/codex-bg` 는 mid-flight nudge 를 제공하지 않는다.

"추론 사이" 는 주체를 구분한다.

- Claude main agent 의 추론 boundary: codex 완료 결과를 완료 wake(§완료 wake 경로)로 받는다.
- codex turn 내부 step 사이: Claude 가 추가 입력을 보낼 수 없다.

방향을 바꿔야 하면 `status`/`tail` 로 관찰한 뒤 `cancel` 하고, 마지막 result /
rollout 내용을 새 prompt 에 요약해 `resume` 으로 다음 turn 을 시작한다.

## Control Surface

| subcommand | 용도 |
|---|---|
| `run` | 새 codex turn 시작. 첫 인자가 없거나 `--`로 시작하면 `run` 으로 간주한다. |
| `resume` | 기존 `thread_id` 에 다음 turn 추가. `resume <thread_id> ...` 또는 `run --thread-id <id> ...`. |
| `health` | codex binary, login, env 기본 진단 + 새 run 의 keep-warm·idle-warn 유효 설정. |
| `status` | invocation/run/thread/output(basename 가능) 선택자 기준 starting/running/done/fatal/lost/suspected_hung 판정 — `starting` = thread·child row 가 아직 없고 pid 생존·age < idle-warn 창(`latest_activity_reason:"pre_index"`, ADR-619 D10 ①); `lost` 는 이 판정 자리에서 lifecycle `run_lost` + registry `end lost` 를 1회 기록(D8 ②); cancel 뒤에도 `thread_id` 는 child row 에서 승계된다(D10 ②) + 종료 run 의 `error_class`. cancel 요청 없이 SIGTERM 으로 죽은 run 은 `failed`/`killed_external` 로 나온다 (§Runner 격리). `suspected_hung` = 나이가 아니라 **quiet ≥ idle-warn 임계**(ADR-898). 선택자 없이 부르면 자기 세션 최신 in-flight run 을 자동 해석(`auto_selected` 표시, 모호 시 형제 목록 동봉)하고, 미해석 시 오류 대신 `status:"unresolved"` + 후보 목록을 준다. `children`과 `children_human`은 파일에서 읽은 자식 활동 사실이며 상태를 추론하지 않는다. |
| `tail` | result/rollout 최근 이벤트와 해당 invocation의 lifecycle 이벤트 확인. resolved `children_tail`은 파일 사실 배열, unresolved는 `children:{resolved:false,reason,children:null,summary:null}`·`children_tail:null`·`children_human` 미해석 문장이다. |
| `changes` | 이번 codex turn 의 `apply_patch` 확정 파일과 shell/git suspect command 확인. 사장 run 은 자식(sub-agent) rollout 의 `apply_patch` 도 `definite_files` 에 `source:"child:<id>"` 로 합산하고 `child_rollouts_scanned` 를 같이 낸다(ADR-619 D10 ③, 2026-09-10) — 부모 우선, `suspect_commands` 는 부모 turn 만. |
| `cancel` | 원장에 `cancel_requested` 를 남긴 뒤 runner unit 을 `systemctl --user stop`. unit 이 이미 없으면 registry pid 검증 후 SIGTERM -> SIGKILL 로 폴백. |

## Run 양식

`--model`/`--reasoning` 을 생략하면 기본값 `gpt-5.6-sol`/`xhigh` 를 사용한다.
이 기본값은 **최상위 run(사장·VP 좌석)** 의 것이다 — 그 밑 직원(sub-agent)의 기본은 `.codex/config.toml` `[agents]` 의
**Luna/max** 다 (2026-09-07; 판정 섞인 조각도 Luna 초안 먼저; Sol 직원 = 판정 역할·Luna 초안 미달 재작업 예외, `@AGENTS.md` §Worker Principles, 2026-09-08). Luna 는
codex-bg 최상위 run 으로 띄우지 않는다: `--model gpt-5.6-luna` 는 wrapper 가 `runner_fatal` 로 거부한다(실측 2026-09-06,
`lib.mjs` 최상위 모델 제한). Luna 는 codex 사장·VP 가 `agent_type="luna_worker"` 로 스폰하는 sub-agent 또는 Sol 직원
경유로만 산다. (wrapper 의 Luna→`max` 정규화는 그 경로가 열릴 때를 위한 것이다.)
**역할별 모델 기본값 (ADR-872, 2026-09-05; deputy 기본 Sol 로 되돌림 2026-09-07 — astra 사장 발주 = `CODEX_MCP_MODEL=gpt-6-astra` 명시)**: `--output` 파일명이 `deputy-*` 면 작은 사장 모델
(`CODEX_MCP_DEPUTY_MODEL`), `vp-*` 면 VP 모델(`CODEX_MCP_VP_MODEL`)이 그 run 의 기본이 된다 — 현재값은
`codex-bg.sh health | jq .role_models`. 호출 env 에 **비어 있지 않은** `CODEX_MCP_MODEL` 을 명시하면 그것이 이긴다(빈 문자열 = 미명시).
`resume` 은 `--output` 과 무관하게 그 thread 가 시작된 모델을 registry 에서 이어받는다. 그 밖의
run 은 base 기본값 그대로. 역할 분류기 = 출력 파일명 (ADR-583 `deputy-*` 관례 재사용; `vp-*` 는 여기서
신설 — VP 발주는 output 을 `vp-*.json` 으로 짓는다).
현재 resolved 기본값은
`/config/work/scripts/codex-mcp-server/codex-bg.sh health # /codex-bg` 로 확인한다.

Bash 로 wrapper 를 호출할 때는 subcommand 와 무관하게 명령 끝에 `# /codex-bg`
marker 를 붙인다.

1. prompt 파일을 작성한다. 첫 줄은 공통 boilerplate 문구를 둔다.

```text
@.claude/skills/codex-bg/codex-prompt-boilerplate.md 본문 절대 준수. 본 prompt 의 영역별 내용은 다음과 같다:
```

2. **foreground Bash** 로 제출한다 — 반환 JSON `status:"submitted"` 의 `invocation_id` 를 적어
   두고 turn 을 끝낸다 (모든 세션 동일; `--no-wait` 는 호환용 no-op 라 붙여도 무해). bridge(`--print`)
   세션은 여기에 단발 ScheduleWakeup 예약을 더한다 (§완료 wake 경로).

새 result 기본 base 는 `${AGENT_SCRATCH_DIR:-/var/tmp/agent-scratch}/codex-results/`
이다. 기존 registry 에 남은 `/tmp/codex-results/...` 경로는 legacy 회수
증거로 계속 유효하며, 이동하거나 삭제하지 않는다.

```text
Bash(
  command="/config/work/scripts/codex-mcp-server/codex-bg.sh run \
    --prompt-file /tmp/codex-prompts/<slug>.txt \
    --output ${AGENT_SCRATCH_DIR:-/var/tmp/agent-scratch}/codex-results/<slug>.json \
    --reasoning xhigh \
    --sandbox danger-full-access \
    [--mode write|review|audit] \
    [--model gpt-5.6-sol] \
    [--approval never] \
    [--network|--no-network] \
    [--ephemeral] \
    [--workdir /config/work]   # trusted project 안이어야 `.codex/config.toml` [agents] 기본값·`.codex/agents` roster·스폰 도구가 붙는다 (격리 worktree = trust 미등록 → roster·spawn 불가, 실측 2026-09-06) \
    [--test-cmd '<verify command>'] \
    [--include-diff] \
    [--timeout-ms <milliseconds>] \
    --no-wait # /codex-bg",
  run_in_background=false,
  description="codex bg: <한 줄 요지>"
)
```

마커 `# /codex-bg` 는 명령 맨 끝, `--no-wait` 는 그 바로 앞이다.

`--timeout-ms` 의 기본·상한 SoT는 `scripts/codex-mcp-server/codex-bg.sh`다. 현재
wrapper 상태는 `codex-bg.sh health`, 정확한 wait 값은 wrapper의 export에서 derive한다.
명시한 값은 해당 호출에 한해 적용되며 wrapper 의 최대값을 넘으면 상한에 맞춘다.
기본·상한은 **6시간**이다 (3h→6h, 사용자 결정 2026-09-08 — 상한에서 잘린 run 은 크레딧이
아니라 최종 보고를 잃는다: 09-08 census 의 timeout 15건이 전부 정확히 180.0분이었고 14/15 는
잘리기 0~7분 전까지 편집 중이었다. ADR-898).
**기본값보다 낮춰 부르지 않는다** — 특히 구현·캠페인 packet 에 1시간 명시는 금지
(사용자 결정 2026-07-17: 1h 지정이 대형 lane 에서 timeout 보고-유실 마찰을 실측으로
만들었다. 짧은 예산이 필요하면 packet 범위를 줄이지 시간을 줄이지 않는다).

3. TaskList 추적 task 를 즉시 만든다. `invocation_id`(반환 JSON), prompt file, output file,
reasoning, sandbox, mode 를 기록하고 검수 완료 전까지 유지한다.

## Run / Resume mechanics

Thread 선택 기준은 `@.claude/rules/delegation.md` §사장 운영 감각 의
`직원을 다시 부를 때 — resume vs fresh` 절이 소유한다. 이 skill 은
명령 사용법만 설명한다.

`run` 은 새 codex turn/thread 를 시작한다. `resume` 은 기존 codex
conversation/session context 에 새 turn 을 추가한다. resume 은 이전 대화 맥락을
이어주지만, 이전 turn 내부의 shell process 나 in-flight command 상태를 보존하지는
않는다. 현재 filesystem/git 상태는 다음 turn 이 다시 관찰해야 한다.

같은 thread 에 in-flight resume 이 있으면 bg-runner 가 새 resume 을 거부한다.

codex resume 의 store 거절(`-32601` + `is not supported yet`)은 wrapper 가
15초 간격으로 같은 명령을 최대 2회 자동 재시도한다. 결과 JSON 의
`resume_store_retries`, `correction: resume_retried_after_-32601` 과
`[resume-retry]` 알림으로 확인한다. 한도를 소진하면
`error_class: resume_store_unavailable` + `next_step` 으로 넘기며 호출자는 추가 재시도하지 않는다.

## Mode 와 Sandbox

`--mode write|review|audit` 는 prompt 양식과 run_id prefix 분류만 바꾼다. sandbox 를
강제하지 않는다. 세 mode 모두 기본값은 `danger-full-access` + approval never다.
review/audit의 no-edit 의미는 prompt가 소유한다. task 자체가 요구할 때만 caller가
`--sandbox`로 해당 호출을 override한다 (ADR-553).

## 사용량 판독

`python scripts/codex-mcp-server/codex_usage.py [--since 2026-09-06] [--json]` 이 codex 소모의
단일 판독 도구다 (기본 창 = 최근 24h, bare 시각은 UTC). rollout + codex-bg registry 를 합쳐
모델·root/child·role×effort·캠페인(deputy/vp) 네 축을 낸다. 각 축은 **토큰과 크레딧을
나란히** 보여 준다 — `tok share` · `cr share` · `cr/1M` 이라 "많이 썼지만 싸다"
가 보인다(by-model 밑에 모델당 한 줄로 요약). 쿼터 pp/시간과 Luna 고용 결과도 함께 낸다. 증분 캐시라 재실행은 수초다 —
census 스크립트를 새로 짓지 않는다.

`--by run` 은 폴링도 같이 낸다 — run 행의 `wa_n`(그 run 이 부른 `wait_agent` 수)·`wa_short`
(300,000ms 미만 = 폴링 비율)·`la_n`(`list_agents`), 그리고 밑에 **run.4** 가 timeout 값별
분포·상습 run(50콜+ & 30%+ 짧음)·규율 착지 이후 시작한 run 의 짧은-대기 비율을 낸다
(호출 수 규율 = `codex-prompt-boilerplate.md` §장시간 turn).

**지금 몇 % 인가** 는 rollout 의 마지막 `token_count.rate_limits.primary` 가 답한다. 창은
payload 가 말해준다 — 이 계정은 `primary` 가 주간(10080분)이고 `secondary` 는 null 이라
"primary=5h" 가정은 틀린다. wrapper 는 이 값을 관측하지 않는다 (ADR-895 D5, 사용자 룰링
2026-09-06 "wrapper 를 왜 만들어? … 사용률 그냥 표시하지마") — 읽기는 statusline tick 쪽
`hooks/lib/usage-pace-notify.sh::usage_pace_notify_codex` 가 bounded tail 로 하고, 5분에
1회만 실제로 읽는다.

**한도 도달은 `error_class="usage_limit"` 로 갈린다** (ADR-895 D4). 그전에는 일반
`codex_failure` 와 구분이 안 됐다. 판정 근거 = 그 run 의 turn 이 남긴 `task_complete` 의
`error.codex_error_info == "usage_limit_exceeded"` (turn 범위로 본다 — rollout 전체
문자열 검색은 같은 파일의 살아남은 형제 turn 을 오분류한다). `usage_limit` 이면 이미 선택된
terminal-turn 실패와 같은 turn의 포화 창에서 만든 `usage_limit_detail`을 wrapper가 전달해
세션 제목을 실은 노란 팝업을 띄운다 (`[HH:MM] Codex Limit <세션 제목>`, 클릭해야 닫힘).
주기적 사용량 관측을 위한 새 polling·reader·cache는 wrapper에 두지 않는다. 5h는 유효한
reset 잔여시간을, 주간은 `주간 한도 도달`만(날짜·reset·기간 없음), 근거 불명은 `한도 도달`을
표시한다. 잔여시간은 1시간 미만 `1시간 미만`, 24시간 이하면 시간만, 초과면 일수만 표시한다.
끄려면 `~/.claude/notify-policy.json` 에 `{"codex_bg_limit": "off"}`.
처분은 종전과 같다 — 재개 여부는 같은 thread resume 재시도로만 확인한다
(1분 간격 2~3회가 판정 단위, `reference_codex_bg_failure_signatures.md` 항목 9).

주간 창의 남은 양이 10% 아래면 pace, 5% 아래면 floor 속도 경고가 뜬다
(`codex 주간 NN% 남음, reset 잔여시간`, 창당 1회). reset 잔여시간도 1시간 미만
`1시간 미만`, 24시간 이하면 시간만, 초과면 일수만 표시한다. 임계·판정·읽기 전부
`~/.claude/hooks/lib/usage-pace-notify.sh` 소유이고 wrapper 는 관여하지 않는다.

## 결과 보고 형식

main agent 가 codex 결과를 사용자에게 보고할 때:

```text
Status: COMPLETED | FAILED | CANCELLED | BLOCKED
Codex: model=<model>, reasoning=<level>, sandbox=<mode>, mode=<write|review|audit>
Invocation: <invocation_id>
Thread: <effective_thread_id>
Turn: <rollout_turn_id>
Resume: /config/work/scripts/codex-mcp-server/codex-bg.sh resume <thread_id> --prompt-file <file> --output <file> ... # /codex-bg
Result: ${AGENT_SCRATCH_DIR:-/var/tmp/agent-scratch}/codex-results/<slug>.json
Rollout: <rollout_jsonl_path or glob>
Changes: /config/work/scripts/codex-mcp-server/codex-bg.sh changes --invocation-id <id> # /codex-bg
Verification:
- command: result
Notes:
- blocker, dirty worktree warning, or suspect shell command note
```

`changes` 의 `definite_files` 는 `apply_patch` 에서 추출한 codex-attributed 파일이다.
shell command 로 바뀐 파일은 확정하지 않고 `suspect_commands` 로만 보고한다.
