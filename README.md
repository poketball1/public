# Claude ↔ Codex CLI 호출 인프라 설치·운영 매뉴얼

이 공개 저장소는 Claude Code와 Codex CLI를 같은 WSL 개발환경에서 함께 쓰기 위한
Claude skill, Codex CLI foreground helper, reverse-direction MCP server와 검증
도구를 제공한다. 아래 호출 실행기는 AIR 내부 저장소의 private orchestration·session
delivery·운영 controller를 포함하지 않는다. AIR 전용 경로를 이 저장소의 설치
전제나 보장 범위로 해석하지 않는다.

## 2026-09-15 갱신 — 위임 스택 글

현행 좌석 지도·위임 판별선·Luna 직원·falsifier·closure 는 [`delegation-stack.md`](delegation-stack.md) 가 현행이다.
그 글이 인용한 원문은 [`source-material/2026-09-15/`](source-material/2026-09-15/) 에 파일로 있다 (AIR repo `84e63c231` 기준).
2026-07 의 사장모드 글(`fable-boss-mode.md`)과 그 원문 사본은 전제가 은퇴해 삭제했다 — 유효한 조각은 위 글 §8 에 흡수, 원문은 git history.
아래 설치·실행 매뉴얼과 [`skills/codex-bg/`](skills/codex-bg/)는 2026-09-15 공개판으로 갱신했다.
`source-material/2026-09-15/skills-codex-bg/`는 AIR 내부 wrapper용 원문 snapshot이며,
공개판 helper와 호출 옵션·wake 계약이 다르다. 공개 설치에서는 아래 §10·§13을 따른다.

이 README의 목표는 개념 소개가 아니다. 새 PC에서 아래 순서대로 실행하면 다음 두
운영 경로를 재현할 수 있다.

1. Claude main → Codex worker: `/codex-bg`가 `skills/codex-bg/scripts/run.mjs`를
   foreground로 실행한다. Claude Code의 top-level Bash tool만 이 명령을
   `run_in_background=true`로 추적한다. helper는 매 실행마다 새 artifact directory를
   만들고 Codex transport 결과를 기록한다.
2. Codex main → Claude worker: `claude-coder` stdio MCP tool call이 Claude child가
   끝날 때까지 기다리고, 결과를 같은 Codex turn에 동기로 반환한다.

첫 번째 경로의 helper는 daemon, systemd service, session-delivery controller,
notification sender가 아니다. Claude Code session이 끝나면 tracked background job도
정리될 수 있으며, 그 뒤 helper가 살아 있거나 Claude main이 깨어난다고 보장하지
않는다. 진행 중인 tracked Bash job은 Claude Code의 TaskStop으로 취소한다.

추가로 Codex app-server가 관리하는 thread에서 Claude background process의 완료
event로 Codex turn을 새로 시작하는 experimental wake probe도 제공한다. 이것은
기존 Codex TUI를 임의로 깨우는 기능이 아니며 안정 운영 기본값도 아니다.


> **이 저장소의 다른 매뉴얼** — [`keepwarm/`](keepwarm/README.md): Claude Code 프롬프트 캐시
> keep-warm 을 측정(transcript 에서 캐시 히트/미히트 읽기)부터 자동화(idle 50분 자동 턴 주입
> daemon·hook·relay)까지 제3자가 따라 만들 수 있게 적은 재현 가이드. 실행 가능한 스크립트 동봉.

---

## 1. 작성·검증 기준

| 항목 | 이 문서의 실측 기준 |
| --- | --- |
| 현재 문서 범위 | 2026-09-15, Asia/Seoul — Claude → Codex helper와 installer 문서 갱신 |
| 현재 CLI 확인 | Codex CLI `0.154.0` — 2026-09-15 current scope; helper 실행 결과는 §23 |

2026-07-14 historical snapshot:

| 항목 | 당시 실측 기준 |
| --- | --- |
| 갱신일 | 2026-07-14, Asia/Seoul |
| Windows editor | VS Code `1.128.0` |
| terminal/runtime | WSL2, Debian GNU/Linux 13 |
| Claude Code | `2.1.198` |
| Codex CLI | `0.144.1` |
| bridge Node.js | `20.18.0` |
| 작성 모델 | `gpt-5.6-sol` |
| 공개 저장소 | [poketball1/public](https://github.com/poketball1/public) |

위 표는 당시 재현한 snapshot이다. 영구 최소 버전이라는 뜻은 아니다. 2026-09-15
갱신에서는 Codex CLI `0.154.0` 확인 범위만 현재 값으로 다룬다. Claude Code 버전,
bridge runtime, `claude-coder` live smoke와 app-server probe에 대한 아래의 기존
결과는 모두 2026-07-14 historical evidence로 유지하며 이번 갱신에서 재실행했다고
주장하지 않는다.

Codex `0.115`부터 Linux sandbox가 bubblewrap 기반으로 바뀌어 WSL1은 지원되지
않는다. Windows에서 이 매뉴얼을 사용할 때는 WSL2를 사용한다.

---

## 2. 사용자 요약

- 이 구성은 Claude와 Codex를 서로의 sub-agent처럼 활용하는 CLI 인프라다.
- main agent는 작업을 나누고 상대 agent에게 조사·구현·검증을 맡긴다.
- Claude main에서 Codex를 부를 때는 `/codex-bg` skill과 portable foreground helper를 사용한다.
- helper는 `codex exec --json`의 stdout JSONL을 `events.jsonl`에, stderr를 별도
  `stderr.log`에 남긴다. `result.md`와 `status.json`으로 마지막 transport 상태를
  읽을 수 있다.
- Claude Code top-level main이 Bash tool을 `run_in_background=true`로 호출할 때만
  job tracking과 작업 중 대기가 가능하다. helper가 Claude session 밖에서 계속
  살아 있거나 session 종료 뒤 main을 깨운다고 보장하지 않는다.
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

helper의 `completed`는 Codex transport turn이 끝났다는 뜻이며, 작업 목표가
수용됐거나 테스트가 통과했다는 뜻이 아니다. 최종 판단은 Claude main이 result,
status, diff와 필요한 검증을 직접 읽고 내린다.

아래 세 절은 이 요약의 정확한 완료·wake 계약이다.

### 2.1 Claude main → Codex

`/codex-bg` skill은 Claude main이 Claude Code의 Bash tool을
`run_in_background=true`로 호출해 `skills/codex-bg/scripts/run.mjs`를 실행하게 한다.

```text
Claude main
  └─ Claude Code Bash tool: run_in_background=true
      └─ node skills/codex-bg/scripts/run.mjs run ...
          ├─ result.md
          ├─ events.jsonl (Codex stdout only)
          ├─ stderr.log
          └─ status.json

Codex transport turn ends
  └─ helper writes terminal status and exits foreground
      └─ Claude Code harness observes tracked background job completion
          └─ top-level Claude main may inspect the artifact directory
```

중요한 조건:

- top-level Claude main이 직접 helper를 background Bash job으로 시작해야 한다.
- shell 명령 끝에 단순히 `&`나 `nohup`를 붙이는 것과 같지 않다.
- Claude background sub-agent에게 `/codex-bg`를 다시 시키지 않는다.
- Codex transport가 끝났다는 사실과 Claude main이 최종 완료를 판정하는 것은 별개다.
- 이 방향에는 별도 polling daemon·systemd·session-delivery·notify controller가 없다.
- Claude Code session이 끝나면 tracked job이 정리될 수 있다. session 종료 뒤 result
  전달이나 Claude main wake를 보장하지 않는다.

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

## 3. 저장소의 주요 파일

```text
public/
├─ README.md
├─ delegation-stack.md
├─ keepwarm/
│  ├─ README.md
│  └─ scripts/
├─ install.sh
├─ source-material/
│  └─ 2026-09-15/
├─ tests/
│  └─ install.test.mjs
├─ examples/
│  └─ codex-config.toml
├─ skills/
│  └─ codex-bg/
│     ├─ SKILL.md
│     └─ scripts/
│        ├─ run.mjs
│        └─ run.test.mjs
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
| `install.sh` | 기본 설치는 skill과 reverse MCP를 설치하고, `--only codex-bg`는 skill runtime만 복사 |
| `skills/codex-bg/SKILL.md` | Claude main → Codex helper 호출 계약 |
| `skills/codex-bg/scripts/run.mjs` | Node 20 built-in만 사용하는 foreground `health`, `run`, `resume`, `status` CLI |
| `delegation-stack.md` | 사장·직원·감리 운영 규칙과 자기 환경으로의 이식 지침 |
| `skills/codex-bg/scripts/run.test.mjs`, `tests/install.test.mjs` | 모델 호출 없이 실행·실패·설치 보존을 검증하는 Node 테스트 |
| `source-material/2026-09-15/` | AIR 위임 스택 원문 snapshot. 공개 helper의 설치용 runtime과 구분 |
| `keepwarm/` | 별도의 Claude prompt cache keep-warm 재현 가이드와 스크립트 |
| `bridge/claude-coder-mcp/server.mjs` | Codex에 Claude read/write/resume tool 제공 |
| `bridge/claude-coder-mcp/run.sh` | Node·Claude 경로 확인, state dir 준비, supervisor 시작 |
| `bridge/mcp-stdio-supervisor.mjs` | MCP child crash 뒤 다음 요청을 위한 재기동 |
| `bridge/claude-coder-mcp/smoke.mjs` | MCP initialize, tool list, health, 실제 Claude 응답 검증 |
| `examples/codex-config.toml` | 수동 설치용 전체 TOML 예제 |
| `bridge/codex-app-server-wake/probe.mjs` | idle/busy event-driven wake 실증 |

public판에는 credential 파일이 없다. 현재 WSL 사용자가 각 CLI에 직접 로그인한
상태를 사용한다. `--only codex-bg` 설치는 reverse MCP, Codex TOML, Claude CLI
검사를 건드리지 않고 skill runtime(`SKILL.md`와 `scripts/run.mjs`)만 다룬다.

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
sudo apt install -y git curl ca-certificates python3 util-linux
```

기본 양방향 installer는 기존·생성 예정 Codex TOML을 write 전에 검사하므로
Python 3.11 이상과 표준 library `tomllib`가 필요하다. Debian GNU/Linux 13의
`apt` `python3`가 이 조건을 충족한다. 별도 pip package는 설치하지 않는다.
실제 파일을 쓰는 installer는 Linux/WSL `util-linux`의 `flock`으로 설치를 직렬화한다.
`--only codex-bg`는 Python이나 Claude executable 없이 Node.js와 Codex CLI만 사용하고,
Codex config를 읽거나 변경하지 않는다. dry-run은 파일을 쓰지 않는다.

### 6.2 Node.js가 왜 필요한가

Claude native installer와 Codex native installer 자체는 Node.js를 요구하지 않는다.
하지만 이 저장소의 `skills/codex-bg/scripts/run.mjs` helper와 `claude-coder` MCP
server, supervisor, smoke test, app-server probe는 `.mjs` 파일이므로 Node.js가
필요하다. helper와 bridge는 Node built-in만 사용하며 npm package를 설치하지 않는다.
실행 기준은 Node.js 20 이상이다.

Node를 설치하지 않으면 이 저장소의 helper와 bridge는 실행할 수 없다. CLI를 직접
호출하는 별도 수동 경로는 이 skill의 artifact·resume 계약에 포함되지 않는다.

이 README에 포함된 helper, MCP server와 app-server probe까지 사용하려면 Node.js
20 이상을 설치한다.

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

기대값은 `node --version`이 `v20.x` 이상인 것이다. `run.mjs`는 npm install이나
외부 Node dependency를 사용하지 않는다.

Claude Code를 npm으로 설치하는 방법도 있지만 2026-07-14 historical snapshot의
Claude Code `2.1.198` npm package는 Node.js 22 이상을 요구했다. 이 문서에서는
혼동을 피하기 위해 Claude와 Codex는 각각 공식 native installer로 설치하고, Node
20 이상은 helper·bridge runtime으로 사용한다.

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

설치 방식이나 release가 달라 당시 historical snapshot의 `0.144.1`보다 새 버전이
설치돼도 된다. 현재 갱신에서 확인한 CLI는 `0.154.0`이며, app-server probe는
2026-07-14 historical evidence로만 남겨 두었다. CLI update 뒤 probe를 새로
실행하려면 §23 계획을 따르고 결과를 별도로 기록한다.

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

installer의 기본 모드는 양방향 구성 전체를 설치한다.

전체 설치의 Codex config 파일은 skill runtime·state·설치 잠금 디렉터리와 겹칠 수 없다.
그 디렉터리 안의 파일이나 디렉터리 자체·상위 경로를 config로 지정하면 쓰기 전에 거절한다.
실행기나 audit 로그가 설정을 덮어쓰는 경로 충돌을 막는 경계다. `/tmp/config.toml`처럼
일반 상위 경로만 공유하는 경우는 허용한다. `--only codex-bg`에는 이 config 검사를 적용하지 않는다.

1. `skills/codex-bg/`의 전체 runtime인 `SKILL.md`와 `scripts/run.mjs`를 project
   또는 user skill directory로 복사한다. `*.test.*`·`*.spec.*` 테스트 asset은
   runtime 복사 대상이 아니다.
2. 실제 설치에서는 `flock` 아래에서 기존 Codex config를 다시 확인하고 timestamp
   backup한다.
3. `claude-coder` MCP table을 Codex config에 추가한다.
4. reverse MCP Node source 구문을 검사한다.

Claude → Codex helper만 설치하거나 업데이트할 때는 `--only codex-bg`를 사용한다.
이 mode는 skill runtime 전체를 복사하고(테스트 asset 제외), 기존 skill의 바뀌는 asset은 timestamp
backup한 뒤 교체한다. MCP table이나 Codex config를 변경하지 않으며 Claude executable에는
의존하지 않는다. installer 자체는 skill source syntax 확인을
위해 Node.js와 Codex CLI 경로를 요구하며, helper 실행에도 Node.js 20 이상이 필요하다.

installer가 하지 않는 일:

- WSL, VS Code, Node, Claude 또는 Codex 설치
- Claude/Codex 로그인
- `--only codex-bg`에서 MCP table 추가나 Codex config 수정
- 기존 `claude-coder` table 덮어쓰기
- dangerous permission 활성화
- app-server controller 상시 실행

installer mode별 prerequisite:

| mode | 필요한 것 |
| --- | --- |
| 기본 전체 설치 | Node.js 20 이상, Codex CLI, Claude Code, Python 3.11 이상 표준 library `tomllib`, 실제 write 시 `flock` |
| `--only codex-bg` | Node.js 20 이상, Codex CLI, 실제 skill write 시 `flock`; Python·Claude executable 불필요, Codex config/MCP table을 읽거나 변경하지 않음 |

먼저 dry-run한다.

```bash
cd "$BRIDGE_REPO"

./install.sh \
  --project "$PROJECT" \
  --dry-run
```

helper만 설치할 때의 dry-run과 실제 설치:

```bash
./install.sh \
  --only codex-bg \
  --project "$PROJECT" \
  --dry-run

./install.sh \
  --only codex-bg \
  --project "$PROJECT"
```

`--only codex-bg` dry-run의 변경 계획은 skill runtime 설치로 한정된다. 실제 설치에서
기존 skill asset이 바뀌면 timestamp backup 경로가 출력된다.
Codex config나 `claude-coder` MCP table을 읽거나 변경하지 않으며 Claude executable
검사를 설치 대상에 포함하지 않는다.
`--dry-run`은 skill·config를 쓰지 않고 계획만 출력한다.

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
| Claude skill runtime | `$PROJECT/.claude/skills/codex-bg/{SKILL.md,scripts/run.mjs}` |
| Codex config | `$CODEX_HOME/config.toml` (`CODEX_HOME` 설정 시), 아니면 `$HOME/.codex/config.toml` |
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

이 중복 거부 동작은 기본 전체 설치에만 적용된다. `--only codex-bg`는 MCP/config를
만지지 않으므로 기존 MCP table의 존재와 무관하게 skill runtime만 설치·업데이트한다.

helper의 설치 후 health, 새 run, 상태·artifact 확인, 명시적 thread resume과 lifecycle
경계는 §13에서만 설명한다.

---

## 11. 수동 설치

installer를 쓰지 않는 경우 이 절을 그대로 따른다. reverse MCP를 쓰지 않고
Claude → Codex helper만 필요하면 11.1과 11.2만 진행해도 된다.

### 11.1 `/codex-bg` skill 복사

project 하나에서만 사용:

```bash
mkdir -p "$PROJECT/.claude/skills/codex-bg/scripts"
cp --backup=numbered "$BRIDGE_REPO/skills/codex-bg/SKILL.md" \
  "$PROJECT/.claude/skills/codex-bg/SKILL.md"
cp --backup=numbered "$BRIDGE_REPO/skills/codex-bg/scripts/run.mjs" \
  "$PROJECT/.claude/skills/codex-bg/scripts/run.mjs"
```

모든 project에서 사용:

```bash
mkdir -p "$HOME/.claude/skills/codex-bg/scripts"
cp --backup=numbered "$BRIDGE_REPO/skills/codex-bg/SKILL.md" \
  "$HOME/.claude/skills/codex-bg/SKILL.md"
cp --backup=numbered "$BRIDGE_REPO/skills/codex-bg/scripts/run.mjs" \
  "$HOME/.claude/skills/codex-bg/scripts/run.mjs"
```

`SKILL.md`만 복사하면 helper가 없어 실행할 수 없다. `skills/codex-bg/` 아래의
`SKILL.md`와 `scripts/run.mjs`를 한 묶음으로 복사한다. 위 명령은 기존 파일을 같은
디렉터리의 번호가 붙은 backup으로 보존한다. 수동 복사는 installer의 경로 검사와
동시 설치 잠금을 제공하지 않으므로, 대상이 일반 디렉터리인지 확인하고 단독으로 실행한다.

사장모드 운영 규칙은 [위임 스택 §8](delegation-stack.md#8-자기-환경에-옮기기)의
이식 지침을 따른다. 별도 `skills/boss-mode/SKILL.md`는 폐기됐으며 installer도 설치하지 않는다.
`source-material/2026-09-15/`의 AIR 원문은 환경 치환 없이 설치하는 공개 skill이 아니다.

### 11.2 권한과 source availability

`run.mjs`는 `node`로 호출하므로 executable bit가 필요하지 않다. helper-only 수동
설치에서는 reverse MCP 파일에 `chmod`를 적용할 필요가 없다. reverse MCP를 함께
수동 설치하는 경우에만 기존 source의 실행 권한을 확인한다.
아래 검사는 project scope 기준이다. user scope로 복사했다면 첫 줄을
`SKILL_DIR="$HOME/.claude/skills/codex-bg"`로 바꾼다.

```bash
SKILL_DIR="$PROJECT/.claude/skills/codex-bg"
test -f "$SKILL_DIR/SKILL.md"
test -f "$SKILL_DIR/scripts/run.mjs"
node --version
```

reverse MCP를 사용할 때만:

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

node --check skills/codex-bg/scripts/run.mjs
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

### 13.1 helper와 Codex CLI health

skill은 session 시작 시 발견되는 것이 가장 확실하다. skill runtime을 설치한 뒤
실행 중이던 Claude session을 닫고 새로 시작한다.

```bash
cd "$PROJECT"
claude
```

설치된 skill 경로를 확인하고 health를 호출한다. 이 단계는 모델 turn을 만들지 않는다.
project scope는 아래 `SKILL_DIR`을 사용한다. `--skill-scope user`로 설치했다면
첫 줄을 `SKILL_DIR="$HOME/.claude/skills/codex-bg"`로 바꾼다. 이후 사용법의 `RUNNER`도
이 경로를 그대로 사용한다.

```bash
SKILL_DIR="$PROJECT/.claude/skills/codex-bg"
RUNNER="$SKILL_DIR/scripts/run.mjs"

test -f "$RUNNER"
node --version
node "$RUNNER" health
```

health가 실패하면 `/codex-bg` lifecycle 문제가 아니다. 먼저 Node PATH, Codex
설치·로그인, helper 경로를 확인한다.

### 13.2 새 run: Claude top-level main의 tracked Bash

Claude에게 다음처럼 요청한다.

```text
/codex-bg를 사용해서 read-only smoke test를 해.
Codex는 파일을 수정하지 말고 마지막 응답으로 CODEX_BG_OK만 반환하게 해.
새 절대경로 run directory와 prompt file을 사용하고 status.json과 result.md를 확인해.
```

Claude main은 Write로 prompt를 run directory 밖에 만들고, 아직 존재하지 않는
절대경로를 선택한 뒤 아래 명령 전체를 Bash tool의 `run_in_background=true`로
실행한다.
민감한 prompt와 실행 기록은 repository 밖 사용자 전용 경로에 둔다. helper는
repository 위치나 비밀 포함 여부를 검사하지 않으므로 경로 선택은 호출자의 몫이다.

```bash
# RUNNER는 §13.1에서 선택한 설치 경로를 유지한다.
PROMPT_FILE="/absolute/path/to/smoke.prompt.md"
RUN_DIR="/absolute/path/to/new-run-dir"

test -f "$PROMPT_FILE"
test ! -e "$RUN_DIR"

node "$RUNNER" run \
  --workdir "$PROJECT" \
  --prompt-file "$PROMPT_FILE" \
  --run-dir "$RUN_DIR" \
  --sandbox read-only \
  --timeout-seconds 21600
```

helper 자체는 foreground에서 Codex transport turn이 끝날 때까지 기다린다. Bash가
반환한 tracked task ID와 `RUN_DIR`을 기록한다. 사용자가 shell의 `&`나 `nohup`를
붙여 별도 daemon으로 만들지 않는다.

### 13.3 lifecycle과 경계

1. Claude top-level main이 prompt file과 새 run directory를 정한다.
2. Claude Code Bash tool이 helper를 tracked background task로 시작하고 task ID를 반환한다.
3. Claude main은 다른 일을 하거나 harness의 완료 알림을 기다린다.
4. helper가 Codex transport turn의 stdout/stderr와 terminal status를 artifact에 기록한다.
5. helper가 foreground process로 종료하고 tracked Bash job이 완료된다.
6. Claude main이 `status`, `result`, `events`, `stderr`와 write 작업의 실제 diff·test를 읽는다.
7. `completed`는 transport turn 종료일 뿐 요청한 작업의 수용·테스트 통과가 아니다.

Claude Code session이 종료되면 tracked background task가 정리될 수 있다. 종료된
session을 다시 깨우거나, session 종료 뒤 결과를 전달하거나, 재부팅 뒤 작업을
이어주는 보장은 없다. 이 공개판에는 systemd, session-delivery, notify daemon 또는
생존 controller가 없다. 진행 중인 tracked Bash job은 Claude Code TaskStop으로
취소한다.

### 13.4 sandbox·model·timeout

첫 smoke는 항상 `read-only`다. 파일 변경이 필요한 경우에만
`workspace-write`를 명시한다. `danger-full-access`는 공개 기본값이 아니며 접근
범위가 허용된 격리 환경에서만 직접 선택한다.

```bash
node "$RUNNER" run \
  --workdir "$PROJECT" \
  --prompt-file "$PROMPT_FILE" \
  --run-dir "$RUN_DIR" \
  --sandbox workspace-write \
  --model MODEL_ID \
  --timeout-seconds 21600
```

`--model`은 선택 인자다. 생략하면 Codex config 모델을 승계하며, helper가 다른
모델로 조용히 바꾸지 않는다. `--timeout-seconds` 기본값은 21,600초(6시간)다.
`--ignore-user-config`는 `run`·`resume`에서만 사용할 수 있는 진단용 선택 인자로,
그 호출에서 사용자 Codex config를 건너뛴다. 기본값은 사용자 config 승계이며 일반
실행에서는 이 인자를 생략한다.
prompt의 “이 파일만 수정해”는 기계적 sandbox가 아니다. `workspace-write`도
working directory 안의 광범위한 write가 가능하므로 dirty worktree와 diff를
반드시 확인한다.

### 13.5 결과와 명시적 status 확인

tracked task 완료 알림 뒤에도 main이 파일을 직접 확인한다. status command와
artifact 검사를 함께 실행한다.

```bash
node "$RUNNER" status --run-dir "$RUN_DIR"
test -f "$RUN_DIR/prompt.md"
test -f "$RUN_DIR/result.md"
test -f "$RUN_DIR/events.jsonl"
test -f "$RUN_DIR/stderr.log"
test -f "$RUN_DIR/status.json"
cat "$RUN_DIR/status.json"
cat "$RUN_DIR/result.md"
tail -n 50 "$RUN_DIR/events.jsonl"
tail -n 50 "$RUN_DIR/stderr.log"
```

각 새 run directory에는 `prompt.md`, `result.md`, `events.jsonl`, `stderr.log`,
`status.json`이 남는다. `events.jsonl`은 Codex `--json` stdout JSONL만 담고,
stderr는 `stderr.log`에만 담긴다. status file은 원자적으로 갱신된다. result가
없거나 status가 terminal이 아니면 `events.jsonl` 마지막 event, `stderr.log`와
tracked Bash exit를 대조한다. result가 있거나 process exit가 0인 것만으로 작업
완료를 선언하지 않는다.

### 13.6 명시적 thread resume

같은 Codex conversation context를 이어갈 때만 `status.json`에 기록된 thread UUID를
명시한다. `--last`와 마지막 thread 추론은 사용하지 않는다. resume은 기존 run
directory를 재사용하지 않고 새 artifact directory를 만든다.

```bash
FOLLOWUP_PROMPT="/absolute/path/to/followup.prompt.md"
FOLLOWUP_RUN_DIR="/absolute/path/to/another-new-run-dir"

test -f "$FOLLOWUP_PROMPT"
test ! -e "$FOLLOWUP_RUN_DIR"

node "$RUNNER" resume \
  --thread "<THREAD_UUID_FROM_STATUS>" \
  --workdir "$PROJECT" \
  --prompt-file "$FOLLOWUP_PROMPT" \
  --run-dir "$FOLLOWUP_RUN_DIR" \
  --sandbox workspace-write \
  --timeout-seconds 21600

node "$RUNNER" status --run-dir "$FOLLOWUP_RUN_DIR"
cat "$FOLLOWUP_RUN_DIR/status.json"
cat "$FOLLOWUP_RUN_DIR/result.md"
```

resume는 conversation context만 이어가며 이전 shell process나 당시 worktree를
복원하지 않는다. 독립 감리·다른 목적은 새 thread로 시작한다. resume도 run 종료 뒤
새 `status.json`·`result.md`를 직접 읽어야 하며 이전 run의 결과를 현재 실행 결과로
대체하지 않는다.

### 13.7 Claude background sub-agent에서의 잘못된 사용

다음 모양은 사용하지 않는다.

```text
Claude main
  └─ Claude background sub-agent
       └─ /codex-bg helper
```

helper artifact는 남을 수 있어도 background sub-agent가 completion event로 자동
재개된다고 보장할 수 없다. 자동 전달이 필요하다고 해서 helper를 daemon화하거나
Codex app-server probe를 안정 운영 경로로 승격하지 않는다.

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

Claude → Codex helper의 prompt와 run directory는 사용자가 정한 repository 밖의
절대경로에 둔다. 각 run directory에는 `prompt.md`, `result.md`, `events.jsonl`,
`stderr.log`, `status.json`이 생긴다. helper는 run directory를 자동으로 삭제하지
않는다.

로그에는 다음이 들어갈 수 있다.

- prompt 일부 또는 final response
- Codex JSONL stdout (`events.jsonl`)와 stderr (`stderr.log`)
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

### 20.11 `/codex-bg` skill이 Claude에서 안 보이거나 helper가 없다

project scope라면 `$PROJECT/.claude/skills/codex-bg`, user scope라면
`$HOME/.claude/skills/codex-bg` 아래에 `SKILL.md`와 `scripts/run.mjs`가 모두
있어야 한다. 두 파일을 다시 설치한 뒤 기존 Claude session을 닫고 새 session을
시작한다. health와 helper 실행은 §13.1–§13.2의 명령을 사용한다.

### 20.12 helper는 끝났지만 result/status를 찾을 수 없다

helper 실행 때 지정한 **새 절대경로** run directory를 확인하고 §13.5의
status·artifact 대조를 따른다. 예전 slug 기반 세 파일 recipe를 사용하지 않는다.
`events.jsonl`은 stdout JSONL, `stderr.log`는 진단 출력이며, Claude session 종료로
tracked job이 정리된 경우 session 종료 뒤 main wake나 결과 delivery를 기대하지 않는다.
helper를 daemon/systemd/notify로 바꾸지 말고 새 run을 시작한다.

### 20.13 helper run이 `model unavailable`로 실패한다

public skill은 model을 고정하지 않는다. `--model`을 지정했다면 계정에서 사용
가능한 ID인지 확인하고, 설정된 기본 모델을 사용할 때는 `--model`을 제거한 새 run을
만든다. 완료된 run directory를 덮어쓰지 않는다.

### 20.14 resume이 거부되거나 잘못된 대화를 이어간다

§13.6에서 status.json의 명시적 thread UUID만 `--thread`에 넣고, `--last`나 마지막
run 자동 선택을 사용하지 않는다. resume은 기존 run directory와 별개의 새 절대경로를
받아야 한다.

thread를 잃었거나 다른 task의 UUID라면 새 thread로 발주한다. resume은 conversation
context만 보존하며 이전 shell process나 worktree 상태를 복원하지 않는다.

### 20.15 WSL과 Windows binary가 섞였다

```bash
command -v node claude codex
file "$(command -v node)"
file "$(command -v claude)"
file "$(command -v codex)"
printf 'WSL_DISTRO_NAME=%s\n' "$WSL_DISTRO_NAME"
```

Windows npm global path나 `.exe`가 먼저 나오면 WSL PATH를 수정한다.

### 20.16 repository가 `/mnt/c` 아래라 느리다

```bash
mkdir -p "$HOME/code"
cd "$HOME/code"
git clone <YOUR_PROJECT_GIT_URL> my-project
```

WSL Linux filesystem으로 옮기고 installer의 `--project`와 Codex config workdir을
새 절대경로로 다시 맞춘다.

### 20.17 app-server probe에서 `process/spawn` unknown method

```bash
codex --version
codex app-server --help
```

현재 Codex CLI가 experimental process API를 포함하는지 확인한다. CLI를 update한
경우 protocol 변경 가능성이 있으므로 probe source와 official app-server 문서를
대조한다. 기존 TUI에서 이 method를 직접 호출하려 하지 않는다.

### 20.18 busy probe가 `first-turn-completed-before-claude`로 실패한다

첫 Codex turn이 Claude보다 먼저 끝났다는 뜻이다. PC나 model 속도에 따라 race가
날 수 있다.

probe의 first turn sleep을 늘리거나 Claude model을 더 빠른 것으로 바꾼 뒤 다시
실행한다. 이것은 queue logic 실패가 아니라 test timing 실패일 수 있다.

### 20.19 dirty worktree에서 변경 귀속이 불분명하다

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

### 21.1 `/codex-bg` helper runtime update

public clone의 변경을 받은 뒤에는 installer의 helper 전용 mode로 skill runtime 전체를
업데이트한다. `--only codex-bg`는 `SKILL.md`와 `scripts/run.mjs`를 함께 복사하며,
기존 skill에서 바뀌는 asset은 timestamp backup한다. reverse MCP source, Codex TOML,
Claude CLI와 login 상태에는 접근하거나 변경하지 않는다.

```bash
cd "$BRIDGE_REPO"
git status --short
git pull --ff-only

./install.sh \
  --only codex-bg \
  --project "$PROJECT" \
  --dry-run

./install.sh \
  --only codex-bg \
  --project "$PROJECT"
```

user scope면 `--skill-scope user`를 더한다. `--only codex-bg`가 끝난 뒤 Claude
session을 새로 시작하고 §13.1의 helper health 확인을 따른다. 진행 중인 run directory는
수정하지 않는다.

기존 양방향 설치를 갱신하려고 `./install.sh --project "$PROJECT"`를 사용할 수도
있지만, 이 기본 mode는 기존 `claude-coder` MCP table을 prewrite 전에 발견하면
중복을 만들지 않고 종료한다. 기존 table이 있는 경우 먼저 설정을 검토한 뒤 수동
절차를 사용한다. helper만 업데이트하는 상황에서는 반드시 `--only codex-bg`를
사용해 MCP/config를 건드리지 않는다.

### 21.2 public reverse bridge source update

```bash
cd "$BRIDGE_REPO"
git status --short
git pull --ff-only

node bridge/claude-coder-mcp/smoke.mjs
node bridge/claude-coder-mcp/smoke.mjs --live --model haiku
```

source path가 그대로면 Codex TOML을 다시 추가할 필요는 없다. source directory를
옮겼다면 `command`를 새 절대경로로 바꾸고 Codex를 재시작한다.

### 21.3 Claude Code update

native install:

```bash
claude update
claude --version
claude doctor
```

update 뒤 MCP live smoke를 다시 실행한다.

### 21.4 Codex update

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

installer가 만든 config backup은 실제 config 경로에 `.bak.<timestamp>`를 붙인
모양이다. 기본 경로는 `CODEX_HOME`이 설정됐으면
`$CODEX_HOME/config.toml.bak.<timestamp>`, 아니면
`$HOME/.codex/config.toml.bak.<timestamp>`다. 전체 config를 backup으로 되돌리기
전에 이후 추가된 다른 설정이 없는지 diff한다.

### 22.3 local state 제거

audit가 더 필요 없는지 확인한 뒤에만:

```bash
rm -rf "$HOME/.local/state/claude-codex-bridge"
```

### 22.4 public clone 제거

Codex config에서 `claude-coder`를 먼저 제거한 뒤 clone을 삭제한다. config가
`run.sh`를 가리키는 상태에서 clone만 지우면 Codex 시작 때 MCP가 실패한다.

---

## 23. 2026-09-15 검증 결과

Node.js `20.18.0`, Codex CLI `0.154.0`에서 아래 검사를 실행했다.
자동 검사는 fake CLI와 임시 설치 대상을 사용하며, 이어서 최신 helper를 임시 git
project에 실제 설치해 로그인된 Codex의 새 turn과 명시적 thread 재개를 확인했다.
원본 실행 기록은 project 밖 검증 폴더에 보존하고 공개 commit에는 넣지 않았다.

```bash
cd "$BRIDGE_REPO"
node --test skills/codex-bg/scripts/run.test.mjs tests/install.test.mjs
bash -n install.sh
node --check skills/codex-bg/scripts/run.mjs
git diff --check
node skills/codex-bg/scripts/run.mjs health
```

| 확인 대상 | 실제 결과 |
| --- | --- |
| [runner tests](skills/codex-bg/scripts/run.test.mjs) + [installer tests](tests/install.test.mjs) | 2026-09-15 최종 확인, 33/33 통과·실패 0. 정상/실패/중단/timeout, TOML·symlink·동시 설치·설정 경로 충돌 포함 |
| Bash/Node syntax, diff whitespace | 모두 exit 0 |
| `--only codex-bg` 재설치 | exit 0, 기존 skill/runner backup 생성, 설치본과 source `cmp` 일치 |
| 설치된 helper health | exit 0, CLI `0.154.0`, login `ok: true` |
| 실제 새 run | 18:18:51–18:19:17 KST, exit 0·`completed`, `CODEX_BG_OK BRIDGE_STATE_FINAL_615` |
| 실제 명시적 thread resume | 18:20:04–18:20:17 KST, 같은 thread·새 run directory, exit 0·`completed`, `BRIDGE_STATE_FINAL_615 RESUME_OK` |
| 실제 실행 기록 | 두 실행 모두 5개 artifact 확인. `events.jsonl` 전 행 JSON parse 및 `turn.completed`, `status.json` 종료 사실, `result.md` 내용 대조 |

마지막 실제 run/resume는 같은 모델 `gpt-6-astra`와 `--ignore-user-config`를 명시했다.
Codex 안에서 다른 Codex를 실행하는 검증 조건을 분리하려고 자식 환경에서
`CODEX_SESSION_ID`와 `CODEX_THREAD_ID`를 제외했으며, helper의 기본 동작은 바꾸지 않았다.
앞선 기본 사용자 설정 승계 run/resume도 성공했지만, 최초 시도는 이벤트 없이 120초
timeout이었다. 초기화 지연의 원인은 확정하지 않았다.

Claude top-level UI의 완료 알림·TaskStop·session 종료 정리는 이번에 재실행하지
않았다. 이 경계는 현재 공식 문서와 §24의 7월 실측을 구분해 읽는다.
역방향 MCP live smoke와 app-server probe도 이번 갱신에서는 재실행하지 않았다.

---

## 24. 2026-07-14 historical verification (retained, not rerun)

아래 결과와 버전은 2026-07-14에 기록한 historical evidence다. 이번
2026-09-15 갱신에서 다시 실행했다고 해석하지 않는다.

### 24.1 source와 installer

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

### 24.2 Codex → Claude live smoke

실제 결과:

```text
status=completed
exit_code=0
timed_out=false
final_response=CLAUDE_CODER_MCP_OK
```

이 결과는 public portable source가 현재 WSL Claude login으로 실제 Claude child를
실행하고 같은 MCP call에 결과를 반환했음을 뜻한다.

### 24.3 app-server idle probe

실제 결과:

```text
ok=true
mode=idle
claudeResult=CLAUDE_BG_BRIDGE_OK
codexMessage=CODEX_EVENT_WAKE_OK
turnStatus=completed
```

### 24.4 app-server busy probe

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

### 24.5 Claude → Codex wake

이 방향의 완료 계약은 top-level Claude Code Bash background job 종료 notification이다.
이 README의 13.1절과 같은 read-only `codex exec`를 다시 실행해 exit code 0과
`CODEX_EXEC_OK` result file을 확인했다. 기존 Claude Code 환경에서는 top-level
background job의 Claude main completion wake도 확인했다. 다만 이 README를 갱신한
session 자체는 Claude main harness가 아니므로 이번 Codex turn에서 해당 UI wake까지
재실행했다고 주장하지 않는다. 새 설치자는 13.2절의 smoke로 자기 Claude Code
client에서 마지막 wake를 확인해야 한다.

---

## 25. 현재 보장 범위와 남은 한계

### 안정 운영 경로

- Claude main → Codex: `/codex-bg` + `scripts/run.mjs` foreground helper + tracked Bash background job
- 새 run directory의 `prompt.md`, `result.md`, stdout-only `events.jsonl`, `stderr.log`, `status.json`
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
- Claude Code session 종료 뒤 helper 생존·결과 delivery·Claude main wake
- app-server durable production controller
- controller restart 뒤 queue recovery
- 여러 PC에 걸친 distributed queue
- permission approval UI relay
- credential 배포
- prompt에 적힌 file 목록을 강제하는 OS sandbox
- 모든 Claude/Codex release에 대한 미래 호환성 보장

---

## 26. 공식 참고 문서

- [Claude Code advanced setup](https://code.claude.com/docs/en/setup)
- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes)
- [Claude Code permissions](https://code.claude.com/docs/en/permissions)
- [OpenAI Codex CLI](https://developers.openai.com/codex/cli/)
- [OpenAI Codex MCP](https://developers.openai.com/codex/mcp/)
- [OpenAI Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Claude Code interactive mode — background Bash](https://code.claude.com/docs/en/interactive-mode)
- [OpenAI Codex app-server](https://learn.chatgpt.com/docs/app-server)
- [OpenAI Codex WSL guide](https://learn.chatgpt.com/docs/windows/wsl)
- [VS Code Remote development in WSL](https://code.visualstudio.com/docs/remote/wsl-tutorial)
- [OpenAI Codex source repository](https://github.com/openai/codex)

---

## 27. 설치 완료 판정표

아래를 모두 확인해야 설치 완료다.

- [ ] VS Code window와 terminal이 WSL2 안에 있다.
- [ ] repository가 WSL Linux filesystem에 있다.
- [ ] `node`, `claude`, `codex`가 같은 WSL user PATH에 있다.
- [ ] Claude interactive login이 된다.
- [ ] `codex login status`가 성공한다.
- [ ] public clone을 삭제하지 않을 위치에 두었다.
- [ ] `install.sh --dry-run`의 모든 절대경로를 확인했다.
- [ ] helper만 설치할 때 `install.sh --only codex-bg`가 skill runtime을 복사하고 MCP/config/Claude를 건드리지 않는다.
- [ ] `codex mcp get claude-coder`가 enabled stdio server를 보여준다.
- [ ] MCP health smoke가 다섯 tool을 보여준다.
- [ ] MCP live smoke가 `CLAUDE_CODER_MCP_OK`를 반환한다.
- [ ] 새 Claude session에서 `/codex-bg` skill이 발견된다.
- [ ] `node --version`은 20 이상이며, helper health는 Codex CLI 버전과 로그인 상태를 보여준다.
- [ ] Claude top-level main의 read-only `/codex-bg`가 새 run directory와 다섯 artifact를 만든다.
- [ ] 그 tracked background job이 session이 살아 있는 동안 완료되면 main이 completion event를 받는다.
- [ ] write mode 전에 dirty worktree와 sandbox를 확인한다.
- [ ] app-server가 필요하면 idle probe를 통과한다.
- [ ] busy delivery가 필요하면 busy probe도 통과한다.
- [ ] credential과 audit log가 git에 들어가지 않는다.

이 판정표에서 reverse MCP live smoke와 helper의 새 artifact·tracked Bash 완료 확인이
각각 통과하면 일상 양방향 사용이 가능하다. helper 완료는 Claude Code session이
살아 있을 때의 tracked job 범위다. app-server 항목은 detached Claude 완료 뒤 Codex가
새 turn을 시작해야 하는 별도 experimental 요구가 있을 때만 필요하다.
