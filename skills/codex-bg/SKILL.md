---
name: codex-bg
description: "Claude main이 Codex를 background sub-agent로 실행하고 Claude Code harness의 완료 알림으로 결과를 회수한다."
argument-hint: "<task> [read-only|write] [workdir]"
allowed-tools: Bash, Read, Write
---

# /codex-bg

Claude main이 Codex에게 조사·구현·검증을 맡길 때 사용한다.
Codex는 Claude Code의 Bash background job으로 실행한다.
Job이 끝나면 Claude Code harness가 top-level Claude main을 다시 깨운다.

## 중요한 경계

- 이 skill은 top-level Claude main이 직접 실행한다.
- Claude background sub-agent에게 이 skill 실행을 다시 맡기지 않는다.
- 그런 다단 위임에서는 작업 파일이 남아도 background sub-agent가 자동 wake되지 않을 수 있다.
- Codex 결과는 증거다. 최종 판단과 사용자 보고는 Claude main이 맡는다.
- 기본 sandbox는 `read-only`다. 파일 변경이 필요한 작업만 `workspace-write`를 선택한다.
- 기존 worktree 변경을 되돌리거나 destructive git 명령을 실행하지 않는다.

## 실행 절차

1. 작업할 repository의 절대경로를 확인한다.
2. `command -v codex`와 `codex login status`를 확인한다.
3. 충돌하지 않는 짧은 `<slug>`를 정한다.
4. 다음 세 경로를 정한다.

```text
prompt: ${TMPDIR:-/tmp}/claude-codex-bridge/<slug>.prompt.md
result: ${TMPDIR:-/tmp}/claude-codex-bridge/<slug>.result.md
events: ${TMPDIR:-/tmp}/claude-codex-bridge/<slug>.events.jsonl
```

5. Write tool로 prompt 파일을 작성한다. 다음 내용을 포함한다.

- 목표와 완료조건
- 읽거나 수정해도 되는 범위
- 금지 범위
- 필요한 검증
- 최종 보고 형식

6. Claude의 Bash tool에서 아래 명령을 `run_in_background=true`로 실행한다.

```bash
mkdir -p "${TMPDIR:-/tmp}/claude-codex-bridge"

codex exec \
  --json \
  --cd "<ABSOLUTE_WORKDIR>" \
  --sandbox read-only \
  --output-last-message "<ABSOLUTE_RESULT_FILE>" \
  - < "<ABSOLUTE_PROMPT_FILE>" \
  > "<ABSOLUTE_EVENT_LOG>" 2>&1
```

파일 변경이 승인된 작업만 `--sandbox workspace-write`로 바꾼다.
`danger-full-access`를 공개 기본값으로 사용하지 않는다.

7. Bash job id와 prompt·result·events 경로를 현재 작업 기록에 남긴다.
8. 다른 독립 작업이 있으면 계속 진행한다. 할 일이 없으면 main은 기다려도 된다.
9. 완료 알림이 오면 result 파일과 events 마지막 항목을 읽는다.
10. write 작업이면 `git diff`로 Codex 변경을 직접 검토하고 필요한 검증을 다시 실행한다.

## 완료 보고

다음 형식으로 Claude main에게 결과를 돌려준다.

```text
Status: completed | blocked | failed
Workdir: <absolute path>
Result: <result file>
Events: <events file>
Changed files: <files or none>
Verification: <commands and results>
Remaining risk: <risk or none>
```

## 실패 처리

- result 파일이 없으면 events 파일의 마지막 오류와 Bash exit status를 확인한다.
- Codex login이 끊겼으면 사용자가 WSL 터미널에서 다시 로그인한다.
- prompt가 잘못됐으면 실행 중인 turn에 억지로 끼워 넣지 말고 job을 종료한 뒤 새 prompt로 다시 실행한다.
- Claude main이 아닌 background sub-agent에서 실행했다면 자동 wake를 기대하지 말고 top-level main에서 다시 시작한다.
