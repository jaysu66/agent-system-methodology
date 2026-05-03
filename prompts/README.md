# 6 个 Agent Prompt(可直接 copy 用)

抽象自 harness v3 实战。每个 prompt 都包含**占位符**(`{XXX}`),你换成你的项目名词即可。

---

## Prompt 速览

| # | 文件 | 谁用 | 用途 |
|---|---|---|---|
| 01 | [01-main-session-loop.txt](01-main-session-loop.txt) | User | 启动主 session /loop dynamic mode 监控 |
| 02 | [02-dev-session-spawn.txt](02-dev-session-spawn.txt) | Main session | spawn dev session 跑 SKILL §4 5-step |
| 03 | [03-verify-session-spawn.txt](03-verify-session-spawn.txt) | Dev session(自调)/ Main session(兜底) | spawn verify session(独立 worktree + cascade fallback) |
| 04 | [04-architect-fix-spec.txt](04-architect-fix-spec.txt) | User → Architect | architect 起 fix-batch SPEC 模板 |
| 05 | [05-phase-validation-spawn.txt](05-phase-validation-spawn.txt) | Main session | spawn phase 验证 dev session(fail-greedy 协议) |
| 06 | [06-emergency-rescue.txt](06-emergency-rescue.txt) | Main session | 兜底操作清单(rebase/force push/merge stuck PR/kill zombie) |

---

## 怎么用

### 场景 1:你是新 user 第一次跑

1. 启动 Claude Code
2. copy `01-main-session-loop.txt` 内容 → 在 Claude Code 输入 `/loop {prompt 内容}`
3. 我开始监控 + 自醒,撞事 ping 你

### 场景 2:你要 spawn 一路 dev session

让我代办即可(我会用 `02-dev-session-spawn.txt` 的模板)。或你自己:

```powershell
$prompt = (Get-Content prompts/02-dev-session-spawn.txt -Raw) -replace '{TRACK}', 'your-track-name'
Start-Process cmd.exe -ArgumentList "/c", "claude --print --dangerously-skip-permissions `"$prompt`" > resume_log.txt 2>&1" -WorkingDirectory "../your-worktree" -WindowStyle Hidden
```

### 场景 3:你要让 architect 起 fix SPEC

copy `04-architect-fix-spec.txt` 内容 → 去 architect session 输入。
架构师写完 SPEC PR → 我 sanity review → 你回 `ack` → 我代办 merge。

### 场景 4:你撞 stuck / hang 不知道怎么办

`06-emergency-rescue.txt` 列了所有兜底操作 + 我代办的命令。

---

## 占位符约定

每个 prompt 用 `{XXX}` 占位:

- `{TRACK}` — sub-task 标识(e.g. `fix-phase1-001-adapter-ledger`)
- `{PROJECT}` — 项目根名(e.g. `harness`)
- `{LAYER}` — 架构层(e.g. `K0` / `K1` / `governance`)
- `{COMMIT}` — git commit hash(e.g. `380acd8`)
- `{PR}` — PR number(e.g. `30`)
- `{TIMESTAMP}` — ISO 8601 UTC(e.g. `2026-05-03T01:35:00Z`)

PowerShell `-replace` 或 sed 替换即可。
