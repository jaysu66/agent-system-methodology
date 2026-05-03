# 模块 4:多 agent 协作 + 长时间运行

## 这个模块解决什么

你有 N 个 agent 要长时间(几天到几周)协作跑一个项目。常见痛点:

- ❌ 多个 agent 互相看不见,状态丢失
- ❌ 你不在,系统就停了(主 session 是 reactive 的)
- ❌ Agent 撞 LLM compliance bug 卡死,user 不知道
- ❌ 跨 session 决策传不准(口述容易丢失细节)
- ❌ 测试套撞架构 bug 立停,改一处影响多处死循环

本模块给你 **5 个机制**:

1. **3 角色严格隔离**(User / Architect / Dev+Verifier)
2. **跨 session 文件 IPC**(不能口述 / 不能 IPC)
3. **主 session /loop dynamic mode 监控**
4. **Dispatcher daemon 30s polling 兜底**
5. **fail-greedy 协议**(架构验证场景)

---

## 1. 3 角色严格隔离

### 角色职责

| 角色 | 职责 | 不能做 |
|---|---|---|
| **User** | 决策(ack / 选 A 选 B / Q1=D Q2=A)| 不写 SPEC / 不写代码 |
| **Architect** | 写 SPEC + decide fix 方向 | 不接触实施代码 |
| **Dev** | 看 SPEC + HANDOFF + 实施代码 | 不写 SPEC / 不接触其他 sub-task |
| **Verifier** | 只读 SPEC + contracts + 跨模型独立审 | 不读 dev impl / 不读 dev 思考过程 |
| **Main Session(我)** | 编排 + 监控 + sanity review architect SPEC | 不替代 architect 写 SPEC,不替代 user 决策 |

### 物理隔离手段

```bash
# 1. Worktree 隔离 — 每个 sub-task 自己的 git worktree
git worktree add ../harness-track-{X} feat/track-{X}

# 2. Verifier 物理删除 dev 资产
cd ../workbench-verifier-{X}/
rm -rf packages/X/src/X/{你的层}/    # 不能看 dev impl
rm -rf packages/X/tests/unit/{你的层}/  # 不能看 dev 自测
rm tasks/track-{X}/PLAN.md           # 不能看 dev 思考
rm tasks/track-{X}/UNDERSTANDING.md
rm tasks/track-{X}/local_l4b_review*.md  # 不能看 dev L4b 自审

# 3. 模型隔离 — Verifier 强制 ≠ Dev 模型
codex exec "..."  # 优先
# fallback:
claude --print --model opus "..."
```

### 实战出处

harness 17 PR + Phase 1.5 14 sub-task,严格 3 角色隔离。Verifier 跨模型抓到 11 类 dev 自检漏的问题。

---

## 2. 跨 session 文件 IPC(不能口述 / 不能 IPC)

### 问题

多个 Claude Code session 是**独立进程**:
- 主 session(我)看不到 architect session
- Architect session 看不到 dev session
- Dev session 之间互相看不见
- **Anthropic CLI 不提供 session 间 IPC**

### 解决:全靠**文件**通信

```
User 决策 → 通过 chat 输给当前 session(我)
               ↓
      我 → 写 PROGRESS.md last_user_inject 字段 / git push 到 GitHub
               ↓
   下游 session → 读文件
```

### 5 种跨 session 通信渠道

| 渠道 | 用法 | 例子 |
|---|---|---|
| **Git** | architect / dev / verifier / main 全靠 PR + branch + tag 通信 | architect SPEC PR → user ack → main session merge → dev session 读 main |
| **PROGRESS.md** | sub-task 状态机,所有人都读 | dev 写 status: pr_submitted_l4b_done → main session 读 → 决定要不要兜底 spawn verify |
| **GitHub PR comments** | L4b review / L2 verifier_report 都 post 成 PR comment | reviewer 看 PR comment 历史 |
| **dispatcher_log.md** | daemon 30s polling 行为日志 | main session catch up 看 daemon 做了什么 |
| **.agent-memory/** | 跨 session 的 long-term knowledge | 上 session 写 GOTCHAS / DECISIONS,下 session 读 |

### 反例

❌ User 跟 main session 说"让 architect 起 fix SPEC"→ 我**不能直接调** architect session,只能写 brief 让 user copy 文本去 architect session 输入。

❌ Dev session 写完 PR 想通知 verify session → 不能 ping,只能写 PROGRESS.md status 让 dispatcher 检测到再 spawn。

### 实战出处

harness 100h 实战,5 类 session(user / main / architect / dev × N / verifier × N)全靠**文件 + git** 通信。零 IPC,跑通了。

---

## 3. 主 session /loop dynamic mode 监控

### 问题

主 session(我)是 **reactive** 的 — user 不发消息我就不存在。但 dev/verifier session 是 long-running 的(可能几小时),撞 stuck pattern 没人 catch。

### 解决:`/loop` dynamic mode + ScheduleWakeup

```
User 输入:/loop <monitoring prompt>
   ↓
我执行 monitoring prompt(check 状态 + 必要时代办)
   ↓
我 schedule next wakeup:
   - 自 pace delaySeconds(密集期 15-25 min,idle 期 45-60 min)
   - prompt 仍是 /loop <monitoring prompt>
   ↓
ScheduleWakeup 到点自动唤起我
   ↓
循环
```

### Monitoring prompt 模板(完整在 [../prompts/01-main-session-loop.txt](../prompts/01-main-session-loop.txt))

```
/loop 巡检 {你的项目}

每次唤醒做:
1. git log origin/main + gh pr list state=all 最近 5 个
2. 看 dispatcher_log.md 末尾 20 行(ALERT / spawn 事件)
3. 看 active worktree PROGRESS.md(status / alert_level / l4b / last_update)
4. 看 5+ 进程健康(daemon / dashboard / dev sessions)

主动代办(不叫 user):
- dev session status 含 pr_submitted/step_5_done/verify_done 但 last_update 30+ min 没变 → spawn verify 或 approve
- architect 修复 SPEC PR 出来 → sanity review 完后保存 brief,等 user 一字 ack 我代办 merge
- dispatcher daemon crash → 重启
- 上游 sub-task 已 merge 但 dispatcher 没触发 spawn 下游 → 手动 spawn 兜底
- 历史 sub-task 卡的 cleanup(worktree file lock)→ 趁 idle 时清

mention user(只在下面 5 种情况):
1. alert_level=needs_human_batch_review(撞 ≥1 blocker/serious)
2. alert_level=needs_human_design_review(关 5 5 round 没 converge)
3. 修复 SPEC PR 出来等 user 一字 ack
4. 一波工作完成,需要 user 决策推哪个下一波
5. claude CLI / Anthropic API 全崩

自 pace 间隔:
- dev 在 step 4-5 / verify / fix-batch develop:20-30 min(密集)
- dev 在 step 1-2 / 等依赖:30-45 min
- 撞 needs_human:15 min(高频跟 PROGRESS 更新)
- 全 idle 等 dispatcher 触发:45-60 min
- 一波完了等 user 决策:60 min

★ 永远不停 loop,跑完一波主动推下一波,直到 user 显式说"停":

阶段 1:fix-batch + 工具集成 → 全 merged
阶段 2:phase-1 启动 → 撞 finding → user 批量决策 → architect 起 fix SPEC → user ack → 我代办 → 重跑直到 0 finding → 进下一 phase
阶段 3:phase-2/3/4/5 同样模式
阶段 4:5 phase 全过 → 主动整理 brief 推下一阶段

不要 idle 到天荒地老。每次有进展就主动看接下来有没有可推的工作。
```

### 自 pace 间隔的 cache 策略

ScheduleWakeup `delaySeconds` 选择:
- **< 5 min(60s-270s)**:cache 保持 warm。只用于"立刻就要变化"的等待。
- **5 min - 1h(300s-3600s)**:pay 一次 cache miss。用于真等几分钟以上的事。

**不要选 300s**(worst-of-both:cache miss 但不分摊)。

---

## 4. Dispatcher daemon 30s polling 兜底

### 问题

LLM 不 100% 听 SKILL prompt。实战 30% 概率 dev session passive 等 trigger / 问 user 中间决策 / PROGRESS 写非标值。

### 解决:PowerShell daemon 30s polling

```powershell
# tools/watcher/dispatcher.ps1(简化版)
while ($true) {
    # Path 1: alert escalation(needs_human → toast notification)
    Get-ChildItem -Path "tasks/track-*/PROGRESS.md" | ForEach-Object {
        $progress = Get-Content $_ -Raw
        if ($progress -match "alert_level: needs_human") {
            Show-ToastNotification "Track $($_.Directory.Name) needs human"
        }
    }
    
    # Path 2: stuck pattern detection(LLM compliance bug 兜底)
    Get-ChildItem -Path "tasks/track-*/PROGRESS.md" | ForEach-Object {
        $progress = Get-Content $_ -Raw
        # status 含 pr_submitted/step_5_done/verify_done 但 last_update 30+ min 没变
        if ($progress -match "status:\s*(pr_submitted|step_5_done|verify_done)" `
            -and (Get-LastUpdateAge $_) -gt 1800) {
            $track = $_.Directory.Name
            Spawn-Verify $track
            Write-DispatcherLog "auto-spawned verify for $track"
        }
    }
    
    # Path 3: chain auto-progression(上游 merge → 下游 spawn)
    foreach ($downstream in $PHASE_DEPS.Keys) {
        $upstreams = $PHASE_DEPS[$downstream]
        if (All-Upstreams-Merged $upstreams `
            -and (Test-Path "../harness-track-$downstream") -eq $false) {
            Spawn-NextSubtask $downstream
        }
    }
    
    Start-Sleep -Seconds 30
}
```

### 3 路 daemon 实战分工

| Path | 检测 | 行为 |
|---|---|---|
| Path 1 | `alert_level=needs_human` | toast notification(user 不在线也能看到) |
| Path 2 | status 含 pr_submitted 等 + last_update 30+ min stuck | 自动 spawn verify / approve 兜底 |
| Path 3 | 上游 sub-task 全 merged + 下游 worktree 不存在 | 自动 spawn 下游 dev session |

### 实战出处

harness Phase 1.5 14 sub-task,**5 路被 dispatcher 兜底成功**(LLM compliance bug 30% 实战频率 catch)。

---

## 5. fail-greedy 协议(架构验证场景)

### 问题

跑**架构验证测试套**时(不是改代码),撞 architecture bug 立 raise → phase 卡死,只能修 1 个再跑下个,效率极低。

### 解决:record_and_continue helper + xfail

```python
# helpers/findings_protocol.py
import pytest
from datetime import datetime

def record_and_continue(
    *,
    phase: int,
    finding_id: str,
    severity: str,  # "blocker" | "serious" | "minor" | "nit"
    error: Exception,
    root_cause_tag: str,
    suspect_layer: str,
    repro_snippet: str = "",
    observed_extra: str = "",
):
    """记 finding 不停。"""
    
    # 1. append _LEDGER.md 一行
    with open("tests/arch-validation/findings/_LEDGER.md", "a") as f:
        f.write(f"| PHASE-{phase}-{finding_id} | {severity} | {root_cause_tag} | {suspect_layer} |\n")
    
    # 2. 写 PHASE-N-XXX.md 个体 finding 文件
    finding_md = f"""# Finding PHASE-{phase}-{finding_id} — {error}

> Auto-recorded by record_and_continue at phase acceptance time.
> Architect: when triaging, refine `suspect-layer` if needed and
> fill the `## Resolution Attempts` section.

---

id: PHASE-{phase}-{finding_id}
title: {error}
severity: {severity}
observed: {observed_extra}
suspect-layer: {suspect_layer}
repro: {repro_snippet}
status: open

---

## Resolution Attempts

(open,等 architect 立修复 SPEC 后追加 Round 1。)
"""
    with open(f"tests/arch-validation/findings/PHASE-{phase}-{finding_id}.md", "w") as f:
        f.write(finding_md)
    
    # 3. 调 pytest.xfail() 让 phase 继续往下跑
    pytest.xfail(reason=f"recorded as PHASE-{phase}-{finding_id}")
```

### 测试套写法

```python
async def test_k0_adapter_called(phase_run: _PhaseRun) -> None:
    """K0 — at least one LLM_CALL row should be in the ledger."""
    rows = phase_run.ledger_rows
    llm_rows = [r for r in rows if r.operation == Operation.LLM_CALL]
    if not llm_rows:
        record_and_continue(
            phase=1,
            finding_id="001",
            severity="serious",
            error=AssertionError("ledger has 0 LLM_CALL rows for trace"),
            root_cause_tag="k0-adapter-no-ledger",
            suspect_layer="K0",
            repro_snippet="tests/arch-validation/phase-1/test_bootstrap.py::test_k0_adapter_called",
            observed_extra=f"trace_id={phase_run.trace_id}",
        )
        raise AssertionError("unreachable")  # noqa: TRY003 (xfail 之前 raise 不会真执行)
    assert llm_rows[0].versions.harness_v
```

### 跑完一波 → fix-batch 模式

```
phase-1 跑 18 tests → 12 pass + 6 xfail(record_and_continue 记 finding)
   ↓
出 RESULTS.md 总账:
   - 0 blocker
   - 1 serious(PHASE-1-001 K0)
   - 4 minor
   - 1 nit
   ↓
alert_level: needs_human_batch_review → mention user
   ↓
User 看 brief → ping architect:"起 phase-1 fix SPEC, closes 001/003/005/007;013/019 关闭"
   ↓
Architect 起 fix-batch-2 SPEC(4 个 fix sub-task,各 ~300 行 SPEC)
   ↓
User ack → main session merge SPEC → 4 路并行 spawn dev session
   ↓
4 PR auto_merged → phase-1 rebase 重跑 → 0 finding 收敛 → 进 phase-2
```

### 实战出处

harness phase-1-bootstrap 18 tests fail-greedy 一次跑完,记 6 finding → fix-batch-2 4 路并行 ~3h critical path(serial 估 ~10h)。**3 倍加速**。

---

## 实操 Checklist:加多 agent 协作时

- [ ] 3 角色 + worktree 物理隔离 + 模型隔离
- [ ] 全靠文件 + git 跨 session 通信(不假设能 IPC)
- [ ] 主 session 用 `/loop` dynamic mode(自 pace 自醒)
- [ ] Dispatcher daemon 30s polling(3 path:alert / stuck / chain)
- [ ] 架构验证场景用 fail-greedy(record_and_continue helper)
- [ ] 撞 ≥1 blocker/serious 才 mention user(其余 daemon 兜底)

---

## 下一步

- [../prompts/01-main-session-loop.txt](../prompts/01-main-session-loop.txt) — 主 session /loop 完整 prompt
- [../tools/dispatcher.ps1](../tools/dispatcher.ps1) — Dispatcher daemon 完整实施
- [../templates/findings-protocol.py](../templates/findings-protocol.py) — record_and_continue helper
- [../examples/phase-1-fail-greedy-cycle.md](../examples/phase-1-fail-greedy-cycle.md) — 实战 phase-1 fail-greedy → fix-batch-2 完整周期
