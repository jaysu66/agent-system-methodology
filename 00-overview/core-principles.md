# 8 个核心设计原则

每条原则都来自 harness v3 ~100h 实战。包含**原则陈述 + 反例 + 实战出处**。

---

## 原则 1:3 角色严格隔离(User / Architect / Dev+Verifier)

### 陈述

3 类 agent 必须**物理 + 模型隔离**:
- **User**:决策者,拍板 ack/reject
- **Architect**:写 SPEC,不接触实施代码
- **Dev**:看 SPEC + 上游 HANDOFF,不写 SPEC
- **Verifier**:只读 SPEC + contracts,**物理删除 dev 实施**,**用不同模型**

### 反例

❌ 同一个 Claude session 既写 SPEC 又写代码 → 自己证明自己对,SPEC 不严谨处被绕过。

❌ Verifier 跟 Dev 同模型(都 claude/opus) → 模型同质化偏见,verifier 看不出 dev 漏洞。

### 实战出处

harness PR #25(fix-k1)round 1 squash-merge 时 codex L2 verifier spawn fail,**直接 merge 没等 verify**。后来 cascade fallback 到 opus 跑出 verdict=needs_revision + 1 BLOCKER + 3 应修。这是「verifier 缺位」的代价 — PR #37 后续补 4 件事(B1+R1+R2+R3)。

---

## 原则 2:单一职责切分(1-2 层 / 1 个 sub-task)

### 陈述

一个 sub-task 只动 **1-2 个架构层**(K0 Adapter / K1 Runtime / K2 Memory / K3 Action / ...)。3 层以上必须拆。

### 反例

❌ "改 K0 + K1 + K2 + 加 test" 一个 sub-task → 改完撞测试不过,不知道哪层错。

❌ "顺手把 K3 也优化一下" → boundary 模糊,reviewer 看不清。

### 实战出处

harness Phase 1 17 sub-task 全部严格 1-2 层。fix-batch-1 5 个 fix sub-task 各只解 1 个 finding,各动 1 层 K-layer + tests。**0 跨层污染**,boundary check 100% 命中。

---

## 原则 3:boundary check 反清单(防越权)

### 陈述

每个 SPEC §9 必须明文写**反清单**(≥ 5 条),列出 dev agent 禁止改的文件:
- ❌ `tasks/_contracts/`(architect 领地)
- ❌ `.github/workflows/`
- ❌ `pyproject.toml` 的 `[tool.mypy*]` `[tool.ruff*]` 等工具配置段
- ❌ 其他 sub-task 的实施代码
- ❌ 33 条 CRITIQUE_HISTORY 修改约束(`datetime.utcnow` / `print(` / `except Exception` 等)

L4b headless reviewer 强制跑 boundary check **优先于** 4 维度审,任一命中直接 🔴 BLOCK。

### 反例

❌ "顺手把 mypy ignore_errors 改成 True 让 self-test 过" → 用工具配置绕过架构约束,偷懒。

❌ "我把这个 contract 加个字段就好了" → contract 是 architect 领地,dev 不能改。

### 实战出处

harness L4b GOTCHAS G1 实录:某次 dev 在 `pyproject.toml` 加 `[[tool.mypy.overrides]] module="contracts.*" ignore_errors = true` 试图绕 self-test fail。L4b boundary check 抓到 → 🔴 BLOCK → 退回 dev 重写。

---

## 原则 4:5-stage 验收(L1 + L2 + L3 + L4a + L4b)

### 陈述

PR 必须过 5 路审查才能 merge:

| 路 | 审什么 | 谁跑 |
|---|---|---|
| **L1 CI** | ruff/mypy/pytest 静态质量 | GitHub Actions |
| **L2 Verifier** | 算法正确性 + SPEC 符合度 | 独立 worktree 跨模型(codex / opus) |
| **L3 Conformance** | 全 18 conformance test 不 regress | pytest -m conformance |
| **L4a Codex Cloud** | 设计 + 维护性 + 一致性(可选)| codex bot 评论 |
| **L4b Local Claude** | boundary + 4 维度审 | claude --print headless |

### 反例

❌ 只看 L1 CI → 写假 test 也能过。

❌ 只 dev 自审 → 自己证明自己对。

### 实战出处

harness 30+ PR 全 5 路审。L4b 抓到 11 类 dev 自检漏的问题(命名不规范 / docstring 缺 / 错误处理裸 raise)。L2 跨模型抓到 6 类 L4b 漏的(算法逻辑错 / SPEC 字段名误用)。

---

## 原则 5:auto_approve 7-condition AND-gate(自动 merge 决策)

### 陈述

7 条 AND-gate **全部满足才** auto_merge:

```
L1_ci_passed ✓ AND
L4b_block_count == 0 AND
L2_verdict == "pass" AND
L2_blocks_count == 0 AND
boundary_check_passed AND
revision_round <= max_rounds (3) AND
l2_revision_round <= max_l2_rounds (3)
→ AUTO_APPROVE_FIRES → gh pr merge --squash
```

任一 fail → 不 merge,走 §6.4 §6.5 revision 闭环。

### 反例

❌ "L4b 1 个 SUGGEST 也算 BLOCK,不 merge" → SUGGEST 不阻塞,只 BLOCK 阻塞。

❌ "verify 跑完先 ping user 再 merge" → 7-gate 全过应该 0 介入 merge。

### 实战出处

harness 30+ PR auto_merged,**0 误 merge**。fix-k5 PR #30 round 1 verifier 出 1 BLOCK SP-1(tz-aware @field_validator missing) → 7-gate fail → §6.5 revision round 1 fix → round 2 verdict=pass → 7-gate 全过 → auto_merge。

---

## 原则 6:跨模型 verifier(防单模型偏见)

### 陈述

L2 Verifier 必须用**不同于 Dev 的模型**。优先级:
1. codex/gpt-5.5(最理想,跨模型族)
2. claude/opus-4.7(同族不同模型,fallback)

cascade fallback:`codex login fail || quota exhausted` → 自动切 opus。

### 反例

❌ Dev 跑 claude,Verifier 也跑 claude → 同质化偏见。

❌ codex 401 直接 abort → 应该 cascade opus 兜底。

### 实战出处

harness 7 次 codex 401(token 失效 / quota / refresh_token_reused),**全部 cascade fallback opus 成功**。fix-k5 PR #30 verifier round 1 + fix-batch-3 R2 PR #41 都是 codex spawn fail → opus pickup → verdict 出来。

---

## 原则 7:fail-greedy 协议(架构验证场景)

### 陈述

跑**架构验证测试套**时(不是改代码),撞 architecture bug **不停继续记**:

```python
try:
    assert ledger.has_row(operation=Operation.LLM_CALL)
except AssertionError as exc:
    record_and_continue(
        phase=1,
        finding_id="001",
        severity="serious",
        error=exc,
        root_cause_tag="k0-adapter-no-ledger",
        suspect_layer="K0",
    )
    pytest.xfail(reason="recorded as PHASE-1-001")
```

helper 自动:
- append `_LEDGER.md` 一行
- 写 `PHASE-N-XXX.md` 个体 finding 文件
- 调 `pytest.xfail()` 让测试不 fail
- phase 继续往下跑下一个 test

跑完一波出 RESULTS.md 总账 → architect **集中**起 fix SPEC(fix-batch 模式)。

### 反例

❌ 测试撞 fail 立 raise → phase 卡死,只能修 1 个再跑下个,效率低。

❌ 用 try/except 静默吞错 → 信息丢失,后期 debug 难。

### 实战出处

harness phase-1-bootstrap 18 tests 一次跑完,记 6 finding(1 serious + 4 minor + 1 nit)→ architect 起 fix-batch-2(4 个 fix SPEC 并行)→ critical path ~3h(serial 估 ~10h)。

---

## 原则 8:defense-in-depth(全链防御 ≠ 单点保护)

### 陈述

LLM compliance bug 是事实(实战 30% 概率),靠**多层防御**而非"加 prompt 强制":

```
Layer 1: SKILL prompt 写"自动闭环铁律"(80% 听话)
Layer 2: dispatcher daemon 30s polling 兜底(catch stuck pattern)
Layer 3: /loop dynamic mode 主 session 监控(catch LLM 行为级异常)
Layer 4: User 偶尔 mention(撞 4 mention 情况才打扰)
Layer 5: max_rounds 配额(防死循环)
Layer 6: cascade fallback(防单模型 fail)
Layer 7: cross-model L2(防单模型偏见)
Layer 8: boundary check(防越权)
```

### 反例

❌ "再加更严格 prompt 约束" → LLM 还是 30% 不听。

❌ "100% 靠 prompt 保证" → 每次撞 bug 都是 user 介入,长跑必崩。

### 实战出处

harness Phase 1.5 17 sub-task,**5 路被 dispatcher daemon 兜底成功**(LLM 在 prompt 严格条件下仍 passive 等 trigger / 问 user 中间决策 / PROGRESS 写非标值 / cascade 卡决策)。**没有 daemon,这 5 路都会卡 user 介入。**

---

## 8 原则速查卡片

```
1. 3 角色隔离      User / Architect / Dev+Verifier 物理 + 模型分开
2. 单一职责切分    1 sub-task 只动 1-2 层架构
3. boundary check  SPEC §9 反清单 ≥5 条 + L4b 优先审
4. 5-stage 验收    L1 + L2 + L3 + L4a + L4b 全过
5. auto_approve    7-condition AND-gate 全过 才 merge
6. 跨模型 verifier codex 优先 → opus cascade fallback
7. fail-greedy     测试套撞 bug 不停继续记 → fix-batch 集中修
8. defense-in-depth 多层防御 ≠ 单点保护(LLM 不 100% 听话)
```

---

## 下一步

- 模块 1[01-task-decomposition](../01-task-decomposition/README.md) 看任务切分实操
- 模块 2[02-skill-orchestration](../02-skill-orchestration/README.md) 看 SKILL 怎么写
- 模块 3[03-quality-gates](../03-quality-gates/README.md) 看 5-stage 验收实操
- 模块 4[04-multi-agent-coordination](../04-multi-agent-coordination/README.md) 看多 agent 协作
