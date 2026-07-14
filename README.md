# Claude ↔ Codex 양방향 호출 인프라 설치·운영 매뉴얼

이 저장소는 Claude Code와 Codex CLI를 같은 WSL 개발환경에서 서로 호출하기 위한
실제 설정, skill, MCP server와 검증 코드를 함께 제공한다.

이 README의 목표는 개념 소개가 아니다. 새 PC에서 아래 순서대로 실행하면 다음 두
운영 경로를 재현하는 것이다.

1. Claude main → Codex worker: Claude Code의 background Bash job으로 `codex exec`를
   실행하고, job 종료를 Claude Code harness가 감지해 Claude main을 다시 깨운다.
2. Codex main → Claude worker: `claude-coder` stdio MCP tool call이 Claude child가
   끝날 때까지 기다리고, 결과를 같은 Codex turn에 동기로 반환한다.

추가로 Codex app-server가 관리하는 thread에서 Claude background process의 완료
event로 Codex turn을 새로 시작하는 experimental wake probe도 제공한다. 이것은
기존 Codex TUI를 임의로 깨우는 기능이 아니며 안정 운영 기본값도 아니다.

---

## 1. 작성·검증 기준

| 항목 | 이 문서의 실측 기준 |
| --- | --- |
| 갱신일 | 2026-07-14, Asia/Seoul |
| Windows editor | VS Code `1.128.0` |
| terminal/runtime | WSL2, Debian GNU/Linux 13 |
| Claude Code | `2.1.198` |
| Codex CLI | `0.144.1` |
| bridge Node.js | `20.18.0` |
| 작성 모델 | `gpt-5.6-sol` |
| 공개 저장소 | [poketball1/public](https://github.com/poketball1/public) |

이 값은 재현한 snapshot이다. 영구 최소 버전이라는 뜻은 아니다. CLI를 올린 뒤에는
`claude-coder` live smoke와 app-server probe를 다시 실행해야 한다.

Codex `0.115`부터 Linux sandbox가 bubblewrap 기반으로 바뀌어 WSL1은 지원되지
않는다. Windows에서 이 매뉴얼을 사용할 때는 WSL2를 사용한다.

---

## 2. 사용자 요약

- 이 구성은 Claude와 Codex를 서로의 sub-agent처럼 활용하는 CLI 인프라다.
- main agent는 작업을 나누고 상대 agent에게 조사·구현·검증을 맡긴다.
- 목표는 main agent가 idle이어도 sub-agent가 끝나면 자동으로 다시 이어지는 것이다.
- Claude main에서 Codex를 부를 때는 `/codex-bg` skill을 사용한다.
- Codex가 끝나면 Claude Code가 background job 종료를 감지해 Claude main을 깨운다.
- 이때 단순한 shell `&`가 아니라 Claude Code가 추적하는 background job이어야 한다.
- Codex main에서 Claude를 부를 때는 `claude-coder` MCP tool을 사용한다.
- 이 방향은 Claude가 끝날 때까지 같은 Codex turn이 기다리므로 별도 wake가 필요 없다.
- Codex가 Claude를 완전히 분리해 보내고 먼저 idle이 되는 방식은 안정 기본 경로가 아니다.
- 그런 경우를 위해 app-server 기반 idle wake와 busy queue를 실증한 probe도 제공한다.
- Codex가 이미 작업 중이면 Claude 결과로 현재 turn을 끊지 않고 완료 뒤 전달한다.
- Claude와 Codex의 모델 실행은 원격 서비스에서 처리되므로 PC가 모델 자체를 돌리지는 않는다.
- 전용 GPU는 필요하지 않다.
- 로컬 PC 부하는 CLI·Node process, 저장소 검색, Git 명령과 로그 기록에서 생긴다.
- 한두 작업은 대체로 가볍지만 큰 저장소에서 여러 작업을 병렬 실행하면 CPU·RAM·disk 사용량이 늘어난다.
- 처음에는 양방향 smoke를 한 개씩 통과시킨 뒤 병렬 작업 수를 늘리는 것이 안전하다.

아래 세 절은 이 요약의 정확한 완료·wake 계약이다.

### 2.1 Claude main → Codex

`/codex-bg` skill은 Claude main이 Claude Code의 Bash tool을
`run_in_background=true`로 호출하게 한다.

```text
Claude main
  └─ Claude Code Bash tool: run_in_background=true
      └─ codex exec --json ...
          ├─ result file
          └─ JSONL event log

codex process exits
  └─ Claude Code harness observes tracked background job completion
      └─ top-level Claude main receives completion event and continues
```

중요한 조건:

- top-level Claude main이 직접 background Bash job을 시작해야 한다.
- shell 명령 끝에 단순히 `&`나 `nohup`를 붙이는 것과 같지 않다.
- Claude background sub-agent에게 `/codex-bg`를 다시 시키지 않는다.
- Codex 결과가 성공했다는 사실과 Claude main이 최종 완료를 판정하는 것은 별개다.
- 이 방향의 wake는 Claude Code client/harness 기능이다. 별도 polling daemon이 아니다.

### 2.2 Codex main → Claude

`claude-coder` MCP server는 `claude -p --output-format json`을 child process로
실행한다. MCP `tools/call` 응답은 Claude child가 끝난 뒤에만 반환된다.

```text
Codex turn
  └─ claude-coder MCP tools/call
      └─ local Claude Code child process
          └─ completed JSON result
      └─ MCP tool result
  └─ the same Codex turn continues
```

이 경로는 Codex가 idle로 끝난 뒤 다시 깨어나는 방식이 아니다. Codex가 MCP tool
result를 기다리고 있으므로 별도 wake가 필요 없다. 현재 안정 운영 경로는 이것이다.

### 2.3 Codex가 Claude를 background로 보내고 먼저 idle이 되는 경우

일반 Codex TUI와 일반 MCP notification만으로는 detached Claude의 완료를 기존
Codex TUI turn에 주입할 수 없다.

이 저장소의 `bridge/codex-app-server-wake/probe.mjs`는 Codex app-server가 관리하는
별도 thread에서 다음 흐름을 검증한다.

```text
process/spawn(Claude)
  → process/exited
  → Codex thread state 확인
     ├─ idle   → turn/start
     └─ active → queue에 보관
                 → turn/completed
                 → turn/start
```

이 경로는 experimental proof다. restart 뒤 queue 복구, durable storage, 중복 전달
방지와 permission routing을 갖춘 운영 controller가 아니다.

---

## 3. 저장소에 포함된 실제 파일

```text
public/
├─ README.md
├─ install.sh
├─ examples/
│  └─ codex-config.toml
├─ skills/
│  └─ codex-bg/
│     └─ SKILL.md
└─ bridge/
   ├─ claude-coder-mcp/
   │  ├─ package.json
   │  ├─ run.sh
   │  ├─ server.mjs
   │  └─ smoke.mjs
   ├─ codex-app-server-wake/
   │  └─ probe.mjs
   ├─ lib/
   │  └─ lifecycle-audit.mjs
   └─ mcp-stdio-supervisor.mjs
```

각 파일의 역할:

| 파일 | 역할 |
| --- | --- |
| `install.sh` | 프로젝트 skill 복사, Codex MCP TOML 추가, 기존 config backup |
| `skills/codex-bg/SKILL.md` | Claude main → Codex background 호출 계약 |
| `bridge/claude-coder-mcp/server.mjs` | Codex에 Claude read/write/resume tool 제공 |
| `bridge/claude-coder-mcp/run.sh` | Node·Claude 경로 확인, state dir 준비, supervisor 시작 |
| `bridge/mcp-stdio-supervisor.mjs` | MCP child crash 뒤 다음 요청을 위한 재기동 |
| `bridge/claude-coder-mcp/smoke.mjs` | MCP initialize, tool list, health, 실제 Claude 응답 검증 |
| `examples/codex-config.toml` | 수동 설치용 전체 TOML 예제 |
| `bridge/codex-app-server-wake/probe.mjs` | idle/busy event-driven wake 실증 |

public판에는 credential 파일이 없다. 현재 WSL 사용자가 각 CLI에 직접 로그인한
상태를 사용한다.

---

## 4. 설치 전에 정할 경로

이 문서의 예시는 두 directory를 구분한다.

```bash
# 이 공개 인프라 저장소를 보관할 위치
BRIDGE_REPO="$HOME/code/claude-codex-infra"

# Claude와 Codex가 실제로 작업할 사용자 repository
PROJECT="$HOME/code/my-project"
```

`BRIDGE_REPO`는 설치 뒤에도 삭제하거나 옮기면 안 된다. Codex config의 MCP command가
그 안의 `bridge/claude-coder-mcp/run.sh` 절대경로를 가리킨다.

`PROJECT`는 반드시 실제 존재하는 절대경로여야 한다. installer는 상대경로를
거부한다.

권장 위치는 WSL Linux filesystem 아래 `/home/<user>/...`다. `/mnt/c/...`에서도
실행할 수 있지만 큰 repository의 file I/O, symlink와 permission 처리가 느리거나
다르게 동작할 수 있다.

---

## 5. Windows, WSL2와 VS Code 준비

### 5.1 WSL2 설치

관리자 PowerShell에서 실행한다.

```powershell
wsl --install -d Debian
wsl --update
wsl --set-default-version 2
wsl -l -v
```

`wsl -l -v`의 VERSION 열이 `2`여야 한다. 설치나 update 뒤 재부팅 요청이 나오면
Windows를 재부팅한다.

Ubuntu를 사용해도 되지만 이 문서의 실측 환경은 Debian 13이다.

### 5.2 VS Code의 WSL extension 설치

Windows 쪽 VS Code에 WSL extension을 설치한다.

```powershell
code --install-extension ms-vscode-remote.remote-wsl
```

그다음 WSL terminal에서 프로젝트를 연다.

```bash
mkdir -p "$HOME/code"
cd "$HOME/code"
code .
```

확인할 것:

- VS Code 왼쪽 아래에 `WSL: Debian` 또는 사용하는 distro가 보인다.
- integrated terminal의 path가 `C:\...`가 아니라 `/home/...`다.
- 아래 명령이 distro 이름을 출력한다.

```bash
printf 'WSL_DISTRO_NAME=%s\n' "$WSL_DISTRO_NAME"
uname -srmo
pwd
```

Claude, Codex, Node는 Windows PowerShell이 아니라 이 WSL terminal 안에 설치한다.

---

## 6. WSL 기본 도구와 Node.js 설치

### 6.1 기본 package

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
```

### 6.2 Node.js가 왜 필요한가

Claude native installer와 Codex native installer 자체는 Node.js를 요구하지 않는다.
하지만 이 저장소의 `claude-coder` MCP server, supervisor, smoke test와 app-server
probe는 `.mjs` 파일이므로 Node.js가 필요하다.

Node를 설치하지 않으면 다음 최소 경로만 가능하다.

- Claude → Codex: Claude가 `codex exec`를 직접 background 실행
- Codex → Claude: Codex가 shell에서 `claude -p`를 foreground 실행

이 README에 포함된 MCP server와 app-server probe까지 사용하려면 Node.js 20 이상을
설치한다.

현재 환경처럼 nvm을 쓰는 예:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

nvm install 20
nvm alias default 20
nvm use 20

node --version
npm --version
```

기대값은 `node --version`이 `v20.x` 이상인 것이다.

Claude Code를 npm으로 설치하는 방법도 있지만 Claude Code `2.1.198`의 npm package는
Node.js 22 이상을 요구한다. 이 문서에서는 혼동을 피하기 위해 Claude와 Codex는
각각 공식 native installer로 설치하고, Node 20은 bridge runtime으로만 사용한다.

---

## 7. Claude Code와 Codex CLI 설치

### 7.1 Claude Code

WSL 안에서 Anthropic 공식 native installer를 실행한다.

```bash
curl -fsSL https://claude.ai/install.sh | bash
hash -r
claude --version
claude doctor
```

`claude`가 안 보이면 새 WSL shell을 열거나 `$HOME/.local/bin`이 PATH에 있는지
확인한다.

```bash
printf '%s\n' "$PATH"
ls -l "$HOME/.local/bin/claude"
command -v claude
```

### 7.2 Codex CLI

WSL 안에서 OpenAI 공식 installer를 실행한다.

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
hash -r
codex --version
```

설치 방식이나 release가 달라 `0.144.1`보다 새 버전이 설치돼도 된다. 다만 이 문서의
app-server probe는 CLI update 뒤 다시 검증해야 한다.

### 7.3 설치 위치가 같은 WSL인지 확인

```bash
command -v node
command -v claude
command -v codex

node --version
claude --version
codex --version

file "$(command -v claude)"
file "$(command -v codex)"
```

세 command가 모두 WSL 안에서 실행돼야 한다. Windows의 `.exe`가 섞이면 MCP child의
HOME, credential과 path가 서로 달라진다.

---

## 8. 두 CLI 로그인

### 8.1 Claude 로그인

```bash
cd "$PROJECT"
claude
```

브라우저 인증을 끝내고 Claude CLI를 종료한 뒤 확인한다.

```bash
claude auth status --json
```

Claude Code는 Pro, Max, Team, Enterprise 또는 Console/API 계정이 필요하다. 현재
public bridge는 로그인 token을 저장소에 복사하지 않는다.

### 8.2 Codex 로그인

```bash
codex login
codex login status
```

두 CLI는 같은 WSL 사용자로 직접 로그인한다. 다른 PC의 credential 파일,
`~/.codex/auth.json`, Claude credential, OAuth token이나 API key를 복사하거나
public repository에 넣지 않는다.

---

## 9. public 저장소와 사용자 프로젝트 준비

```bash
mkdir -p "$HOME/code"
cd "$HOME/code"

git clone https://github.com/poketball1/public.git claude-codex-infra
git clone <YOUR_PROJECT_GIT_URL> my-project

export BRIDGE_REPO="$HOME/code/claude-codex-infra"
export PROJECT="$HOME/code/my-project"

test -d "$BRIDGE_REPO/.git"
test -d "$PROJECT"
test -x "$(command -v node)"
test -x "$(command -v claude)"
test -x "$(command -v codex)"
```

이미 사용자 프로젝트가 있으면 두 번째 clone은 생략하고 `PROJECT`만 실제 절대경로로
설정한다.

---

## 10. 권장 설치: installer 사용

installer는 다음 작업만 한다.

1. `skills/codex-bg/SKILL.md`를 project 또는 user skill directory로 복사한다.
2. 기존 Codex config를 timestamp backup한다.
3. `claude-coder` MCP table을 Codex config에 추가한다.
4. Node source 구문을 검사한다.

installer가 하지 않는 일:

- WSL, VS Code, Node, Claude 또는 Codex 설치
- Claude/Codex 로그인
- 기존 `claude-coder` table 덮어쓰기
- dangerous permission 활성화
- app-server controller 상시 실행

먼저 dry-run한다.

```bash
cd "$BRIDGE_REPO"

./install.sh \
  --project "$PROJECT" \
  --dry-run
```

출력에서 다음 절대경로를 확인한다.

- `project`가 사용자 프로젝트인가
- `codex config`가 수정하려는 config인가
- `skill target`이 맞는가
- `MCP wrapper`가 public clone 안에 있는가
- `NODE_BIN`과 `CLAUDE_BIN`이 WSL binary인가

문제가 없으면 실제 설치한다.

```bash
./install.sh --project "$PROJECT"
```

기본 설치 위치:

| 대상 | 기본 위치 |
| --- | --- |
| Claude skill | `$PROJECT/.claude/skills/codex-bg/SKILL.md` |
| Codex config | `$HOME/.codex/config.toml` |
| bridge state/log | `$HOME/.local/state/claude-codex-bridge/` |

모든 project에서 `/codex-bg`를 사용하려면:

```bash
./install.sh \
  --project "$PROJECT" \
  --skill-scope user
```

다른 Codex config를 사용하려면:

```bash
./install.sh \
  --project "$PROJECT" \
  --codex-config "$PROJECT/.codex/config.toml"
```

project-scoped `.codex/config.toml`은 trusted project에서만 적용된다.

installer가 기존 `claude-coder` table을 발견하면 아무것도 덮어쓰지 않고 종료한다.
기존 table을 먼저 읽고 보존할 내용을 결정한 다음 수동 설치 절을 사용한다.

---

## 11. 수동 설치

installer를 쓰지 않는 경우 이 절을 그대로 따른다.

### 11.1 `/codex-bg` skill 복사

project 하나에서만 사용:

```bash
mkdir -p "$PROJECT/.claude/skills/codex-bg"
cp "$BRIDGE_REPO/skills/codex-bg/SKILL.md" \
  "$PROJECT/.claude/skills/codex-bg/SKILL.md"
```

모든 project에서 사용:

```bash
mkdir -p "$HOME/.claude/skills/codex-bg"
cp "$BRIDGE_REPO/skills/codex-bg/SKILL.md" \
  "$HOME/.claude/skills/codex-bg/SKILL.md"
```

### 11.2 실행 파일 권한

```bash
chmod +x "$BRIDGE_REPO/bridge/claude-coder-mcp/run.sh"
chmod +x "$BRIDGE_REPO/bridge/claude-coder-mcp/smoke.mjs"
chmod +x "$BRIDGE_REPO/bridge/codex-app-server-wake/probe.mjs"
```

### 11.3 절대경로 수집

```bash
NODE_BIN="$(command -v node)"
CLAUDE_BIN="$(command -v claude)"
MCP_WRAPPER="$BRIDGE_REPO/bridge/claude-coder-mcp/run.sh"

printf 'NODE_BIN=%s\n' "$NODE_BIN"
printf 'CLAUDE_BIN=%s\n' "$CLAUDE_BIN"
printf 'MCP_WRAPPER=%s\n' "$MCP_WRAPPER"
printf 'PROJECT=%s\n' "$PROJECT"

test -x "$NODE_BIN"
test -x "$CLAUDE_BIN"
test -x "$MCP_WRAPPER"
test -d "$PROJECT"
```

### 11.4 Codex TOML 추가

`$HOME/.codex/config.toml`에 아래 block을 추가한다. angle bracket을 그대로
남기지 않는다.

TOML string 안의 `~`, `$HOME`와 shell variable은 확장되지 않는다. 반드시
`/home/alice/...` 같은 실제 절대경로를 쓴다.

```toml
[mcp_servers.claude-coder]
command = "/home/YOU/code/claude-codex-infra/bridge/claude-coder-mcp/run.sh"
args = []
startup_timeout_sec = 10.0
tool_timeout_sec = 1860.0
default_tools_approval_mode = "approve"

[mcp_servers.claude-coder.env]
NODE_BIN = "/home/YOU/.nvm/versions/node/v20.18.0/bin/node"
CLAUDE_BIN = "/home/YOU/.local/bin/claude"
CLAUDE_MCP_MODEL = "sonnet"
CLAUDE_MCP_ALLOWED_MODELS = "sonnet,opus,haiku"
CLAUDE_MCP_WORKDIR = "/home/YOU/code/my-project"
CLAUDE_MCP_ALLOWED_WORKDIRS = "/home/YOU/code/my-project"
CLAUDE_MCP_DEFAULT_PERMISSION_MODE = "default"
CLAUDE_MCP_DEFAULT_WRITE_PERMISSION_MODE = "acceptEdits"
CLAUDE_MCP_ALLOW_DANGEROUS = "0"
CLAUDE_MCP_ALLOW_BARE = "0"
CLAUDE_MCP_DEFAULT_WAIT_MS = "1800000"
CLAUDE_MCP_MAX_WAIT_MS = "1800000"
CLAUDE_MCP_WRITE_TIMEOUT_MS = "1800000"
CLAUDE_MCP_RUN_AUDIT_PATH = "/home/YOU/.local/state/claude-codex-bridge/claude-mcp-runs.jsonl"
CLAUDE_MCP_LIFECYCLE_AUDIT_PATH = "/home/YOU/.local/state/claude-codex-bridge/claude-mcp-lifecycle.jsonl"
MCP_SUPERVISOR_LIFECYCLE_AUDIT_PATH = "/home/YOU/.local/state/claude-codex-bridge/mcp-supervisor-claude-coder-lifecycle.jsonl"
PATH = "/home/YOU/.local/bin:/home/YOU/.nvm/versions/node/v20.18.0/bin:/usr/local/bin:/usr/bin:/bin"
```

같은 내용의 standalone 예시는
`examples/codex-config.toml`에도 있다.

### 11.5 TOML table 중복 확인

```bash
rg -n '^\[mcp_servers\.("?claude-coder"?)\]$' \
  "$HOME/.codex/config.toml"
```

결과가 한 줄이어야 한다. 같은 table이 두 번 있으면 Codex가 config parse 단계에서
실패한다.

### 11.6 Codex 완전 재시작

MCP config는 실행 중인 Codex process에 자동 주입되지 않는다.

1. 실행 중인 Codex TUI, CLI와 IDE Codex session을 닫는다.
2. 새 WSL terminal을 연다.
3. `PROJECT`에서 Codex를 다시 시작한다.

```bash
cd "$PROJECT"
codex mcp get claude-coder
codex mcp list
codex
```

`codex mcp get claude-coder`에서 확인할 값:

- `enabled: true`
- `transport: stdio`
- `command`가 public clone의 `run.sh` 절대경로
- `startup_timeout_sec: 10`
- `tool_timeout_sec: 1860`

---

## 12. 설치 직후 독립 smoke test

Codex UI를 열기 전에 MCP source 자체를 검증할 수 있다.

### 12.1 구문 검사

```bash
cd "$BRIDGE_REPO"

node --check bridge/claude-coder-mcp/server.mjs
node --check bridge/mcp-stdio-supervisor.mjs
node --check bridge/lib/lifecycle-audit.mjs
node --check bridge/claude-coder-mcp/smoke.mjs
node --check bridge/codex-app-server-wake/probe.mjs

bash -n install.sh
bash -n bridge/claude-coder-mcp/run.sh
```

모든 명령이 출력 없이 exit code 0이면 통과다.

### 12.2 MCP health smoke

```bash
cd "$PROJECT"

node "$BRIDGE_REPO/bridge/claude-coder-mcp/smoke.mjs"
```

기대 결과:

```json
{
  "ok": true,
  "mode": "health",
  "tools": [
    "claude_health",
    "claude_run_task",
    "claude_run_write_task",
    "claude_continue_thread",
    "claude_list_runs"
  ]
}
```

이 test는 Claude model turn을 사용하지 않는다. `claude --version`과 MCP protocol,
tool list만 확인한다.

### 12.3 실제 Claude 응답 smoke

Claude 사용량이 발생한다.

```bash
cd "$PROJECT"

node "$BRIDGE_REPO/bridge/claude-coder-mcp/smoke.mjs" \
  --live \
  --model haiku
```

계정에 Haiku가 없으면 `--model sonnet`으로 바꾼다.

기대 핵심 필드:

```json
{
  "ok": true,
  "mode": "live",
  "task": {
    "status": "completed",
    "exit_code": 0,
    "timed_out": false,
    "final_response": "CLAUDE_CODER_MCP_OK"
  }
}
```

이 test가 통과하면 public MCP source, 현재 WSL Claude 로그인, model 선택과 동기
result 반환이 모두 동작한다.

---

## 13. Claude → Codex 사용법

### 13.1 Codex CLI만 먼저 확인

Claude를 열기 전에 `codex exec`가 독립적으로 되는지 확인한다.

```bash
cd "$PROJECT"

printf '%s\n' \
  'Do not modify files. Reply exactly CODEX_EXEC_OK.' \
  | codex exec \
      --json \
      --cd "$PROJECT" \
      --sandbox read-only \
      --output-last-message /tmp/codex-exec-smoke.result.md \
      - \
      > /tmp/codex-exec-smoke.events.jsonl

cat /tmp/codex-exec-smoke.result.md
tail -n 5 /tmp/codex-exec-smoke.events.jsonl
```

`/tmp/codex-exec-smoke.result.md`에 `CODEX_EXEC_OK`가 있어야 한다.

여기서 실패하면 `/codex-bg`나 wake 문제가 아니다. 먼저 Codex login, PATH, model,
sandbox 문제를 해결한다.

### 13.2 새 Claude Code session 시작

skill은 session 시작 시 발견되는 것이 가장 확실하다. skill을 복사한 뒤 실행 중이던
Claude session을 닫고 새로 시작한다.

```bash
cd "$PROJECT"
claude
```

Claude에게 다음처럼 요청한다.

```text
/codex-bg를 사용해서 read-only smoke test를 해.
Codex는 파일을 수정하지 말고 마지막 응답으로 CODEX_BG_OK만 반환하게 해.
반드시 top-level Claude main이 Bash run_in_background=true로 직접 시작해.
```

Claude가 해야 하는 핵심 명령 모양:

```bash
mkdir -p /tmp/claude-codex-bridge

codex exec \
  --json \
  --cd "/absolute/project/path" \
  --sandbox read-only \
  --output-last-message "/tmp/claude-codex-bridge/smoke.result.md" \
  - < "/tmp/claude-codex-bridge/smoke.prompt.md" \
  > "/tmp/claude-codex-bridge/smoke.events.jsonl" 2>&1
```

이 shell 명령을 사용자가 직접 background로 치는 것이 아니라 Claude Code의 Bash
tool이 `run_in_background=true`로 시작해야 한다.

### 13.3 기대되는 lifecycle

1. Claude main이 prompt file을 쓴다.
2. Claude Bash tool이 tracked background job ID를 반환한다.
3. Claude main은 다른 일을 하거나 idle 상태가 된다.
4. Codex가 종료한다.
5. Claude Code harness가 background job 종료를 main session에 전달한다.
6. Claude main이 result와 events를 읽는다.
7. write 작업이면 Claude main이 `git diff`와 필요한 test를 검토한다.
8. Claude main이 사용자에게 최종 결과를 보고한다.

### 13.4 read와 write mode

처음 smoke는 항상 `read-only`다.

파일 변경이 필요한 경우에만:

```bash
--sandbox workspace-write
```

로 바꾼다.

`danger-full-access`를 public 기본값으로 사용하지 않는다. prompt의 “이 파일만
수정해”는 기계적 sandbox가 아니다. `workspace-write`도 working directory 안의
광범위한 write가 가능하므로 dirty worktree와 diff를 반드시 확인한다.

### 13.5 결과 파일

skill의 기본 경로:

```text
/tmp/claude-codex-bridge/<slug>.prompt.md
/tmp/claude-codex-bridge/<slug>.result.md
/tmp/claude-codex-bridge/<slug>.events.jsonl
```

진단:

```bash
ls -lah /tmp/claude-codex-bridge
cat /tmp/claude-codex-bridge/<slug>.result.md
tail -n 50 /tmp/claude-codex-bridge/<slug>.events.jsonl
```

result가 없으면 events의 마지막 `turn.failed`, `error` 또는 process exit를 본다.

### 13.6 자동 wake가 안 되는 잘못된 모양

다음 모양은 사용하지 않는다.

```text
Claude main
  └─ Claude background sub-agent
       └─ codex exec background
       └─ sub-agent turn 종료
```

Codex result file은 남을 수 있지만 그 background Claude sub-agent가 completion
event로 자동 재개된다고 보장할 수 없다.

또한 Claude가 Bash tool을 foreground로 실행하면 동작은 하지만 Claude main이 계속
기다리므로 background wake의 장점이 없다.

---

## 14. Codex → Claude `claude-coder` 사용법

### 14.1 health tool

Codex를 새로 시작한 뒤 다음 요청을 한다.

```text
claude-coder의 claude_health를 호출해서
ok, Claude version, claude_bin, default_workdir,
allowed_workdirs, allow_bare, allow_dangerous를 보여줘.
```

기대값:

- `ok=true`
- `version`에 Claude Code version
- `claude_bin`이 같은 WSL의 실제 binary
- `default_workdir`이 `PROJECT`
- `allow_bare=false`
- `allow_dangerous=false`

### 14.2 read/review task

Codex에게 다음처럼 요청한다.

```text
claude-coder의 claude_run_task를 호출해.
workingDirectory는 현재 프로젝트 절대경로로 설정해.
bare는 생략하거나 false로 해.
Claude에게 README 첫 20줄을 읽고 제목만 반환하게 해.
파일은 수정하지 마.
```

MCP argument의 핵심 모양:

```json
{
  "prompt": "README 첫 20줄을 읽고 제목만 반환해. 파일은 수정하지 마.",
  "workingDirectory": "/home/YOU/code/my-project",
  "model": "sonnet",
  "permissionMode": "default",
  "bare": false
}
```

`default` mode에서 file read는 승인 없이 가능하다. Bash command처럼 승인 질문이
필요한 action은 headless `-p` session에서 사람이 답할 수 없으므로 denied될 수 있다.
단순 review는 Read/Grep 중심 prompt로 시작한다.

### 14.3 write task

```text
claude-coder의 claude_run_write_task를 호출해.
작업 목표와 수정 가능한 파일을 명시하고,
permissionMode는 acceptEdits로 해.
dangerouslySkipPermissions는 사용하지 마.
작업 전후 changed files와 diff_stat을 반환받아.
```

argument 예:

```json
{
  "prompt": "docs/example.md의 오탈자 한 곳만 고쳐.",
  "workingDirectory": "/home/YOU/code/my-project",
  "model": "sonnet",
  "permissionMode": "acceptEdits",
  "bare": false,
  "changedFilesOnly": [
    "docs/example.md"
  ],
  "testCommand": "git diff --check -- docs/example.md",
  "include_diff": true
}
```

주의:

- `changedFilesOnly`는 Claude prompt에 추가되는 advisory rule이다.
- `CLAUDE_MCP_ALLOWED_WORKDIRS`는 시작 cwd allowlist다.
- `addDirs`도 이 allowlist 안의 경로만 허용된다. 여러 root가 필요하면
  `CLAUDE_MCP_ALLOWED_WORKDIRS`에 comma로 구분한 절대경로를 넣고 Codex를 재시작한다.
- 이 allowlist와 `changedFilesOnly`는 OS filesystem sandbox가 아니다.
- 기계적 격리가 필요하면 별도 git worktree, container 또는 VM을 사용한다.
- `acceptEdits`는 file edit와 일부 filesystem command를 자동 승인하지만 임의 Bash
  test는 permission rule이 없으면 denied될 수 있다.
- 반환된 `changed_files` 전체가 이번 Claude run의 변경이라고 단정하지 않는다.
  `dirty_before`, `new_changed_files`와 실제 diff를 함께 본다.

### 14.4 같은 Claude session 이어가기

첫 반환의 `session_id`를 저장한다.

```text
claude-coder의 claude_continue_thread를 호출해.
session_id는 직전 반환값을 사용하고,
앞서 수정한 내용에서 test 실패 한 건만 고치게 해.
```

argument 예:

```json
{
  "session_id": "<returned-session-id>",
  "prompt": "직전 변경의 test failure만 고쳐. 범위를 넓히지 마.",
  "workingDirectory": "/home/YOU/code/my-project",
  "permissionMode": "acceptEdits",
  "bare": false,
  "write": true
}
```

`task_id`는 같은 MCP server process가 기억하는 run에만 사용할 수 있다. Codex나
supervisor가 재시작될 수 있으므로 durable continuation key로는 Claude
`session_id`를 사용한다.

### 14.5 tool별 완료 의미

| Tool | 완료 시점 |
| --- | --- |
| `claude_health` | `claude --version` 종료 |
| `claude_run_task` | Claude read/review child 종료 |
| `claude_run_write_task` | Claude child 종료 + after git snapshot |
| `claude_continue_thread` | resumed Claude child 종료 |
| `claude_list_runs` | 현재 MCP server process의 memory 반환 |

`claude_list_runs`는 background job polling API가 아니다. `run_id`도 detached job
handle이 아니다.

### 14.6 MCP timeout

public config의 기본값:

- Claude child default: 1,800,000 ms
- Codex MCP `tool_timeout_sec`: 1,860 seconds

MCP client timeout은 Claude child timeout과 SIGTERM/SIGKILL·audit 정리보다 길어야
한다.

더 긴 Claude run을 요청하려면 두 값을 함께 올리고 Codex를 재시작한다. server
timeout만 올리고 `tool_timeout_sec`를 그대로 두면 Claude audit에는 결과가 남아도
Codex caller가 먼저 tool timeout을 받을 수 있다.

---

## 15. Claude permission과 `bare`

### 15.1 안전 기본값

public installer가 쓰는 값:

```text
read task  = permissionMode default
write task = permissionMode acceptEdits
dangerous  = disabled
bare       = disabled
```

Claude permission mode의 의미:

| mode | headless bridge에서의 의미 |
| --- | --- |
| `default` | read-only tool은 가능, 새 approval이 필요한 action은 막힐 수 있음 |
| `plan` | 조사 중심, source edit 금지 |
| `acceptEdits` | in-scope file edit와 일반 file operation 자동 승인 |
| `dontAsk` | allow rule에 없는 승인 요청을 자동 거부 |
| `auto` | 계정·model 조건이 맞을 때 background safety classifier 사용 |
| `bypassPermissions` | 모든 permission check 우회, 격리된 환경 외 사용 금지 |

### 15.2 `bare:true`를 기본 금지하는 이유

현재 OAuth/Max setup에서 Claude Code `--bare`는 저장된 OAuth/keychain login을
사용하지 않고 API key 또는 `apiKeyHelper` 인증을 요구한다.

따라서 MCP 호출에서는:

```json
{
  "bare": false
}
```

로 보내거나 `bare`를 생략한다.

`CLAUDE_MCP_ALLOW_BARE=1`은 API-key/apiKeyHelper 인증을 별도로 구성하고 실제
`claude --bare` smoke를 통과한 환경에서만 사용한다.

---

## 16. supervisor와 crash 처리

`run.sh`는 MCP server를 바로 실행하지 않고 `mcp-stdio-supervisor.mjs` 아래에서
실행한다.

supervisor의 역할:

1. Codex와 연결된 stdio pipe를 유지한다.
2. MCP initialize request와 initialized notification을 기억한다.
3. child MCP server가 crash하면 pending request를 failure로 반환한다.
4. child를 재기동한다.
5. 새 child에 initialize/initialized를 replay한다.
6. 이후 새 요청을 새 child로 전달한다.

중요한 한계:

- crash 당시 실행 중이던 Claude task를 자동 replay하지 않는다.
- 실패한 write task를 자동 replay하면 중복 edit가 생길 수 있으므로 의도적인 제한이다.
- audit와 git diff를 확인한 뒤 새 호출 또는 `claude_continue_thread`를 선택한다.

---

## 17. Codex app-server experimental wake probe

이 절은 안정 MCP 설치가 통과한 뒤에만 진행한다.

### 17.1 사전 확인

```bash
codex app-server --help
node --version
claude --version
codex --version
```

probe는 experimental `process/spawn`을 사용한다. Codex update로 protocol이 바뀌면
실패할 수 있다.

### 17.2 idle wake probe

Claude가 끝날 때 Codex app-server thread가 idle인 경우:

```bash
cd "$PROJECT"

node "$BRIDGE_REPO/bridge/codex-app-server-wake/probe.mjs" \
  --mode idle \
  --workdir "$PROJECT"
```

기본 Claude model은 `haiku`다. 계정에서 unavailable이면:

```bash
node "$BRIDGE_REPO/bridge/codex-app-server-wake/probe.mjs" \
  --mode idle \
  --workdir "$PROJECT" \
  --claude-model sonnet
```

기대 핵심 결과:

```json
{
  "ok": true,
  "mode": "idle",
  "claudeResult": "CLAUDE_BG_BRIDGE_OK",
  "codexMessage": "CODEX_EVENT_WAKE_OK",
  "claudeArrivedWhileActive": false,
  "queuedClaude": false,
  "stage": "complete",
  "turnStatus": "completed"
}
```

### 17.3 busy queue probe

Claude가 끝날 때 Codex turn이 이미 `sleep 12`를 수행 중인 경우:

```bash
cd "$PROJECT"

node "$BRIDGE_REPO/bridge/codex-app-server-wake/probe.mjs" \
  --mode busy \
  --workdir "$PROJECT"
```

기대 핵심 결과:

```json
{
  "ok": true,
  "mode": "busy",
  "claudeResult": "CLAUDE_BG_BRIDGE_OK",
  "firstTurnMessage": "FIRST_TURN_DONE",
  "codexMessage": "CODEX_EVENT_WAKE_OK",
  "claudeArrivedWhileActive": true,
  "queuedClaude": false,
  "stage": "complete",
  "turnStatus": "completed"
}
```

의미:

1. Claude result가 첫 Codex turn 중 도착했다.
2. probe는 현재 turn을 끊지 않고 memory queue에 보관했다.
3. 첫 turn이 끝난 뒤 두 번째 `turn/start`로 Claude 결과를 전달했다.
4. 같은 result는 한 번만 전달됐다.

### 17.4 이 probe가 운영 controller가 아닌 이유

현재 source는 재현 가능한 E2E probe다. 다음 기능은 없다.

- controller restart 뒤 pending queue 복구
- disk/DB durable queue
- 여러 thread와 여러 Claude job 동시 관리
- secret redaction policy
- permission request를 사용자에게 전달하는 UI
- explicit `turn/steer` failure fallback E2E
- target thread archive/delete recovery
- delivery ledger와 retention 관리

따라서 production daemon처럼 상시 실행하지 않는다.

---

## 18. Codex가 이미 작업 중일 때의 운영 정책

persistent controller를 만들 때 기본 정책은 `queue-until-idle`이다.

```text
Claude result arrives
├─ target Codex thread is idle
│  └─ turn/start(result)
└─ target Codex thread is active
   ├─ pending queue에 저장
   └─ turn/completed 또는 thread/status/changed=idle
      └─ turn/start(result)
```

`turn/steer`는 현재 turn의 방향을 즉시 바꿔야 할 때만 사용한다.

steer를 쓰려면:

- target `thread_id`가 맞아야 한다.
- 현재 `active_turn_id`를 알아야 한다.
- `expectedTurnId`가 일치해야 한다.
- review, compact 등 steer 불가 상태를 처리해야 한다.
- steer 실패 시 queue로 되돌려야 한다.

queue item 최소 필드:

```json
{
  "job_id": "claude-job-001",
  "thread_id": "target-codex-thread",
  "launched_from_turn_id": "codex-turn-that-started-claude",
  "delivery_mode": "after_idle",
  "result": "Claude final response",
  "delivered_at": null
}
```

같은 `job_id`를 두 번 전달하지 않는다. target thread가 사라졌을 때 임의의 새
thread에 결과를 넣지 않는다.

---

## 19. 로그와 민감 데이터

기본 state directory:

```text
$HOME/.local/state/claude-codex-bridge/
├─ claude-mcp-runs.jsonl
├─ claude-mcp-lifecycle.jsonl
└─ mcp-supervisor-claude-coder-lifecycle.jsonl
```

Claude → Codex skill의 prompt/result/events는 기본적으로
`/tmp/claude-codex-bridge/`에 생긴다.

로그에는 다음이 들어갈 수 있다.

- prompt 일부 또는 final response
- stdout/stderr
- 작업 directory
- changed file 이름
- Claude session ID
- model usage
- failure message

금지:

- OAuth token
- API key
- password
- private key
- `~/.codex/auth.json`
- Claude credential file
- `.env` 내용

state directory 권한 확인:

```bash
chmod 700 "$HOME/.local/state/claude-codex-bridge"
stat -c '%a %n' "$HOME/.local/state/claude-codex-bridge"
```

필요한 retention 기간을 정하고 오래된 audit를 사용자가 직접 삭제한다. public
source는 credential을 저장하거나 배포하지 않는다.

---

## 20. 증상별 문제 해결

### 20.1 `claude-coder` tool이 Codex에 보이지 않는다

확인:

```bash
codex mcp get claude-coder
codex mcp list
rg -n 'claude-coder' "$HOME/.codex/config.toml"
```

해결 순서:

1. TOML table 이름과 중복을 확인한다.
2. `command` 절대경로가 존재하고 executable인지 확인한다.
3. 실행 중인 모든 Codex process를 닫는다.
4. 새 WSL terminal에서 Codex를 다시 시작한다.
5. IDE extension이면 extension도 restart한다.

### 20.2 MCP startup timeout

```bash
test -x "$BRIDGE_REPO/bridge/claude-coder-mcp/run.sh"
bash -n "$BRIDGE_REPO/bridge/claude-coder-mcp/run.sh"
node --check "$BRIDGE_REPO/bridge/claude-coder-mcp/server.mjs"

cd "$PROJECT"
node "$BRIDGE_REPO/bridge/claude-coder-mcp/smoke.mjs"
```

health smoke도 실패하면 Codex 문제가 아니라 bridge process 자체 문제다. 출력의
`stage`와 `stderr`를 본다.

### 20.3 `node executable not found`

```bash
command -v node
node --version
rg -n 'NODE_BIN|PATH' "$HOME/.codex/config.toml"
```

`NODE_BIN`을 실제 absolute path로 수정한다. nvm version을 바꾼 뒤 old version
path를 config에 남겨두지 않는다.

### 20.4 `claude executable not found` 또는 `spawn ... ENOENT`

```bash
command -v claude
claude --version
rg -n 'CLAUDE_BIN|PATH' "$HOME/.codex/config.toml"
```

native installer라면 보통 `$HOME/.local/bin/claude`다. 실제 `command -v` 결과로
TOML을 수정하고 Codex를 재시작한다.

### 20.5 Claude authentication failure

같은 WSL 사용자와 같은 HOME에서 확인한다.

```bash
printf 'HOME=%s\n' "$HOME"
claude auth status --json
claude
```

interactive `claude` login이 성공한 뒤 MCP live smoke를 다시 실행한다. credential을
다른 사용자 HOME에서 복사하지 않는다.

### 20.6 `bare:true is disabled`

MCP 호출에서 `bare`를 빼거나 `false`로 바꾼다. OAuth/Max 로그인만 사용하는
환경에서 `CLAUDE_MCP_ALLOW_BARE=1`로 억지로 열지 않는다.

### 20.7 Claude read task가 file은 읽지만 Bash에서 막힌다

`default` permission mode에서 Read/Grep은 가능하지만 승인 필요한 Bash는 headless
session에서 막힐 수 있다.

해결 선택지:

1. prompt를 Read/Grep 중심으로 바꾼다.
2. 필요한 tool만 `allowedTools`로 사전 허용한다.
3. 조사 task에 `plan` mode를 사용한다.
4. locked-down automation은 `dontAsk`와 명시적 allow rule을 함께 사용한다.
5. `bypassPermissions`는 container/VM 같은 격리 환경에서만 사용한다.

### 20.8 write task가 edit 뒤 test를 못 돌린다

`acceptEdits`는 file edit를 허용하지만 임의 Bash command를 모두 허용하지 않는다.

- edit 결과는 반환될 수 있다.
- test는 permission denial로 실행되지 않을 수 있다.
- Codex main이 test를 별도로 실행하거나 필요한 Bash allow rule을 설정한다.
- `permission_denials`와 `final_response`를 확인한다.

### 20.9 MCP tool timeout

```bash
codex mcp get claude-coder
rg -n 'tool_timeout_sec|CLAUDE_MCP_.*WAIT|WRITE_TIMEOUT' \
  "$HOME/.codex/config.toml"
```

`tool_timeout_sec`가 child timeout보다 짧지 않게 한다. 수정한 뒤 Codex를 재시작한다.

### 20.10 TOML parse error

주요 원인:

- 같은 `[mcp_servers.claude-coder]` table 중복
- quote 누락
- Windows path의 backslash escape
- `~`나 `$HOME`가 자동 확장된다고 가정
- angle bracket placeholder를 그대로 둠

`examples/codex-config.toml`과 한 줄씩 대조한다.

### 20.11 `/codex-bg` skill이 Claude에서 안 보인다

```bash
test -f "$PROJECT/.claude/skills/codex-bg/SKILL.md" ||
test -f "$HOME/.claude/skills/codex-bg/SKILL.md"

sed -n '1,30p' "$PROJECT/.claude/skills/codex-bg/SKILL.md"
```

skill을 설치한 뒤 기존 Claude session을 닫고 `PROJECT`에서 새 session을 시작한다.

### 20.12 Codex는 끝났는데 Claude main이 안 깨어난다

아래를 확인한다.

- top-level Claude main이 직접 Bash tool을 호출했는가
- Bash tool의 실제 옵션이 `run_in_background=true`였는가
- shell 안의 `&`만 사용한 것은 아닌가
- Claude background sub-agent가 Codex를 시작한 것은 아닌가
- Claude main session 자체를 사용자가 종료하지 않았는가
- result/events file이 생성됐는가

```bash
ls -lah /tmp/claude-codex-bridge
tail -n 100 /tmp/claude-codex-bridge/<slug>.events.jsonl
```

result가 정상인데 wake만 없으면 Codex 문제가 아니라 Claude Code harness 또는
호출 계층 문제다.

### 20.13 `codex exec`가 model unavailable로 실패한다

public skill은 model을 고정하지 않는다. 직접 명령에 `--model`을 넣었다면 우선
제거하고 로그인 계정의 default를 사용한다.

### 20.14 WSL과 Windows binary가 섞였다

```bash
command -v node claude codex
file "$(command -v node)"
file "$(command -v claude)"
file "$(command -v codex)"
printf 'WSL_DISTRO_NAME=%s\n' "$WSL_DISTRO_NAME"
```

Windows npm global path나 `.exe`가 먼저 나오면 WSL PATH를 수정한다.

### 20.15 repository가 `/mnt/c` 아래라 느리다

```bash
mkdir -p "$HOME/code"
cd "$HOME/code"
git clone <YOUR_PROJECT_GIT_URL> my-project
```

WSL Linux filesystem으로 옮기고 installer의 `--project`와 Codex config workdir을
새 절대경로로 다시 맞춘다.

### 20.16 app-server probe에서 `process/spawn` unknown method

```bash
codex --version
codex app-server --help
```

현재 Codex CLI가 experimental process API를 포함하는지 확인한다. CLI를 update한
경우 protocol 변경 가능성이 있으므로 probe source와 official app-server 문서를
대조한다. 기존 TUI에서 이 method를 직접 호출하려 하지 않는다.

### 20.17 busy probe가 `first-turn-completed-before-claude`로 실패한다

첫 Codex turn이 Claude보다 먼저 끝났다는 뜻이다. PC나 model 속도에 따라 race가
날 수 있다.

probe의 first turn sleep을 늘리거나 Claude model을 더 빠른 것으로 바꾼 뒤 다시
실행한다. 이것은 queue logic 실패가 아니라 test timing 실패일 수 있다.

### 20.18 dirty worktree에서 변경 귀속이 불분명하다

```bash
cd "$PROJECT"
git status --short
git diff --stat
git diff
```

MCP 반환의 `dirty_before`와 `new_changed_files`를 확인한다. 다른 session의 기존
변경을 Claude run 결과로 보고하거나 되돌리지 않는다.

---

## 21. update 절차

### 21.1 public bridge source update

```bash
cd "$BRIDGE_REPO"
git status --short
git pull --ff-only

node bridge/claude-coder-mcp/smoke.mjs
node bridge/claude-coder-mcp/smoke.mjs --live --model haiku
```

source path가 그대로면 Codex TOML을 다시 추가할 필요는 없다. source directory를
옮겼다면 `command`를 새 절대경로로 바꾸고 Codex를 재시작한다.

### 21.2 Claude Code update

native install:

```bash
claude update
claude --version
claude doctor
```

update 뒤 MCP live smoke를 다시 실행한다.

### 21.3 Codex update

설치 방식에 맞게 Codex를 update한 뒤:

```bash
codex --version
codex login status
codex mcp get claude-coder

node "$BRIDGE_REPO/bridge/claude-coder-mcp/smoke.mjs"
node "$BRIDGE_REPO/bridge/codex-app-server-wake/probe.mjs" \
  --mode idle \
  --workdir "$PROJECT"
node "$BRIDGE_REPO/bridge/codex-app-server-wake/probe.mjs" \
  --mode busy \
  --workdir "$PROJECT"
```

---

## 22. 제거와 rollback

### 22.1 Claude skill 제거

project scope:

```bash
rm -rf "$PROJECT/.claude/skills/codex-bg"
```

user scope:

```bash
rm -rf "$HOME/.claude/skills/codex-bg"
```

### 22.2 MCP 제거

```bash
codex mcp remove claude-coder
codex mcp list
```

installer가 만든 config backup은 `$HOME/.codex/config.toml.bak.<timestamp>`
모양이다. 전체 config를 backup으로 되돌리기 전에 이후 추가된 다른 설정이 없는지
diff한다.

### 22.3 local state 제거

audit가 더 필요 없는지 확인한 뒤에만:

```bash
rm -rf "$HOME/.local/state/claude-codex-bridge"
```

### 22.4 public clone 제거

Codex config에서 `claude-coder`를 먼저 제거한 뒤 clone을 삭제한다. config가
`run.sh`를 가리키는 상태에서 clone만 지우면 Codex 시작 때 MCP가 실패한다.

---

## 23. 이 저장소에서 2026-07-14에 다시 실행한 검증

### 23.1 source와 installer

통과:

- Node syntax: MCP server, supervisor, lifecycle audit, smoke, app-server probe
- Bash syntax: `install.sh`, MCP `run.sh`
- installer dry-run
- 임시 HOME에서 installer 실제 실행
- 생성된 Codex config permission `600`
- 별도 `CODEX_HOME`에서 `codex mcp get claude-coder` config parse
- project-scoped `/codex-bg` skill 복사
- MCP initialize와 tool list
- `claude_health`

### 23.2 Codex → Claude live smoke

실제 결과:

```text
status=completed
exit_code=0
timed_out=false
final_response=CLAUDE_CODER_MCP_OK
```

이 결과는 public portable source가 현재 WSL Claude login으로 실제 Claude child를
실행하고 같은 MCP call에 결과를 반환했음을 뜻한다.

### 23.3 app-server idle probe

실제 결과:

```text
ok=true
mode=idle
claudeResult=CLAUDE_BG_BRIDGE_OK
codexMessage=CODEX_EVENT_WAKE_OK
turnStatus=completed
```

### 23.4 app-server busy probe

실제 결과:

```text
ok=true
mode=busy
firstTurnMessage=FIRST_TURN_DONE
claudeArrivedWhileActive=true
codexMessage=CODEX_EVENT_WAKE_OK
queuedClaude=false
turnStatus=completed
```

### 23.5 Claude → Codex wake

이 방향의 완료 계약은 top-level Claude Code Bash background job 종료 notification이다.
이 README의 13.1절과 같은 read-only `codex exec`를 다시 실행해 exit code 0과
`CODEX_EXEC_OK` result file을 확인했다. 기존 Claude Code 환경에서는 top-level
background job의 Claude main completion wake도 확인했다. 다만 이 README를 갱신한
session 자체는 Claude main harness가 아니므로 이번 Codex turn에서 해당 UI wake까지
재실행했다고 주장하지 않는다. 새 설치자는 13.2절의 smoke로 자기 Claude Code
client에서 마지막 wake를 확인해야 한다.

---

## 24. 현재 보장 범위와 남은 한계

### 안정 운영 경로

- Claude main → Codex: `/codex-bg` + tracked Bash background job
- Codex main → Claude: `claude-coder` synchronous MCP call
- MCP child crash 뒤 새 요청을 위한 supervisor restart
- read/write/resume tool과 git before/after evidence
- OAuth/Max 환경에서 `bare:false`

### experimental

- app-server `process/spawn`
- `process/exited` 뒤 `turn/start`
- active turn 중 memory queue 후 idle delivery

### 아직 제공하지 않는 것

- 기존 Codex TUI session을 외부 process가 임의로 깨우는 기능
- app-server durable production controller
- controller restart 뒤 queue recovery
- 여러 PC에 걸친 distributed queue
- permission approval UI relay
- credential 배포
- prompt에 적힌 file 목록을 강제하는 OS sandbox
- 모든 Claude/Codex release에 대한 미래 호환성 보장

---

## 25. 공식 참고 문서

- [Claude Code advanced setup](https://code.claude.com/docs/en/setup)
- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes)
- [Claude Code permissions](https://code.claude.com/docs/en/permissions)
- [OpenAI Codex CLI](https://developers.openai.com/codex/cli/)
- [OpenAI Codex MCP](https://developers.openai.com/codex/mcp/)
- [OpenAI Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- [OpenAI Codex app-server](https://learn.chatgpt.com/docs/app-server)
- [OpenAI Codex WSL guide](https://learn.chatgpt.com/docs/windows/wsl)
- [VS Code Remote development in WSL](https://code.visualstudio.com/docs/remote/wsl-tutorial)
- [OpenAI Codex source repository](https://github.com/openai/codex)

---

## 26. 설치 완료 판정표

아래를 모두 확인해야 설치 완료다.

- [ ] VS Code window와 terminal이 WSL2 안에 있다.
- [ ] repository가 WSL Linux filesystem에 있다.
- [ ] `node`, `claude`, `codex`가 같은 WSL user PATH에 있다.
- [ ] Claude interactive login이 된다.
- [ ] `codex login status`가 성공한다.
- [ ] public clone을 삭제하지 않을 위치에 두었다.
- [ ] `install.sh --dry-run`의 모든 절대경로를 확인했다.
- [ ] `codex mcp get claude-coder`가 enabled stdio server를 보여준다.
- [ ] MCP health smoke가 다섯 tool을 보여준다.
- [ ] MCP live smoke가 `CLAUDE_CODER_MCP_OK`를 반환한다.
- [ ] 새 Claude session에서 `/codex-bg` skill이 발견된다.
- [ ] Claude top-level main의 read-only `/codex-bg`가 result file을 만든다.
- [ ] 그 background job 종료 뒤 Claude main이 completion event를 받는다.
- [ ] write mode 전에 dirty worktree와 sandbox를 확인한다.
- [ ] app-server가 필요하면 idle probe를 통과한다.
- [ ] busy delivery가 필요하면 busy probe도 통과한다.
- [ ] credential과 audit log가 git에 들어가지 않는다.

이 판정표 중 MCP live smoke와 `/codex-bg` wake가 통과하면 일상 양방향 사용이
가능하다. app-server 항목은 detached Claude 완료 뒤 Codex가 새 turn을 시작해야 하는
별도 experimental 요구가 있을 때만 필요하다.
