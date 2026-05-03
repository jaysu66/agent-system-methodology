# 模块 1:任务切分到「单 agent 可执行」颗粒度

## 这个模块解决什么

你有一个大项目(几周到几个月),要拆成 agent 能独立做的 sub-task。常见痛点:

- ❌ 任务太大,agent 一次做不完,跑歪
- ❌ 任务边界模糊,agent 越界改不该改的
- ❌ sub-task 之间互相依赖,谁等谁不清楚
- ❌ 一个 sub-task 描述写得糊涂,agent 写出来跟你想的不一样

本模块给你 **4 个工具**:

1. **SPEC 12 段必备格式** — 让 sub-task 描述无糊涂空间
2. **单一职责切分原则** — 1-2 层 / 1 sub-task 的颗粒
3. **boundary check 反清单** — 防 agent 越权
4. **依赖图 + 并行度** — 决定哪些可以并行 spawn

---

## 1. SPEC 12 段必备格式

每个 sub-task 用 1 个 SPEC.md 描述,**12 段必备 + 每段非空**。完整模板见 [../templates/SPEC.template.md](../templates/SPEC.template.md)。

### 12 段速览

```
§1  一句话目标(≤ 50 字,读完知道要做啥)
§2  你是谁(给 dev agent 的角色 prompt)
§3  涉及的架构层(K0/K1/K2/...,选 1-2 层)
§4  关联文档必读清单(7-10 份)
§5  任务步骤(≥ 3 步,每步 1-2 行)
§6  验收标准(可粘贴 shell 命令的 13 工具 + 33 grep)
§7  依赖(谁等你 + 你等谁)
§8  产出物清单(精确文件路径 + 行数估)
§9  反清单(≥ 5 条,boundary check 用)
§10 Verifier 任务段(≥ 5 positive + ≥ 5 negative xfail)
§11 工作量估计(代码 + test + 工时)
§12 完成标志(可粘贴 bash,全过 = sub-task done)
```

### 为什么 12 段都重要

| 段 | 不写会怎样 |
|---|---|
| §1 一句话目标 | dev agent 跑歪方向 |
| §2 你是谁 | dev agent 行为不一致(每次不同) |
| §3 涉及层 | dev 改超出范围(违反原则 2) |
| §4 关联文档 | dev step 1 onboarding 上下文不全 |
| §5 任务步骤 | dev 跳过设计直接 implement |
| §6 验收 | dev 自检不全(L1 CI 漏过) |
| §7 依赖 | 上下游 chain 断 |
| §8 产出物 | dev 多写少写 |
| §9 反清单 | dev 越权(改 .github / contracts / pyproject ruff) |
| §10 Verifier | verifier 不知道审什么 |
| §11 工时 | user 估不准并行度 |
| §12 完成标志 | dev 不知道何时收尾 |

### 实战示例

完整 SPEC 例子见 [../examples/spec-fix-k5-observer.md](../examples/spec-fix-k5-observer.md)(harness 实战脱敏版)。

---

## 2. 单一职责切分原则

### 规则

- ✅ 一个 sub-task 只动 **1-2 个架构层**
- ✅ 一个 sub-task 只解 **1-3 个 finding**(fix-batch 模式)
- ✅ 一个 sub-task 只引入 **1 个新 contract / Protocol**
- ❌ 改 ≥ 3 层 → 必须拆
- ❌ 同 PR 改 contract + impl + 全套 test + docs → 太大,拆

### 怎么判断要不要拆

3 个问题:

1. **跨模块(layer)?** 改 ≥3 个模块的代码 → 拆
2. **跨阶段(phase)?** 一个 sub-task 涉及"加新接口" + "迁移已有 caller" + "废弃旧接口" → 拆 3 个
3. **跨 PR review 维度?** 既改算法 + 又改命名规范 + 又加新依赖 → 拆

### 实战示例

harness fix-batch-3 R2(3 个 SPEC,各 ~300 行):
- `fix-phase1-001-r2-facade-binds-adapter-ledger`(只动 K0 + facade)
- `fix-phase1-003-r2-facade-default-branch-checkpoint`(只动 K1 + facade)
- `fix-phase1-007-r2-tool-call-trace-id`(只动 K3 + 测试调用)

3 个全独立,Day 1 全 spawn,~3h critical path。

**反例**:某次 architect 把 K0 + K1 + K2 fix 写一个 SPEC,~1500 行 → dev 实施撞 contract collision → 拆成 3 个重写。

---

## 3. boundary check 反清单(SPEC §9)

### 规则

每个 SPEC §9 必须明文列 **≥ 5 条反清单**。L4b headless reviewer **强制优先于** 4 维度审跑 boundary check,任一命中直接 🔴 BLOCK。

### 标准反清单(必含 5 条)

```markdown
## §9 反清单(boundary check 用)

- [ ] ✗ 修改 `tasks/_contracts/` 任何文件(architect 领地)
- [ ] ✗ 修改 `.github/workflows/*` 任何文件
- [ ] ✗ 修改 `pyproject.toml` 的 `[tool.mypy*]` `[tool.ruff*]` `[tool.interrogate*]` `[tool.importlinter*]` 段
- [ ] ✗ 改其他 sub-task 的实施代码
- [ ] ✗ 33 条 CRITIQUE_HISTORY 修改约束:
  - ✗ datetime.utcnow()(用 utc_now)
  - ✗ print() 当 log(用 structlog / stdlib logging)
  - ✗ except Exception 静默吞错(必须 catch 具体异常)
  - ✗ raise Exception / RuntimeError(必须 raise 具体子类)
  - ✗ 直接 import anthropic / openai(走 adapter)
- [ ] ✗ 在 K 层使用业务名词(发票/客户/订单)— K 层 business-agnostic
- [ ] ✗ 同 PR 改 ≥ 2 个架构层
- [ ] ✗ 留 TODO/FIXME 到 main
```

### 例外授权机制

某些 sub-task **必须**改 contract(SPEC §8 钦定时):
- SPEC 显式写 "本 PR 例外授权改 X"
- User 明文 ack(`Q4=ACK` 这种)
- L4b boundary check prompt 加例外 case:"本 PR 是 fix-batch-N 第 M 号修复,SPEC §8 显式钦定改 governance_contract.py + tasks/_contracts/ mirror。前例:fix-k2 PR #26 改 memory_contract.py 是合法的(已 merged)"

### 实战出处

harness L4b GOTCHAS G1(实录):dev session 在 `pyproject.toml` 加 `[[tool.mypy.overrides]] module="contracts.*" ignore_errors = true` 试图绕 self-test fail。L4b boundary check 抓到 → 🔴 BLOCK → 退回。

---

## 4. 依赖图 + 并行度

### 规则

- 写 SPEC §7 标明:"你依赖什么" + "谁依赖你"
- 编排 daemon(dispatcher)读 PHASE_DEPS 决定何时 spawn
- 独立 sub-task **Day 1 全并行**(N 路 worktree + N 个 dev session)
- 有依赖的 serial chain

### 依赖图举例(harness fix-batch-3 R2)

```
fix-batch-3 SPEC PR(architect 写,user ack)
              ↓ merge
       ┌──────┼──────┐
       ↓      ↓      ↓     (3 个全独立,Day 1 全 spawn)
   001-r2  003-r2  007-r2
       ↓      ↓      ↓
       └──────┼──────┘
              ↓ 全 merged
       phase-1 rebase + 重跑
              ↓ 0 finding
       dispatcher spawn phase-2
              ↓
        phase-2 dev session
              ↓
            ...
```

### 怎么判断能不能并行

3 个问题:

1. **改不改同一个文件?** 改同文件 → serial(避免 git rebase 冲突)
2. **依赖同一个 contract 改动?** 是 → serial(下游等上游 contract merged)
3. **改完后下游需要 rebase 重跑?** 是 → serial(下游 spawn 等上游 done)

否则 → 并行。

### 实战出处

harness fix-batch-2 R1(4 个 SPEC):各动不同 K 层(K0/K1/K2/K3),无 contract 共享 → Day 1 全并行 spawn → critical path ~3h。

vs fix-batch-1(5 个 SPEC):有 SubscriptionHandle 共享依赖,fix-k2 必须先 done(写 contract)→ fix-k3-k4 / fix-k5 才能开始 → serial part + parallel part,critical path ~6-8h。

---

## 实操 Checklist:写 SPEC 时

- [ ] §1 一句话目标(≤ 50 字)
- [ ] §3 涉及 1-2 层(超 3 层 → 拆)
- [ ] §4 关联文档 7-10 份(让 dev step 1 onboarding 充分)
- [ ] §5 任务步骤 ≥ 3 步
- [ ] §6 验收标准可粘贴 shell 命令(13 工具 + 33 grep)
- [ ] §7 依赖图清晰(谁等你 / 你等谁)
- [ ] §8 产出物精确文件路径 + 行数估
- [ ] §9 反清单 ≥ 5 条(含 boundary + 33 约束)
- [ ] §10 Verifier 任务段 ≥ 5 positive + ≥ 5 negative
- [ ] §12 完成标志可粘贴 bash

---

## 下一步

- [../templates/SPEC.template.md](../templates/SPEC.template.md) — 12 段空白模板
- [../examples/spec-fix-k5-observer.md](../examples/spec-fix-k5-observer.md) — 实战 SPEC 例子
- [../02-skill-orchestration/README.md](../02-skill-orchestration/README.md) — SPEC 写完,SKILL 怎么编排 dev session
