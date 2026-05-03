# 架构总览(15 分钟读完)

## 1. 整体架构图

```
┌────────────────────────────────────────────────────────────────────┐
│                         User(决策者)                                │
│  - 看 brief 拍板("ack" / "选 A 选 B" / "Q1=D Q2=A Q4=ACK")         │
│  - 启动 /loop dynamic mode 后走开                                   │
│  - 偶尔 review architect SPEC PR(一字 ack)                         │
└────────────────────────────────────────────────────────────────────┘
                          ↑                  ↓
          (mention user 5 种情况)     (decision via chat)
                          ↑                  ↓
┌────────────────────────────────────────────────────────────────────┐
│              Main Session(/loop dynamic mode + ScheduleWakeup)      │
│                                                                     │
│  职责:                                                              │
│  - sanity review architect SPEC PR + 写 brief 给 user              │
│  - 代办 gh pr merge / git worktree add / spawn dev session         │
│  - 监控 N 路并行 dev session 状态                                  │
│  - 撞 finding 收集 → 整理 brief → mention user                    │
│  - 自醒间隔 15-60 min(密集期短/idle 期长)                          │
│                                                                     │
│  自代办的 5 种情况(不打扰 user):                                   │
│  1. dev session passive 等 verify trigger > 30 min → spawn verify │
│  2. architect SPEC PR sanity 后保存 brief                         │
│  3. dispatcher daemon crash → 重启                                │
│  4. 上游 merge 但 chain 没触发 → 手动 spawn 兜底                  │
│  5. 历史 worktree 卡 file lock → 趁 idle 清理                     │
│                                                                     │
│  mention user 的 5 种情况:                                          │
│  1. alert_level=needs_human_batch_review(撞 ≥1 blocker/serious)  │
│  2. alert_level=needs_human_design_review(关 5 round 5 没 converge) │
│  3. architect 修复 SPEC PR 出来等 user ack                        │
│  4. 一波工作完成,需要 user 决策推下一波                            │
│  5. CLI / API 全崩(3 路全错)                                       │
└────────────────────────────────────────────────────────────────────┘
       ↕ spawn(claude --print headless)         ↕ poll worktree state
┌──────────────────────────┐              ┌────────────────────────────┐
│  Architect Session        │              │  Dispatcher Daemon         │
│  (用户另开,独立 Claude)   │              │  (PowerShell 30s polling)   │
│                           │              │                             │
│  职责:                    │              │  职责:                      │
│  - 起 fix-batch SPEC PR  │              │  - stuck pattern 检测       │
│  - 解多 finding(集中修)  │              │  - chain auto-progression  │
│  - 决策修方向(option A/B) │              │  - LLM compliance bug 兜底 │
│  - self-criticism 入 PLAN │              │  - 历史 worktree cleanup   │
└──────────────────────────┘              └────────────────────────────┘
              ↕(SPEC PR 走 GitHub)                     ↕
┌────────────────────────────────────────────────────────────────────┐
│   Dev Session(claude --print 跑 SKILL §4 5-step)                    │
│   独立 worktree,只看自己 SPEC,看不到其他 sub-task 实施              │
│                                                                     │
│   1. /harness-dev freeze {track}      → SPEC.md → SPEC_FROZEN.md   │
│   2. step 1 onboarding                → UNDERSTANDING.md           │
│   3. step 2 PLAN                      → PLAN.md(≥3 决策 + ≥2 推翻) │
│   4. step 3 implement                 → 只动 SPEC §8 钦定文件      │
│   5. step 4 self-test                 → 13 工具全过                │
│   6. step 5 PR                        → commit + push + gh pr create│
│   7. step 5.5 L4b 自审                → 0 BLOCK approve            │
│   8. §6.5 verify                      → 跨模型 verifier            │
│   9. §6.4 §6.5 自动 revision          → max 3 轮                   │
│  10. §10 auto_approve 7-gate          → gh pr merge --squash       │
│  11. §6.3 archive                     → memory + commit + push     │
│                                                                     │
│   全程 0 user 介入(除非撞 4 mention 情况)                          │
└────────────────────────────────────────────────────────────────────┘
       ↕ verify spawn(独立 worktree + 跨模型)
┌────────────────────────────────────────────────────────────────────┐
│   Verifier Agent(强制 ≠ Dev Agent 模型)                             │
│   独立 worktree(workbench-verifier-{X}),物理删除 dev impl          │
│                                                                     │
│   优先 codex/gpt-5.5 → cascade fallback claude/opus-4.7            │
│                                                                     │
│   1. Read-only Onboard(只读 SPEC + contracts,不读 dev impl)        │
│   2. Independent Test(写 verifier_test.py ≥5 positive + ≥5 xfail)  │
│   3. Run on Dev Impl(checkout dev impl + 跑 verifier_test)         │
│   4. Report(verifier_report.md 7 段 + ≥5 可疑点)                   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据流(一个 sub-task 完整生命周期)

```
[Architect] 写 SPEC.md(12 段必备)
    ↓
[User] sanity check + ack
    ↓
[Main Session] gh pr merge SPEC + git worktree add + spawn dev session
    ↓
[Dev Agent] freeze SPEC(sha256 lock)
    ↓
[Dev Agent] step 1 读 7 共享上下文 + 写 UNDERSTANDING.md
    ↓
[Dev Agent] step 2 写 PLAN.md(≥3 设计决策 + ≥2 推翻方案)
    ↓
[Dev Agent] step 3 implement(只动 SPEC §8 钦定文件)
    ↓
[Dev Agent] step 4 self-test(ruff/mypy/interrogate/bandit/pip-audit/pytest unit/contract/conformance + grep 反清单)
    ↓
[Dev Agent] step 5 commit + push + gh pr create
    ↓
[Dev Agent] step 5.5 L4b headless claude --print 自审 PR
    ↓
[GitHub Actions] L1 CI(Static Quality + Contracts Import)
    ↓
[Dev Agent] §6.5 verify spawn(独立 worktree + cascade fallback)
    ↓
[Verifier Agent] verdict: pass / needs_revision / reject
    ↓
   ├── pass + 7-gate 全过 → §6.3 auto_merge + archive
   ├── needs_revision → §6.5 L2 revision round 1 fix → 重 verify
   └── reject → max_l2_rounds 用尽 → mention user
    ↓
[Dev Agent] gh pr merge --squash + delete branch
    ↓
[Dev Agent] 写 HANDOFF.md + .agent-memory/SESSIONS/ + commit + push
    ↓
[Dispatcher Daemon] 检测到 sub-task done → 看 PHASE_DEPS chain → spawn 下游 sub-task
    ↓
[循环回 Architect / Dev]
```

---

## 3. 关键设计决策(为什么这么搭)

### 决策 1:为什么 Architect / Dev / Verifier 必须独立?

**问题**:同一个 agent 既写 SPEC 又写代码,会产生「自己证明自己对」的偏见 — 它会绕过 SPEC 不严谨的地方,验收时也不会发现。

**方案**:
- Architect:只写 SPEC,不接触实施代码
- Dev:只看 SPEC + 上游 HANDOFF,不看 SPEC 草稿
- Verifier:只读 SPEC + contracts,**物理删除** dev 实施 + 用**不同模型**(codex 不是 claude)

**实战验证**(harness):17 PR 跑 verifier 跨模型 cross-check,抓到 11 类 dev 没自检出的问题(SP-X 命名约定)。

### 决策 2:为什么用 5-step 强制流程?

**问题**:agent 接到 prompt 一上手就写代码 → 跳过设计思考 → 写出来不对要重写。

**方案**:强制 step 1 onboarding(读 7 份上下文 + 写"我理解的任务" 200 字)+ step 2 PLAN(列 ≥3 设计决策 + ≥2 推翻过的方案)。这两步逼 agent 把思考过程写出来,后面才能 implement。

**实战验证**:跳过 step 1-2 直接 implement 的 sub-task 平均 round 2-3 才收敛;严格走 5-step 的平均 round 0-1 收敛。

### 决策 3:为什么 auto_approve 要 7-condition AND-gate?

**问题**:单点验收(只看 CI)容易漏 — agent 写假 test,CI 全绿但代码烂。

**方案**:7 条 **AND** 全过才 merge:
1. L1 CI ✓(GitHub Actions)
2. L4b 0 BLOCK(本地 claude 跨提示审)
3. L2 verdict=pass(独立 verifier 跨模型审)
4. L2 0 blocks(verifier 5+ 可疑点都不算 BLOCK)
5. boundary_check_passed(没改 contracts/.github/pyproject ruff 段)
6. revision_round ≤ max(3 轮没收敛 mention user)
7. l2_revision_round ≤ max(同上)

任一 fail → 不 merge,走 revision 闭环 max 3 轮。

**实战验证**:30+ PR auto_merged,**0 误 merge**。boundary check 拦截 2 次 dev 越权(改 mypy ignore_errors 绕过 self-test fail)。

### 决策 4:为什么需要 Dispatcher Daemon?

**问题**:LLM 不 100% 听 SKILL prompt:
- 形态 (a) passive 等 trigger:dev step 5 push 完不自调 verify
- 形态 (b) 问 user 中间决策:dev step 1 死等 stdin
- 形态 (c) PROGRESS.md 写非标值:dispatcher regex 不识别
- 形态 (d) verify session 卡 cascade fallback 决策

**方案**:PowerShell 30s polling tools/watcher/dispatcher.ps1,catch stuck patterns → 自动 `claude --print "/harness-dev verify {track}"` 兜底 spawn。

**实战验证**:Phase 1.5 17 sub-task,**5 路被 dispatcher 兜底成功**(LLM compliance bug 实战频率约 30%)。

### 决策 5:为什么 fix-batch 集中修复?

**问题**:phase 验证撞 finding 立修 → 改一处影响多处 → 改完一波又撞新 finding → 死循环。

**方案**:**fail-greedy 协议** — 测试套撞 finding 不停继续记(record_and_continue helper),跑完一波出 RESULTS.md → architect **集中起 fix-batch SPEC**(一次解多 finding)→ user ack → 多路并行 dev session 修 → rebase 重跑。

**实战验证**:fix-batch-2 4 路并行 ~3h critical path(serial 估 7-10h);fix-batch-3 R2 同模式 0 revision 一次过。

---

## 4. 8 大核心组件

| 组件 | 职责 | 实现 |
|---|---|---|
| **SPEC** | 单 sub-task 的"任务说明书" | 12 段必备 markdown,sha256 frozen |
| **SKILL** | 编排 dev 5-step 工作流 | ~/.claude/skills/X/SKILL.md |
| **Worktree** | 物理隔离 dev / verifier | git worktree add |
| **PROGRESS.md** | sub-task 状态机(checkpoint) | YAML frontmatter + step ledger |
| **L4b headless review** | 走 user Max 订阅 0 额外费 | claude --print 启动 sub session 审 PR |
| **Cross-model verifier** | 防单模型偏见 | codex 优先 → cascade opus |
| **Dispatcher daemon** | LLM compliance bug 兜底 | PowerShell 30s polling |
| **/loop monitoring** | 主 session 自醒 | dynamic mode + ScheduleWakeup |

---

## 5. 你不需要全部 component

最小可用配置(只要 sub-task 跑通):
- ✅ SPEC + SKILL + Dev Agent + L1 CI
- ❌ 跳过 Verifier / Dispatcher / L4b(质量靠 dev 自检 + CI)

完整配置(长跑高质量):
- ✅ 全部 8 个

**渐进采用**:先 minimal 跑通几个 sub-task,撞质量问题再加 Verifier;撞长跑卡死再加 Dispatcher;撞主 session 不在再加 /loop。

---

## 下一步阅读

- [core-principles.md](core-principles.md) — 8 个核心原则的详细解释
- [../01-task-decomposition/README.md](../01-task-decomposition/README.md) — 任务切分细节
- [../case-study-harness/timeline.md](../case-study-harness/timeline.md) — 实战 100h 时间线
