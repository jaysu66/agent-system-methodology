# 模块 3:多重审查 + 自动 merge 决策

## 这个模块解决什么

你怎么保证 agent 写出来的代码**真的对**?

常见痛点:
- ❌ 只看 L1 CI(ruff/pytest)→ 写假 test 也能过
- ❌ Agent 自审 → 自己证明自己对
- ❌ 单模型 verify → 同质化偏见
- ❌ 撞 fail 直接 reject → 应该自动 revision 闭环
- ❌ 全过了不知道何时自动 merge

本模块给你 **4 个机制**:

1. **5 路审查链**(L1 + L2 + L3 + L4a + L4b)
2. **跨模型 Verifier**(防单模型偏见)
3. **auto_approve 7-condition AND-gate**
4. **revision 闭环**(max 3 轮 + 配额)

---

## 1. 5 路审查链

### 总览

| 路 | 审什么 | 谁跑 | 决定性 |
|---|---|---|---|
| **L1 CI** | 静态质量(ruff/mypy/pytest unit/contract) | GitHub Actions | 必过 |
| **L2 Verifier** | 算法正确性 + SPEC 符合度 | 独立 worktree + 跨模型 | 必过 |
| **L3 Conformance** | 全 conformance test 不 regress | pytest -m conformance | 必过 |
| **L4a Codex Cloud** | 设计 + 维护性 + 一致性 | codex bot 评论(可选) | nice-to-have |
| **L4b Local Claude** | boundary + 4 维度审 | claude --print headless | 必过 |

### L1 CI(GitHub Actions)

最快 + 最便宜。`.github/workflows/static-quality.yml`:

```yaml
name: Static Quality (L1)
on: [push, pull_request]
jobs:
  static-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e packages/X
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy --strict src/
      - run: interrogate --fail-under 100 src/
      - run: bandit -r src/
      - run: pip-audit
      - run: pytest -m unit --cov-fail-under=80
      - run: pytest -m contract
```

`.github/workflows/contracts-import.yml`:
```yaml
name: Contracts Import Test
jobs:
  test:
    steps:
      - run: python -c "import contracts; contracts.validate_all()"
```

### L2 Verifier(关键 — 详见第 2 节)

### L3 Conformance(整套不 regress)

```bash
pytest -m conformance --tb=short > conformance_results.txt
```

Conformance test 是**跨 sub-task 的契约测试**(a1 a2 a3 a4 a5 / b1 b2 / c1 c2 c3 c4 c5 c6 / ...)。每个 sub-task PR 必须不让任何 conformance test 从 PASS 变成 FAIL。

### L4a Codex Cloud(可选 — webhook 不可靠)

当年规划的"GitHub PR webhook 触发 codex bot 评论"。实测 webhook 不稳(harness 实战 4 次 push 0 评论),改成**可选**,有就计入,没就跳过。

### L4b Local Claude(走 user Max 订阅 0 额外费)

详见 [../02-skill-orchestration/README.md](../02-skill-orchestration/README.md) Step 5.5。

**核心优势**:不需要 OAuth secret / GitHub workflow / 额外 API key。Dev session 自调 `claude --print` headless 启动 sub session 审 PR,走 user 个人 Max 订阅 quota,**0 额外费用**。

---

## 2. 跨模型 Verifier(防单模型偏见)

### 为什么必须跨模型

Dev 用 claude/opus 写代码 + Verifier 也用 claude/opus 审 → 同模型族同样的偏见,verifier 看不出 dev 漏的洞。

**实战教训**:harness PR #25 round 1 squash-merge 时 codex L2 verifier spawn fail,直接 merge 没等 verify。后来 cascade fallback 到 opus 才跑出 verdict=needs_revision + 1 BLOCKER + 3 应修。

### 模型级联(优先 codex,fallback opus)

```bash
# SKILL §5.1 模型级联
if command -v codex >/dev/null 2>&1 \
   && codex login status 2>&1 | grep -q "Logged in"; then
  spawn="codex exec"
  model_used="codex/gpt-5.5"
elif command -v claude >/dev/null 2>&1; then
  spawn="claude --print --model opus"
  model_used="claude/opus-4.7"
else
  abort "neither codex nor claude CLI available"
fi

PROMPT="$(cat verifier_prompt.txt)"
$spawn "$PROMPT" > tasks/track-{X}/verifier_run_log.md 2>&1
```

### Verifier 强制约束(SKILL §5)

**物理隔离**:
```bash
# 必须在独立 worktree
cd ../workbench-verifier-{X}/

# 物理删除 dev impl(verifier 看不到)
rm -rf packages/X/src/X/{你的层}/

# 物理删除 dev 自测
rm -rf packages/X/tests/unit/{你的层}/

# 物理删除 dev 思考过程
rm tasks/track-{X}/PLAN.md
rm tasks/track-{X}/UNDERSTANDING.md
rm tasks/track-{X}/PROGRESS.md
rm tasks/track-{X}/local_l4b_review*.md  # 防 verifier 看到 dev 自审
```

**只能读**:
- `tasks/track-{X}/SPEC_FROZEN.md`
- `contracts/*.py`
- `docs/DEV_SPEC.md`
- `docs/CRITIQUE_HISTORY.md` §9

### Verifier 4-step

#### Step 1:Read-only Onboard
读 SPEC_FROZEN + contracts + DEV_SPEC,写 `verifier_understanding.md`(≥ 100 字)。

#### Step 2:Independent Test

写 `verifier_test.py`:
- ≥ 5 个 positive case(SPEC 验收标准映射)
- ≥ 5 个 negative case(用 `@pytest.mark.xfail` 标记,故意应失败)

**自跑一次**验证 test 自身合理:
```
pytest tasks/track-{X}/verifier_test.py
positive case 全过 ✓
negative case 全 xfail ✓
```

#### Step 3:Run on Dev Impl

```bash
git checkout origin/feat/{track-X} -- packages/X/src/X/{你的层}/
pytest tasks/track-{X}/verifier_test.py --tb=short
pytest -m conformance --tb=short
pytest -m unit packages/X/tests/unit/{你的层}/ --tb=short
```

#### Step 4:Report

`verifier_report.md` 7 段:
1. Onboarding(看了什么)
2. Independent Test(写了什么 test)
3. Run Results(positive/negative pass count)
4. Conformance Results
5. **5 Suspicious Points**(必非空,每个 ≥ 50 字)
6. Verdict(✅ pass / ⚠️ needs_revision / ❌ reject)
7. Tally(机器可读 JSON)

```markdown
<!-- l2-tally: {"verdict": "needs_revision", "blocks": 1, "suggestions": 3, "model": "claude/opus-4.7"} -->
```

---

## 3. auto_approve 7-condition AND-gate

### 7 条件(全部 AND)

```python
# SKILL §10
def auto_approve_check(progress):
    return all([
        progress.l1_ci_passed,                                    # 1. L1 CI ✓
        progress.l4b_tally.block == 0,                            # 2. L4b 0 BLOCK
        progress.l2_tally.verdict == "pass",                      # 3. L2 verdict pass
        progress.l2_tally.blocks == 0,                            # 4. L2 0 blocks
        progress.boundary_check_passed,                           # 5. boundary 干净
        progress.revision_round <= MAX_ROUNDS,                    # 6. revision ≤ 3
        progress.l2_revision_round <= MAX_L2_ROUNDS,              # 7. L2 revision ≤ 3
    ])

if auto_approve_check(progress):
    decision = "AUTO_APPROVE_FIRES"
    gh_pr_merge_squash()
else:
    decision = "GATE_BLOCKED"
    enter_revision_loop()
```

### 7 条件失败的处理

| Fail 项 | 怎么办 |
|---|---|
| L1 CI fail | §6.4 revision round +1 → dev fix → re-push → CI rerun |
| L4b BLOCK | §6.4 revision(L4b feedback 写到 REVISION_FEEDBACK.md round N) |
| L2 needs_revision | §6.5 L2 revision round +1 |
| L2 reject | §6.5 L2 revision round +1(verifier 自动重跑) |
| boundary fail | mention user(G1 越权,SKILL §4.2 4 mention 之一) |
| revision_round > max | mention user(SKILL §4.2 4 mention 之一) |
| l2_revision_round > max | mention user |

### PROGRESS.md auto_approve_gate 字段

```yaml
auto_approve_gate:
  l1_ci_passed: true
  l4b_block_zero: true
  l2_verdict_pass: true
  l2_blocks_zero: true
  boundary_check_passed: true
  revision_round_under_max: true
  l2_revision_round_under_max: true
  decision: AUTO_APPROVE_FIRES   # or GATE_BLOCKED
```

### 实战出处

harness 30+ PR auto_merged,**0 误 merge**。fix-k5 PR #30 round 1 verifier 出 1 BLOCK SP-1(tz-aware @field_validator missing) → 7-gate fail → §6.5 L2 revision round 1 fix(加 2 个 classmethod validator)→ round 2 verdict=pass → 7-gate 全过 → auto_merge。

---

## 4. revision 闭环(§6.4 + §6.5)

### §6.4:L4 BLOCK 闭环(L1 fail + L4a + L4b BLOCK)

```
状态机:

Round 0: dev 提 PR → 等 L1 + L4a + L4b 返回
   ↓
   收集 BLOCK 数:
   - L1 fail 数 (gh pr checks → conclusion=failure)
   - L4a Codex BLOCK (gh pr view comments | grep "🔴 BLOCK")  ← optional 缺席=0
   - L4b Local BLOCK (PROGRESS.md l4b_tally.block)
   ↓
   total_block = L1_fail + L4a_block + L4b_block
   ↓
┌──┴──────────────────────────────────────┐
│  total_block == 0:                       │
│    → 进 §6.5 verify 阶段                  │
│                                          │
│  total_block ≥ 1 AND round < max_rounds: │
│    → 自动 revision:                      │
│       a. aggregate 3 路 feedback          │
│       b. 写到 REVISION_FEEDBACK.md round N│
│       c. 唤醒 dev session                │
│       d. dev 读 feedback → step 3 改 →   │
│          step 4 self-test → step 5 push   │
│          (revision_round: N+1)             │
│       e. push 触发 L1/L4 重跑 + step 5.5  │
│       f. 回到本流程顶部                   │
│                                          │
│  total_block ≥ 1 AND round == max_rounds: │
│    → STOP 自动循环                        │
│    → PROGRESS.md alert_level: needs_human │
│    → mention user                         │
└──────────────────────────────────────────┘
```

### §6.5:L2 Verifier 闭环

```
进入条件:§6.4 total_block == 0
   ↓
spawn verify session(独立 worktree + cascade fallback)
   ↓
verifier_report.md verdict:
   ↓
┌──┴──────────────────────────────────────┐
│  verdict == "pass" AND blocks == 0:      │
│    → §10 auto_approve gate 检查          │
│    → 全过 → §6.3 gh pr merge --squash    │
│                                          │
│  verdict == "needs_revision":            │
│    AND l2_revision_round < max_l2_rounds:│
│    → 写 REVISION_FEEDBACK.md L2 round N  │
│    → 唤醒 dev session                    │
│    → dev fix → push → 重 spawn verify    │
│    (l2_revision_round: N+1)              │
│                                          │
│  verdict == "reject":                    │
│    AND l2_revision_round < max_l2_rounds:│
│    → 同 needs_revision 路径              │
│                                          │
│  l2_revision_round == max:               │
│    → STOP                                │
│    → mention user(SKILL §4.2 mention 3) │
└──────────────────────────────────────────┘
```

### max_rounds 配额(关键!)

**两个配额分开**:
- `max_rounds = 3`(§6.4 L4 BLOCK 闭环)
- `max_l2_rounds = 3`(§6.5 L2 verifier 闭环)

**为什么分开**:防止 reviewer 死循环。L4 是浅层(boundary + 命名),3 轮内必收敛。L2 是深层(算法 + SPEC 符合度),允许 3 轮深思考。两个加起来 6 轮 hard cap。

---

## 实操 Checklist:加质量保证时

- [ ] L1 CI 配 .github/workflows(static-quality.yml + contracts-import.yml)
- [ ] L2 Verifier 用 cascade fallback(codex 优先 → opus)
- [ ] L4b 用 headless claude --print(不要 GitHub workflow)
- [ ] auto_approve 7-condition AND-gate 实施(SKILL §10)
- [ ] §6.4 §6.5 revision 闭环(max 3 轮 each)
- [ ] PROGRESS.md auto_approve_gate 字段(7 项 + decision)

---

## 下一步

- [../examples/pr-30-full-cycle.md](../examples/pr-30-full-cycle.md) — fix-k5 PR #30 完整 round 1 → round 2 闭环实战
- [../04-multi-agent-coordination/README.md](../04-multi-agent-coordination/README.md) — 多 agent 协作
- [../lessons-learned/api-stream-timeout.md](../lessons-learned/api-stream-timeout.md) — API timeout 时怎么 cascade
