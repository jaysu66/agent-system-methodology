# Tools

实操脚本,从 harness v3 实战版直接 copy。改占位符即可用。

---

## dispatcher.ps1.example

**实战版** dispatcher v5(harness 项目用了 50+ 小时,catch 了 5 路 LLM compliance bug)。

### 是什么

PowerShell daemon,30s polling 你的项目 worktree state(PROGRESS.md / git log / GitHub PR state),做 3 件事:

| Path | 检测 | 行为 |
|---|---|---|
| **Path 1** | PROGRESS.md `alert_level=needs_human` | toast notification + 写 dispatcher_log.md |
| **Path 2** | status 含 pr_submitted/step_5_done/verify_done 但 last_update 30+ min 没变 | 自动 spawn `claude --print "/{project}-dev verify {track}"` 兜底 |
| **Path 3** | 上游 sub-task 全 merged + 下游 worktree 不存在 | 自动 `git worktree add` + spawn 下游 dev session |

### 怎么用

1. copy `dispatcher.ps1.example` → `dispatcher.ps1`
2. 改:
   - `$PROJECT_ROOT` 改成你项目根
   - `$PROJECT_NAME` 改成你项目名(命令前缀,比如 `harness-dev`)
   - `$PHASE_DEPS`(Path 3 chain)改成你项目 sub-task 依赖图
   - 替换 `{TRACK}` `{COMMIT}` 等占位符
3. 启 daemon:
   ```powershell
   Start-Process powershell.exe `
       -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", `
                     "-File", "tools/dispatcher.ps1" `
       -WindowStyle Hidden -PassThru
   ```
4. log 看 `tools/dispatcher_log.md`(daemon 行为日志)

### 关键 design

- **30s polling**(不要更快,polling 太频繁伤 API + git fs)
- **last_update 30+ min stuck threshold**(LLM compliance bug 实战频率,catch 30% 不听话)
- **claude .cmd shim 包 cmd.exe**:Windows 上 `claude` 是 .cmd 不是 .exe,Start-Process 必须用 `cmd.exe /c claude ...`
- **worktree 隔离 spawn**:每个 sub-task 独立 worktree,避免 dev session 互相污染

### 实战出处

harness 100h 实战:
- Path 1 实战 catch 7 次 needs_human(SPEC bug / cascade 全 fail)
- Path 2 实战 catch 5 次 LLM compliance bug(passive 等 trigger)
- Path 3 实战 spawn 4 路 fix-batch-2 + 3 路 fix-batch-3 R2 + 1 路 fix-batch-4 R3 dev session 自动 chain

详见 [../lessons-learned/llm-compliance-bugs.md](../lessons-learned/llm-compliance-bugs.md)。

---

## 其他建议工具(未提供模板,需要你自己写)

### dashboard server(可选)

uvicorn `:8000` 服务,WebSocket push PROGRESS.md state 到浏览器(让 user 一眼看 N 路并行状态)。harness 用 FastAPI + 9-panel HTML,~500 行,不复杂。

### Cron / ScheduleWakeup setup

Anthropic Claude Code 提供 `ScheduleWakeup` API,/loop dynamic mode 自动用,不需要你写。

但如果你的环境没有(用其他 CLI),可以用 OS-level cron(Linux)/ Task Scheduler(Windows)/ launchd(macOS)启 main session。

---

## License

dispatcher.ps1 抽象自 harness 项目,MIT。改改继续用。
