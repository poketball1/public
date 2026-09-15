# keep-warm injector (VS Code)

터미널에 직접 타이핑할 수 있는 유일한 주체는 그 터미널을 쥔 프로세스다. 이 확장은
그 자리에서 **요청 파일을 읽어 타이핑만** 한다 — 확인도, 재시도도, 원장도 없다.

## 설치

```bash
mkdir -p ~/.vscode/extensions/keepwarm-injector
cp package.json extension.js ~/.vscode/extensions/keepwarm-injector/
```

그 다음 VS Code 에서 **Developer: Reload Window** (`Ctrl+Shift+P`). 확장 파일을
고칠 때마다 Reload Window 가 필요하다 — VS Code 는 확장 코드를 프로세스 시작 시
한 번만 읽는다. 이걸 잊으면 "코드를 고쳤는데 동작이 그대로"인 상태로 한참 헤맨다.

동작 확인: `View → Output` 에서 `keep-warm injector` 채널을 고르면
`watching /home/<you>/.claude/wake-request` 한 줄이 보여야 한다.

## 계약

요청 파일 `~/.claude/wake-request/<sid>.json`:

```json
{
  "sid": "2f9c1d04-7b3e-4a51-9c80-000000000001",
  "message": "[keep-warm 14:32] arm_a1b2c3#3 — warm 유지용 자동 턴. ...",
  "source": "keepwarm-arm",
  "requested_at": 1789083402,
  "submit_plan": ["body", "cr"]
}
```

- `sid` 가 권위다. 파일 이름이 아니라 이 필드로 터미널을 찾는다.
- `requested_at` 은 epoch **초**. 확장은 이 값을 읽지 않는다 (TTL 은 파일 mtime 기준).
- `submit_plan` 토큰: `body` (개행 없이 본문), `cr` (캐리지 리턴 하나),
  `body+cr`, `newline-submit`, `delay:<ms>` (최대 2000). 본문 쓰기는 정확히 1회여야
  하고, 위반하면 통째로 무시하고 기본 `["body","cr"]` 로 떨어진다.
- 슬롯은 sid 당 하나다. 발신측은 `link(2)` 로 써서 **기존 파일을 절대 덮지 않는다** —
  아직 소비되지 않은 남의 메시지를 조용히 지우는 것을 막기 위해서다.

## 설계상 그렇게 한 것

**세션 엄격(session-strict)**. 대상 세션의 터미널이 이 창에 없으면 파일을 **그대로
둔다**. "활성 터미널"·"유일한 터미널" 같은 fallback 은 자동 경로에 두지 않는다 —
엉뚱한 세션에 들어간 keep-warm 턴은 놓친 턴보다 나쁘다.

**본문과 Enter 를 따로 쓴다** (`sendText(body,false)` → `sendText('\r',false)`).
하나로 합친 `sendText(text, true)` 는 입력이 유실되는 것이 관측됐다. 그리고 이 모양
덕분에 재시도가 성립한다 — Enter 가 씹히면 본문은 입력창에 남아 있고, 재시도 문구가
그 뒤에 붙어 한 번의 Enter 로 합쳐져 제출된다.

**500자에서 자른다. 정규화 다음에.** 발신측 확인 술어도 **같은 순서로** 정규화해야
한다. 두 쪽 규칙이 어긋나면 모든 확인이 실패하고 모든 발사가 재시도로 가는데, 원장에는
"전달 문제"로 보인다 — 실제로는 매칭 문제다.

**정규화 규칙 두 개, 순서 고정**: `[\r\n\t]+ → " "` 다음 `[\x00-\x08\x0b-\x1f\x7f] → ""`.
순서가 바뀌면 `"a\rb"` 가 `"a b"` 가 아니라 `"ab"` 가 된다.

## 알려진 구멍

TTL 만료 검사는 **그 요청을 처리하는 패스**와 시작 시 부트스트랩 스캔에서만 돈다.
대상 터미널이 **어느 창에도** 없으면 `fs.watch` 가 한 번 울리고 파일은 남는데, 그 뒤
그 파일을 다시 건드리는 것이 아무것도 없다. 남은 파일은 그 sid 의 유일한 슬롯을
점유하므로 다음 배달이 `link(2)` EEXIST 로 즉시 실패한다. 실제 운영에서 TTL 의 400배가
지난 파일이 남아 있는 것을 확인했다. 재현하는 쪽에서는 발신측에 슬롯 점유 실패를
전달 실패로 기록하게 하고, 주기적으로 오래된 요청 파일을 청소하는 쪽을 권한다.
