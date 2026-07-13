# Claude ↔ Codex 양방향 호출과 자동 wake 구성

Claude Code와 Codex CLI를 같은 개발환경에서 서로 호출하는 방법을 정리한 문서다.
처음 설치하는 사용자와 실제 호출을 수행하는 agent를 함께 독자로 둔다.
내부 프로젝트 문서가 없어도 핵심 구조를 이해하고 최소 구성을 재현할 수 있게 작성했다.

## 1. 문서 기준

| 항목 | 기준 |
| --- | --- |
| 작성일 | 2026-07-13, Asia/Seoul |
| 작업환경 | VS Code `1.128.0` + WSL2 Debian 13 터미널 |
| Claude Code | `2.1.198` |
| Codex CLI | `0.144.1` |
| 작성 모델 | `gpt-5.6-sol` |

버전은 작성일의 검증 기준이며 영구 최소 버전은 아니다.

## 2. 사용자 요약

### 무엇을 위한 구성인가

- Claude와 Codex를 서로의 sub-agent처럼 활용하는 CLI 인프라다.
- Claude에서는 `/codex-bg` skill로 Codex를 부르고, Codex에서는 `claude-coder` MCP tool로 Claude를 부른다.
- main agent가 일을 나누면 상대 agent가 조사·구현·검증을 맡는다.
- 목표는 main agent가 idle이어도 sub-agent가 완료되면 자동으로 wake되는 것이다.
- 사용자는 한쪽 CLI에서 요청하고 같은 작업 흐름 안에서 결과를 이어받는다.

### PC에는 얼마나 부담되는가

- 두 agent는 VS Code의 WSL 터미널에서 각각 CLI process로 실행된다.
- AI 추론은 원격 서비스에서 처리하므로 PC가 Claude나 Codex 모델을 직접 돌리지는 않는다.
- 전용 GPU는 필요하지 않다.
- 로컬 부하는 CLI·Node process, 저장소 탐색, 로그와 결과 파일 기록에서 생긴다.
- 한두 작업은 보통 가볍지만 큰 작업을 여러 개 병렬 실행하면 CPU·RAM·디스크 사용량이 늘어난다.

### 자동 wake는 어디까지 되는가

- Claude main이 Codex를 background로 부르는 방향은 현재 자동 wake가 된다.
- Codex가 Claude를 동기로 부르면 Codex가 기다리므로 idle wake는 아니다.
- Codex가 Claude를 background로 보내고 idle이 된 뒤 깨어나는 기능은 아직 운영 적용 전이다.
- 다만 Codex app-server로 idle wake와 작업 중 queue 전달을 실제 검증했다.
- Codex가 작업 중이면 현재 turn을 끊지 않고 결과를 보관했다가 완료 후 전달한다.
- 이 controller는 experimental이므로 별도 운영 구성과 복구 장치가 필요하다.

## 3. 구조를 한눈에 보기

```text
Windows VS Code
└─ Remote-WSL + WSL 통합 터미널
   ├─ Claude Code top-level main
   │  └─ Bash(run_in_background=true)
   │     └─ codex exec
   │        └─ 종료 이벤트 → Claude Code harness → Claude main wake
   │
   └─ Codex
      ├─ 단순 경로
      │  └─ foreground claude -p
      │     └─ Claude 종료 → shell result → 같은 Codex turn 계속
      │
      └─ 자동 wake 경로
         └─ Codex app-server를 제어하는 외부 controller
            ├─ Claude process 시작
            ├─ process/exited event 수신
            └─ idle: turn/start / active: queue 또는 turn/steer
```

여기서 wake는 잠든 모델 프로세스에 신호를 보내는 신비한 기능이 아니다.
어떤 host가 완료 이벤트를 관찰하고 다음 model turn을 시작하는 동작이다.

## 4. 현재 가능한 것과 불가능한 것

| 방향 | 방법 | 완료 처리 | 자동 wake |
| --- | --- | --- | --- |
| Claude main → Codex | `codex exec`를 Claude Bash background로 실행 | Claude Code harness가 job 종료 관찰 | 가능 |
| Claude background sub-agent → Codex | 같은 background 실행 | 결과 파일은 남길 수 있음 | 해당 sub-agent wake 불가 |
| Codex → Claude | `claude -p` foreground | Codex shell call이 끝날 때까지 대기 | wake 불필요 |
| Codex TUI → detached Claude | 임의 background process | Codex TUI가 종료 event를 model input으로 받지 않음 | 불가 |
| Codex app-server controller → Claude | `process/spawn` + `process/exited` | controller가 event 수신 후 `turn/start` | 가능, experimental |

중요한 결론은 두 가지다.

- 기존 Codex TUI나 일반 MCP server push만으로 idle Codex를 깨우는 기능은 확인되지 않았다.
- Codex app-server를 host API로 사용하면 controller가 event를 받아 Codex turn을 다시 시작할 수 있다.

## 5. Codex가 이미 작업 중일 때

Claude 결과가 도착했다고 현재 Codex turn을 무조건 끊으면 안 된다.
안전한 기본 정책은 `queue-until-idle`이다.

```text
Claude result arrives
├─ thread is idle
│  └─ turn/start(result)
└─ thread is active
   ├─ 기본: pending queue에 저장
   │  └─ turn/completed 또는 thread/status/changed=idle
   │     └─ turn/start(result)
   └─ 명시적 즉시 반영: turn/steer(result, expectedTurnId)
      └─ steer 불가 상태면 pending queue로 복귀
```

`turn/steer`는 진행 중인 turn의 방향을 바꾼다. 결과가 현재 작업과 직접 관련 있고
즉시 반영해야 할 때만 쓴다. review나 manual compact처럼 steer를 받을 수 없는 turn도
있다. 그런 상태에서 재시도 loop를 돌리지 말고 현재 turn 완료를 기다린다.

queue 항목에는 최소한 다음 값을 둔다.

- `job_id`: Claude 호출 식별자
- `thread_id`: 결과를 받을 Codex thread
- `launched_from_turn_id`: Claude를 발사한 Codex turn
- `delivery_mode`: `after_idle` 또는 `steer_if_active`
- `result`: Claude 최종 응답
- `delivered_at`: 중복 전달 방지 시각

같은 `job_id`는 한 번만 전달한다. Codex thread가 종료됐으면 새 thread를 임의로
만들지 말고 사용자에게 결과를 남긴다.

## 6. 설치

### 6.1 WSL과 VS Code

1. Windows에 WSL2와 Debian 또는 Ubuntu를 설치한다.
2. Windows VS Code와 Remote-WSL extension을 설치한다.
3. Linux filesystem 안에 작업 repo를 둔다.
4. VS Code를 WSL window로 열고 통합 터미널을 사용한다.

확인:

```bash
printf 'TERM_PROGRAM=%s\n' "$TERM_PROGRAM"
printf 'WSL_DISTRO_NAME=%s\n' "$WSL_DISTRO_NAME"
uname -a
```

### 6.2 두 CLI 설치

Node.js는 wake protocol 자체의 필수조건은 아니다. 다만 아래 npm 설치 명령을 쓰려면
Node.js와 npm이 필요하다. 두 CLI를 다른 방식으로 이미 설치했다면 이 단계는 생략한다.
이 문서의 npm 예시는 Node.js 20 계열을 사용한다.

```bash
nvm install 20
nvm use 20

npm install -g @anthropic-ai/claude-code@2.1.198
npm install -g @openai/codex@0.144.1
```

각 CLI는 새 WSL 사용자에서 직접 로그인한다.

```bash
claude
codex login

command -v node
command -v npm
command -v claude
command -v codex
node --version
claude --version
codex --version
codex login status
```

credential 파일과 token을 repo에 복사하지 않는다.

### 6.3 `/codex-bg` skill 설치

우리 환경에서 Claude가 Codex를 부를 때는 긴 명령을 매번 작성하지 않고
`/codex-bg` skill을 사용한다. 공개용 skill 전문은
[`skills/codex-bg/SKILL.md`](skills/codex-bg/SKILL.md)에 함께 올려두었다.

프로젝트 하나에서만 쓸 때:

```bash
mkdir -p .claude/skills/codex-bg
curl -fsSL \
  https://raw.githubusercontent.com/poketball1/public/main/skills/codex-bg/SKILL.md \
  -o .claude/skills/codex-bg/SKILL.md
```

모든 프로젝트에서 쓸 때는 같은 파일을
`~/.claude/skills/codex-bg/SKILL.md`에 둔다. 새 Claude Code session에서
`/codex-bg`를 호출하면 skill이 prompt·result·event log 경로를 만들고 Codex를
Claude Bash background job으로 실행한다.

공개판은 다른 PC에서도 쓸 수 있는 최소형이다. 우리 내부판은 별도 wrapper를 통해
`health`, `status`, `tail`, `changes`, `cancel`, `resume`까지 제공한다.
이 skill은 Claude main → Codex 방향을 담당하며, 반대 방향의 app-server controller를
대신하지 않는다.

Codex → Claude 방향은 현재 별도 slash skill이 아니다. Codex에 등록된
`claude-coder` MCP가 `claude_run_task`, `claude_run_write_task`,
`claude_continue_thread` 같은 tool을 제공한다.

## 7. Claude → Codex: `/codex-bg` skill

### 7.1 최소 실행 명령

Claude가 사용할 prompt와 결과 파일을 정한다.

```bash
PROJECT_ROOT="$PWD"
PROMPT_FILE="/tmp/codex-worker-prompt.txt"
RESULT_FILE="/tmp/codex-worker-result.txt"

codex exec \
  --json \
  --cd "$PROJECT_ROOT" \
  --model gpt-5.6-sol \
  --sandbox workspace-write \
  --output-last-message "$RESULT_FILE" \
  - < "$PROMPT_FILE"
```

모델을 고정할 이유가 없으면 `--model`을 생략하고 로그인 계정의 기본값을 쓴다.
처음에는 `read-only` 또는 `workspace-write` sandbox로 검증한다.

### 7.2 Claude에게 남길 규칙

프로젝트의 `CLAUDE.md`나 Claude skill에 다음 의미를 적는다.

```text
Codex 위임은 top-level Claude main이 직접 시작한다.
codex exec는 Bash background job으로 실행한다.
prompt file, result file, workdir, sandbox를 항상 기록한다.
background Claude sub-agent가 Codex를 발사한 뒤 자기 turn을 끝내고 기다리게 하지 않는다.
Codex 결과는 증거이며 Claude main이 검토하고 최종 판단한다.
```

Claude Code가 Bash tool의 `run_in_background=true`로 명령을 실행하면 job 종료가
top-level Claude main에 자동으로 surface된다. 별도 polling은 기본 경로가 아니다.

## 8. Codex → Claude: 가장 단순한 안정 경로

Codex가 Claude 답을 바로 필요로 하면 foreground로 기다린다.

```bash
claude \
  -p "이 repo를 읽고 요청한 항목만 검토해. 변경하지 마." \
  --output-format json \
  --model sonnet \
  --permission-mode default
```

이 명령은 Claude가 끝날 때까지 shell call을 유지한다. 결과가 돌아오면 같은 Codex
turn이 계속된다. 이것은 polling도 아니고 auto-wake도 아니다. 그냥 동기 호출이다.

read task에서 필요한 tool은 미리 좁혀 허용한다. write task는 별도 permission profile로
분리한다. prompt에 적는 파일 제한은 soft rule일 뿐 filesystem sandbox가 아니다.

MCP tool 형태가 필요하면 위 foreground 호출을 감싼 stdio MCP server를 만들 수 있다.
그 server도 tool call을 Claude child 종료까지 기다리게 하면 완료 의미는 동일하다.
MCP server가 나중에 notification만 보내서 idle Codex TUI를 깨운다고 가정하지 않는다.

## 9. Codex → Claude: app-server 자동 wake

### 9.1 왜 이제 가능한가

Codex CLI `0.144.1`의 app-server는 양방향 JSON-RPC stream을 제공한다.
experimental capability를 켜면 host process를 시작하는 `process/spawn`과 종료 event인
`process/exited`를 사용할 수 있다. Controller는 이 event를 받은 뒤 `turn/start`로
Codex의 다음 turn을 시작할 수 있다.

작성일에 다음 E2E를 실제 실행했다.

```text
Claude process result: CLAUDE_BG_BRIDGE_OK
Codex app-server event: process/exited
Controller action: turn/start
Codex result: CODEX_EVENT_WAKE_OK
Turn status: completed
```

Codex가 이미 작업 중인 경우도 검증했다.

```text
Claude arrived while Codex active: true
First Codex turn: FIRST_TURN_DONE
Pending queue after delivery: empty
Second Codex turn: CODEX_EVENT_WAKE_OK
Turn status: completed
```

즉 기술적으로 더는 불가능하지 않다. 다만 Codex TUI에 기능이 생긴 것이 아니라,
Codex app-server를 사용하는 별도 client/controller가 wake를 구현하는 것이다.

### 9.2 app-server 시작

```bash
codex app-server --listen stdio://
```

stdio transport는 한 줄에 JSON object 하나를 주고받는다. Wire message에서는
`"jsonrpc":"2.0"` header를 생략한다.

처음 연결하면 다음 순서를 지킨다.

```json
{"method":"initialize","id":1,"params":{"clientInfo":{"name":"claude_codex_bridge","title":"Claude Codex Bridge","version":"0.1.0"},"capabilities":{"experimentalApi":true}}}
{"method":"initialized","params":{}}
```

그 다음 Codex thread를 만들고 Claude process를 시작한다.

```json
{"method":"thread/start","id":2,"params":{"cwd":"/absolute/project/path","approvalPolicy":"never","sandbox":"read-only","ephemeral":false}}
{"method":"process/spawn","id":3,"params":{"processHandle":"claude-job-001","command":["/absolute/path/to/claude","-p","검토 질문","--output-format","json","--model","sonnet","--permission-mode","default"],"cwd":"/absolute/project/path","streamStdin":false,"streamStdoutStderr":false,"timeoutMs":180000,"tty":false}}
```

완료되면 server가 다음 notification을 보낸다.

```json
{"method":"process/exited","params":{"processHandle":"claude-job-001","exitCode":0,"stdout":"...","stderr":"...","stdoutCapReached":false,"stderrCapReached":false}}
```

thread가 idle이면 결과를 새 Codex turn으로 전달한다.

```json
{"method":"turn/start","id":4,"params":{"threadId":"<thread-id>","input":[{"type":"text","text":"Claude 작업이 완료됐다. 다음 결과를 검토하고 작업을 계속해: <result>"}]}}
```

thread가 active이고 즉시 반영하기로 결정한 경우에만 active turn id를 넣어 steer한다.

```json
{"method":"turn/steer","id":5,"params":{"threadId":"<thread-id>","expectedTurnId":"<active-turn-id>","input":[{"type":"text","text":"Claude 결과가 도착했다: <result>"}]}}
```

안전한 controller는 active 상태에서 기본적으로 steer하지 않는다. `turn/completed`를
기다린 뒤 queued result를 `turn/start`로 전달한다.

## 10. 자동 wake controller의 최소 상태기계

언어나 framework는 자유지만 다음 상태는 빠뜨리지 않는다.

```js
const pending = new Map(); // jobId -> result envelope
let activeTurnId = null;

function onClaudeExited(job) {
  if (job.exitCode !== 0) return recordFailure(job);
  if (alreadyDelivered(job.id)) return;

  if (!activeTurnId) {
    startCodexTurn(job.result);
    markDelivered(job.id);
    return;
  }

  if (job.deliveryMode === "steer_if_active" && isSteerable(activeTurnId)) {
    steerCodexTurn(activeTurnId, job.result)
      .then(() => markDelivered(job.id))
      .catch(() => pending.set(job.id, job));
    return;
  }

  pending.set(job.id, job);
}

function onCodexTurnCompleted() {
  activeTurnId = null;
  const next = oldestPendingJob();
  if (!next) return;
  pending.delete(next.id);
  startCodexTurn(next.result).then(() => markDelivered(next.id));
}
```

운영 구현에는 다음도 필요하다.

- process와 Codex thread가 죽었을 때의 terminal failure 기록
- stdout/stderr size cap과 secret redaction
- controller restart 뒤 pending queue 복구
- 같은 `job_id` 중복 delivery 방지
- active turn id와 `expectedTurnId` 일치 확인
- 권한 요청을 누가 처리할지에 대한 정책
- app-server process를 localhost 밖에 노출하지 않는 기본값

## 11. 권한과 보안

- `process/spawn`은 Codex sandbox 밖의 host process를 실행한다.
- 이 API는 experimental이므로 신뢰된 local controller에서만 사용한다.
- Claude prompt와 결과에 token, password, private key를 넣지 않는다.
- stdout, stderr, prompt, model response를 저장하는 log는 민감 데이터로 취급한다.
- result file과 queue DB는 user-only permission을 적용한다.
- `allowed workdir`는 시작 cwd 제한일 뿐 filesystem containment가 아니다.
- prompt의 `changed files only`는 advisory rule이지 기계적 sandbox가 아니다.
- 처음에는 read-only Claude와 read-only Codex turn으로 smoke test한다.
- WebSocket transport를 쓸 때는 loopback만 사용하고 인증 없이 외부에 열지 않는다.

## 12. 검증 순서

```bash
node --version
claude --version
codex --version
claude auth status --json
codex login status
codex app-server --help
```

그 다음 아래 순서로 확인한다.

1. Claude에서 짧은 `codex exec` background job을 실행한다.
2. Codex 결과 파일과 Claude main completion wake를 확인한다.
3. Codex에서 짧은 `claude -p` foreground 호출을 실행한다.
4. 같은 Codex turn이 Claude 결과 뒤에 계속되는지 확인한다.
5. app-server controller에서 짧은 Claude process를 실행한다.
6. `process/exited` notification을 확인한다.
7. idle Codex thread에 `turn/start`를 보내 결과를 확인한다.
8. active Codex turn 중에는 결과가 queue되는지 확인한다.
9. turn 완료 뒤 queued 결과가 한 번만 전달되는지 확인한다.
10. Claude 실패·timeout·controller restart 시 결과가 유실되지 않는지 확인한다.

작성일 기준 1~9의 핵심 event 흐름과 active queue 전달은 통과했다. 실패·timeout과
controller restart 복구는 운영 controller를 만들 때 별도 durability 검증이 필요하다.

## 13. 현재 한계

- app-server `process/spawn` 계열은 experimental이다.
- 이 문서의 자동 wake는 기존 Codex TUI session에 임의로 message를 넣는 기능이 아니다.
- 자동 wake controller가 관리하는 app-server thread 안에서만 신뢰할 수 있다.
- controller가 없으면 Codex → background Claude 완료는 자동 전달되지 않는다.
- Claude background sub-agent의 자체 completion wake 제약도 별개의 문제로 남는다.
- CLI upgrade 뒤에는 protocol schema와 E2E를 다시 검증해야 한다.

## 14. 공개 근거

- [Codex App Server 문서](https://learn.chatgpt.com/docs/app-server)
- [Codex 0.144.1 release](https://github.com/openai/codex/releases/tag/rust-v0.144.1)
- [Codex repository](https://github.com/openai/codex)

공식 문서가 설명하는 핵심은 `process/exited`, `thread/status/changed`,
`turn/start`, `turn/steer`다. 이 문서는 그 네 event를 Claude ↔ Codex bridge에
적용하고, 실제 local E2E로 동작을 확인한 결과다.
