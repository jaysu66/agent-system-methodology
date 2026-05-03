# Self-Criticism Pattern(防 architect 重蹈覆辙)

## 核心规则

> **每个 fix-batch / phase 完成后,architect 在 PLAN.md §X 写 "self-criticism" 段,反思本批起草 SPEC 时撞的什么错,纠正措施是什么。**

让下一波不重蹈覆辙。

---

## 为什么需要

LLM 写 SPEC 不是确定性的。同一个 architect session 跨多个 fix-batch,会反复犯同类错(比如忘记 cross-reference HANDOFF 的 deferred 决策)。

如果不显式写 self-criticism,下次再撞 → user 又得 ping architect → 又一轮 fix-batch。

实战 harness:fix-batch-2 SPEC 起草时把"caller 必须传 ledger/trace_id"当 acceptable backward-compat → fix-batch-2 跑完撞 phase-1 K0/K1/K3 fix 没生效 → fix-batch-3 R2 又来一轮。如果 fix-batch-2 PLAN 写了 "self-criticism: 默认行为应让 caller 不传也 work,显式传是高级用法",fix-batch-3 R2 就不会撞同类错。

---

## 模板

每个 fix-batch / phase PLAN 加 §X "self-criticism" 段:

```markdown
## §X Self-Criticism + 纠正(防重蹈)

### 本批撞的错

(1-3 段反思,具体到事例)

写本批 SPEC 时撞 X 错(具体案例:fix-batch-N round Y 撞 finding Z)。
原因是 W(具体 root cause)。
当时没考虑 V(具体技术原因)。

### 纠正措施

(明文写下次怎么避免)

1. 起草下批 SPEC 时,**必须** cross-reference {具体文档段落}
2. 加 SUB_TASK_AUTHORING.md §M 必读清单这条
3. 后续单开 architect SPEC 落地纠正(给 trigger:Phase 2 业务层启动时)

### 已记 PENDING_FOR_ARCHITECT.md

(把 deferred 的纠正写进 .agent-memory/PENDING_FOR_ARCHITECT.md 防丢)

- {纠正条目 1}
- {纠正条目 2}
```

---

## 实战示例(harness fix-batch-3 R2 PLAN §7)

```markdown
## §7 Self-Criticism + 纠正(防重蹈)

### 本批撞的错

写 fix-batch-2 SPEC(R1)时,把 "caller 必须传 ledger=/branch_checkpoint=/trace_id="
当 acceptable backward-compat。文档层正确,实操错 — phase-1 dev 不会主动更新写在前面的
minimal_agent。

R1 实施实际是对的(adapter 写 LLM_CALL / runtime 接 branch_checkpoint kwarg /
tool_registry 同步 await),但 phase-1 minimal_agent.py 是 fix-batch-2 SPEC 存在
之前写的,assembly 没更新 → fix 没生效 → phase-1 撞 K0/K1/K3 仍 xfail → 又一轮
fix-batch-3。

### 纠正措施

**默认行为应该让 caller 不传也能工作,显式传是高级用法**。这条记进 PLAN §7
self-criticism,后续起草修复 SPEC 避免重蹈。

具体执行:
1. 起草 SPEC §3 (步骤段) 时,必须问"caller 不显式传该参数,会发生什么?"
2. 答 "raise" / "warn-once with fallback" / "auto-bind from facade":
   - 如答 "raise" → 文档层加 deprecation,但实施层应有 default 兼容
   - 如答 "warn-once with fallback" → 必须在 SPEC §6 验收加 "fallback 路径
     test"(不只测显式传)
   - 如答 "auto-bind from facade" → 必须有 model_validator + isinstance check

### 已记 PENDING_FOR_ARCHITECT.md

- 起草任何"caller 接口变更" SPEC,必须 cross-reference 现有 caller 用法
  (grep usage),评估是否 backward-compat
```

---

## 实战示例 2(harness fix-batch-5 PLAN §8)

```markdown
## §8 Self-Criticism + 纠正(防重蹈)

### 本批撞的错

写 phase-2 SPEC 时没 cross-reference governance-sandbox HANDOFF §4.1 的 deferred
决策,自己跟自己打架。

phase-2 SPEC §5.3 钦定 sandbox network block 测,期望 SkillSandbox 真实施 seccomp /
namespace。但 governance-sandbox HANDOFF §4.1 早已钦定 sandbox isolation 是 Phase 2
业务层的事,phase-2-correctness 不该越界。

phase-2 dev session 跑完撞 2 serious finding(network block 没 enforce),根本原因
是 architect SPEC 跟自己的 HANDOFF 打架,不是 K5 实施问题。

### 纠正措施

**每个 phase 验证 SPEC 起草必须 cross-reference 该 phase 触及的所有 K 层 HANDOFF
"已知限制 / deferred 决策"段**。

具体执行:
1. SUB_TASK_AUTHORING.md §4 必读清单加这条
2. 起草 phase 验证 SPEC 时,跑 `grep "deferred\|已知限制\|known limit" tasks/track-*/HANDOFF.md`
   收集所有 deferred 决策
3. SPEC §5 步骤段必须明文标 "本 phase 不验 X(已 deferred per HANDOFF §Y.Z)"

### 已记 PENDING_FOR_ARCHITECT.md

- SUB_TASK_AUTHORING.md §4 必读清单加 "phase SPEC 必 cross-ref HANDOFF deferred"
  这条,后续单开 architect SPEC 落地
- Phase 2 业务层 enabling SPEC 真做 seccomp/namespace(trigger:Phase 2 业务层启动时)
```

---

## PENDING_FOR_ARCHITECT.md(deferred 收集站)

`.agent-memory/PENDING_FOR_ARCHITECT.md` 是 architect deferred 决策的收集站:

```markdown
# Pending for Architect

> 本 sub-task / phase 撞但 deferred 的事,收集在这。
> 防 forever deferred:每条必有 trigger(什么时候真做)。

## 1. {主题}

- **来源**:fix-batch-{N} PLAN §X self-criticism / track-{X} HANDOFF §Y deferred
- **决策**:本 phase 不做(理由:...)
- **Trigger**:Phase 2 业务层启动时 / 撞 ≥3 个用户报告同类 bug 时 / 等
- **预估工时**:~Xh

## 2. {主题}

...
```

---

## 防 forever deferred

❌ "deferred 留着以后再说" — 容易忘。

✅ **每个 deferred 必有明确 trigger**(Phase 2 启动 / 用户报告 / 项目周年 / ...)

✅ **PENDING_FOR_ARCHITECT.md 跟 SPEC 一起 review**(下波 fix-batch 时跑 grep 看是否触发 trigger)

---

## 速查卡

```
1. 每 fix-batch / phase PLAN 加 §X "Self-Criticism + 纠正"
2. 反思具体撞了什么错(不要"我们要更小心")
3. 纠正措施明文写(下次怎么避免)
4. deferred 写进 PENDING_FOR_ARCHITECT.md
5. 每条 deferred 必有 trigger
6. 下波起 fix-batch 前 review PENDING(看是否触发)
```
