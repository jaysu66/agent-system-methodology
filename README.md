# Agent System Methodology

让 AI agent 长时间自主运行 + 产出生产级代码质量的通用方法论。

抽象自 **harness v3 项目 ~100h 实战**(30+ PR auto-merged,5 fix-batch,5 phase 架构验证,7 类 LLM compliance bug 实战兜底)。

---

## 这套方法解决什么

你想让 AI 帮你自主开发一个**中长期项目**(1 周以上、几十个 sub-task、需要架构稳定性)。但你撞过这些痛点:

- ❌ 任务一大,agent 跑歪、跑偏、写出来一堆糊弄事
- ❌ 一句话指令交给 agent,产出物质量参差不齐
- ❌ Agent 跑着跑着卡在某一步,passive 等你输入
- ❌ Agent 自检 + 自审 = 自己证明自己对(没真验收)
- ❌ Agent 越权改不该改的(架构层 / 测试 config / CI 文件)
- ❌ 多个 agent 协作互相看不见,状态丢失
- ❌ 你不在,系统就停了

这套方法系统性解决以上所有问题。

---

## 核心思路(一句话)

> **把任务拆到「单 agent 可独立执行」,用「多重审查 + 自动闭环」保证质量,用「主 session 监控 + daemon 兜底」保证长跑。**

3 个独立 agent 角色 + 1 个 daemon + 1 个编排 SKILL,7 项核心机制:

```
User(决策)
  ↕
Architect(写 SPEC)              Main Session(我,/loop 监控)
  ↕                                     ↕
Dev Agent(实施)  ←  SKILL 编排  →   Verifier Agent(独立验收)
                       ↕
                Dispatcher Daemon(30s polling 兜底)
```

---

## 4 大模块

| 模块 | 解决 | 核心文档 |
|---|---|---|
| **[01 任务切分](01-task-decomposition/README.md)** | 怎么把项目拆成 agent 能独立做的 sub-task | SPEC 12 段格式 / 单一职责 / boundary check / 依赖图 |
| **[02 SKILL 编排](02-skill-orchestration/README.md)** | 怎么让 agent 自跑 0 介入到完成 | 5-step 工作流 / 自动闭环铁律 / checkpoint 恢复 |
| **[03 质量保证](03-quality-gates/README.md)** | 怎么用多重审查保证代码质量 | 5 路审查 / auto_approve 7-gate / revision 闭环 |
| **[04 多 agent 协作](04-multi-agent-coordination/README.md)** | 怎么让多个 agent 长时间稳定协作 | 3 角色隔离 / 文件 IPC / /loop 监控 / fail-greedy 协议 |

---

## 8 个核心设计原则

详见 [00-overview/core-principles.md](00-overview/core-principles.md):

1. **3 角色隔离** — User 决策 / Architect SPEC / Dev+Verifier 独立执行
2. **单一职责切分** — 一个 sub-task 只动 1-2 层架构
3. **boundary check** — 反清单防越权
4. **5-stage 验收** — L1 CI + L2 Verifier + L3 Conformance + L4a + L4b
5. **auto_approve 7-gate** — 全过才自动 merge
6. **跨模型 verify** — codex/gpt-5.5 + opus 4.7 cascade fallback
7. **fail-greedy 协议** — 测试套撞 bug 不停继续记
8. **defense-in-depth** — daemon 兜底 + max_rounds 配额 + checkpoint 恢复

---

## 实战来源:harness v3 项目

详见 [case-study-harness/README.md](case-study-harness/README.md)

**数据**:
- 100+ 小时实战
- 30+ PR auto-merged(0 误 merge,boundary check 100% 命中)
- 17 个原计划 v5 架构 track + 14 个 Phase 1.5 验证 sub-task
- 5 轮 fix-batch(集中修复期)
- 7 种 LLM compliance bug 实战兜底
- ~10h user 实际介入(其余全自动)

**架构验证**(Phase 1.5 phase-1 → phase-5):
- phase-1-bootstrap → 撞 6 finding → fix-batch-2 R1(4 个) → fix-batch-3 R2(3 个) → fix-batch-4 R3(SQLite lock) → 1 行 K3 fix → 0 finding 收敛
- phase-2-correctness → 撞 4 finding → fix-batch-5(纯架构决策修复)→ ...

---

## 怎么开始用

### 场景 A:你有一个新项目,从 0 开始

1. 读 [00-overview/architecture-overview.md](00-overview/architecture-overview.md) 理解全貌(15 min)
2. 跟着 [01-task-decomposition](01-task-decomposition/) 写第一个 SPEC
3. copy `prompts/02-dev-session-spawn.txt` 调你的 dev session
4. 跟着 4 模块逐步搭建

### 场景 B:你有一个 in-progress 项目,卡在质量/长跑问题

1. 读 [03-quality-gates](03-quality-gates/) 加多重审查
2. 读 [04-multi-agent-coordination/main-session-loop-monitor.md](04-multi-agent-coordination/main-session-loop-monitor.md) 启动 /loop 监控
3. 读 [lessons-learned/](lessons-learned/) 避坑

### 场景 C:你想理解为什么这么设计

1. 读 [case-study-harness/timeline.md](case-study-harness/timeline.md) 看实战演进
2. 读 [00-overview/core-principles.md](00-overview/core-principles.md) 理解每条原则的实战出处

---

## 仓库结构

```
agent-system-methodology/
├── README.md                          ← 本文件
├── 00-overview/                       ← 总览 + 核心原则 + 架构图
├── 01-task-decomposition/             ← 模块 1:任务切分
├── 02-skill-orchestration/            ← 模块 2:SKILL 编排
├── 03-quality-gates/                  ← 模块 3:质量保证
├── 04-multi-agent-coordination/       ← 模块 4:多 agent 协作
├── templates/                         ← 8 个 .template 文件(SPEC/PLAN/PROGRESS/SKILL...)
├── prompts/                           ← 6 个 agent 启动 prompt(可直接 copy 用)
├── tools/                             ← dispatcher.ps1 等实操脚本
├── examples/                          ← 实战示例(脱敏 SPEC + PR cycle)
├── lessons-learned/                   ← 7 个验证过的教训(LLM bug + API timeout 等)
└── case-study-harness/                ← harness v3 实战回顾(数据 + 时间线)
```

---

## License

MIT — 你随便拿去改、商用、做分享。如果有改进,欢迎 PR。

---

## 致谢

- harness v3 项目实战(2026-04 ~ 2026-05)
- Claude Code(Anthropic)
- Codex CLI(OpenAI)
- 所有踩过坑的 LLM compliance bug
