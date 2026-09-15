---
name: codex-bg
description: "Claude main에서 Codex CLI에 작업을 위임하고, 실행 기록과 명시적 thread 재개로 결과를 회수한다."
argument-hint: "<task> [read-only|workspace-write] [workdir]"
allowed-tools: Bash, Read, Write, TaskStop
---

# /codex-bg

Claude Code의 top-level main에서 사용한다. 실행 도우미는 이 스킬 디렉터리의
`scripts/run.mjs`다. `${CLAUDE_SKILL_DIR}`는 Claude가 스킬을 읽을 때 실제 경로로 치환한다.
치환을 지원하지 않는 이전 client에서는 설치된 스킬의 절대경로를 사용한다.
Node.js 20 이상과 로그인된 Codex CLI가 필요하다.

## 실행 경계

- main이 목표·수정 범위·검증 기준을 정하고, 변경 검수와 사용자 보고를 맡는다.
- 공개판 sandbox 기본은 `read-only`다. 구현 요청에는 `workspace-write`를 명시한다.
  `danger-full-access`는 그 접근 범위가 허용된 환경에서 명시적으로 선택한다.
  작업 유형과 sandbox는 별개이며, 접근 가능하다는 사실이 수정 권한을 넓히지 않는다.
- 모델은 Codex 설정을 승계한다. 사용자가 모델을 지정했다면 `--model`로 전달한다.
  실행 불가 시 다른 모델로 조용히 바꾸지 않는다.
- 기존 변경은 다른 작업의 산출물일 수 있다. 실행 전후 diff만으로 작성자를 단정하거나
  기존 변경을 되돌리지 않는다.

## 발주와 실행

1. repository 절대경로와 현재 변경 상태를 확인한다. `node "${CLAUDE_SKILL_DIR}/scripts/run.mjs" health`는
   CLI 버전과 로그인 상태를 확인하며 모델 요청을 보내지 않는다.
2. Write로 prompt를 작성한다. 목표·완료 기준, 읽기/쓰기 범위, 금지 범위,
   필요한 검증 명령, 반환 형식, 판단이 불가능할 때 돌아올 조건을 담는다.
   하위 직원을 허용하는 작업은 소유 범위와 위임 깊이도 적는다.
3. 실행마다 **아직 존재하지 않는** 절대경로를 `--run-dir`로 정한다.
   상위 디렉터리는 이미 있어야 한다. prompt는 run directory 밖에 먼저 작성한다.
   도우미가 그 내용을 보존한다.
4. 아래 명령을 Claude Bash의 `run_in_background=true`로 실행한다.

```bash
node "${CLAUDE_SKILL_DIR}/scripts/run.mjs" run \
  --workdir "<ABSOLUTE_PROJECT>" \
  --prompt-file "<ABSOLUTE_PROMPT_FILE>" \
  --run-dir "<NEW_ABSOLUTE_RUN_DIR>" \
  --sandbox read-only
```

도우미 자체는 foreground로 남아 Codex 종료까지 기다린다. Bash가 반환한 task ID와
run directory를 작업 기록에 남긴다. 일반 shell의 `&`나 `nohup`를 추가하지 않는다.
전체 실행 제한은 기본 6시간이며 필요하면 `--timeout-seconds`로 정한다.
출력 파일은 민감한 작업 내용을 포함할 수 있으므로 repository 밖 사용자 전용 경로에 둔다.
민감한 prompt 원본도 같은 기준으로 보관한다. 도우미는 repository 안팎을 판정하거나
비밀을 검사하지 않으며, 저장 위치와 공개 여부는 호출자가 정한다.

## 완료 인지와 결과 검수

Claude Code가 추적하는 background task의 완료 알림으로 결과를 회수한다.
상태 조회는 다음과 같다. 작업 중에는 독립 작업을 진행하거나 harness의 완료를 기다린다.

```bash
node "${CLAUDE_SKILL_DIR}/scripts/run.mjs" status --run-dir "<ABSOLUTE_RUN_DIR>"
```

각 실행은 `status.json`, `prompt.md`, `result.md`, `events.jsonl`, `stderr.log`를 보존한다.
`events.jsonl`은 Codex JSON stdout, `stderr.log`는 진단 출력이다.
`status.json`의 thread ID와 종료 정보, `result.md`의 요구사항별 처분을 함께 읽는다.
`completed`는 Codex turn이 정상 종료됐다는 뜻이며, 요청한 작업의 완료 판정은 main이 한다.
result 파일만 있거나 process exit가 0이라는 이유만으로 완료를 판정하지 않는다.

쓰기 작업은 실제 diff와 필요한 검증 결과를 대조한다. 반환에는 변경 파일,
실행한 검증 명령과 결과, 미해결 요구, 증거 경로를 포함한다.

## 중단과 재개

- 취소는 기록한 Bash task ID의 TaskStop으로 요청한다. 도우미는 종료 신호를 자식에게
  전달하고 기록을 남기지만 강제 종료나 OS 종료에서는 마지막 상태가 남지 않을 수 있다.
- 살아 있는 turn에 prompt 파일을 덮어써도 지시가 바뀌지 않는다. 방향을 바꾸려면
  기존 task가 끝났는지 확인한 뒤 새 실행을 만든다.
- 같은 맥락을 이어갈 때는 `status.json`의 **명시적 thread ID**를 사용한다.
  `--last`는 다른 병렬 작업의 thread를 선택할 수 있어 사용하지 않는다.
- resume는 대화 맥락을 이어간다. 이전 shell process나 당시 worktree를 복원하지 않는다.
  독립 감리와 다른 목적의 작업은 새 thread로 시작한다.

```bash
node "${CLAUDE_SKILL_DIR}/scripts/run.mjs" resume \
  --thread "<THREAD_UUID_FROM_STATUS>" \
  --workdir "<ABSOLUTE_PROJECT>" \
  --prompt-file "<ABSOLUTE_FOLLOWUP_PROMPT>" \
  --run-dir "<ANOTHER_NEW_ABSOLUTE_RUN_DIR>" \
  --sandbox workspace-write
```

로그인·모델·resume 거절의 원문은 실행 기록에 남는다. 원인을 확인한 뒤 같은 thread를
재개하거나 새 작업으로 발주한다. 실패한 실행의 기록은 새 실행으로 덮어쓰지 않는다.

사용자 설정의 영향을 분리하는 진단에는 `--ignore-user-config`가 있다. 인증은 그대로
사용하지만 사용자 config의 모델·MCP 등 설정은 읽지 않으므로, 같은 모델을 비교하려면
`--model`도 명시한다. 평소 실행은 설정을 승계하는 기본값을 사용한다.

## 완료 알림의 한계

이 공개판은 Claude Code의 tracked Bash를 사용한다. Claude가 종료되면 background task도
정리될 수 있으며, 종료된 세션을 다시 깨우거나 재부팅 뒤 작업을 이어주는 서비스는 없다.
background 기능이 비활성화됐거나 print/bridge 환경이면 같은 도우미를 foreground로
기다리고 결과를 회수한다. Claude background sub-agent에 재위임한 호출의 자동 재개는
보장하지 않는다. main이 종료됐거나 알림을 놓쳤으면 보존한 run directory를 직접 조회한다.
