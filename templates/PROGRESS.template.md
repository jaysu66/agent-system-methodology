---
# PROGRESS.md - Sub-task 状态机 + checkpoint
#
# 所有人都读这个文件:dev session / verify session / dispatcher daemon / main session / user
# 字段必须严格按定义,不要写非标值(daemon regex 兜底依赖)

# 必填:track 标识
track: track-{X}-{layer-name}

# 必填:状态机字段(SKILL §4.1 启动检查依赖)
# 取值:
#   unstarted | step_1_in_progress | step_1_done | step_2_in_progress | step_2_done |
#   step_3_in_progress | step_3_done | step_4_in_progress | step_4_done |
#   step_5_in_progress | pr_submitted | pr_submitted_l4b_done |
#   verify_round_N_in_progress | verify_round_N_done |
#   l2_revision_round_N_pushed | auto_approving | auto_approved |
#   archive_committed | done |
#   step_N_blocked | paused
status: unstarted

# 必填:alert 级别(决定 user 是否被 mention)
# 取值:
#   ok | needs_human | needs_human_batch_review | needs_human_design_review |
#   auto_approved | error
alert_level: ok

# 时间戳 ISO 8601 UTC
last_update: 2026-05-03T00:00:00Z

# revision round 计数(§6.4 L4 BLOCK 闭环)
# max_rounds = 3
revision_round: 0

# L2 verifier round 计数(§6.5 L2 verifier 闭环)
# max_l2_rounds = 3
l2_revision_round: 0

# L4b 状态(SKILL Step 5.5 自审)
# 取值:not_yet | done | failed | truncated | timeout
l4b: not_yet
l4b_tally:
  block: 0
  suggest: 0
  nit: 0
  approve: false  # true if 全 NIT (0 BLOCK 0 SUGGEST)

# L2 状态
l2_tally:
  verdict: pending  # pending | pass | needs_revision | reject
  blocks: 0
  suggestions: 0
  model: null  # codex/gpt-5.5 | claude/opus-4.7

# 当前 step
current_step: 1

# 当前 in-flight 文件(dev step 3 实时记)
current_files: []

# PR 信息(step 5 后)
pr_number: null
pr_url: null

# user 决策注入(从 main session proxy)
last_user_inject: null
# last_user_inject 例:
# last_user_inject:
#   ts: 2026-05-03T01:35:00Z
#   source: main_session_proxy
#   decisions:
#     Q1_xxx: D
#     Q2_xxx: A

# auto_approve 7-condition gate(SKILL §10)
auto_approve_gate:
  l1_ci_passed: false
  l4b_block_zero: false
  l2_verdict_pass: false
  l2_blocks_zero: false
  boundary_check_passed: false
  revision_round_under_max: true   # initial true (revision_round=0 < max=3)
  l2_revision_round_under_max: true
  decision: PENDING  # PENDING | AUTO_APPROVE_FIRES | GATE_BLOCKED

# Self-test results(step 4)
self_test_results:
  ruff_check: pending
  ruff_format: pending
  mypy_strict: pending
  interrogate: pending
  bandit: pending
  pip_audit: pending
  unit: pending
  coverage: pending
  contract: pending
  conformance: pending
  grep_constraints: pending  # 33 约束 grep 0-hit

# Verifier model 实际用的(cascade fallback 后)
verifier_model_used: null

# SPEC sha256 lock(SKILL §7.1 freeze method)
spec_sha256: null

# alert message(给 user 看的)
alert_message: null
---

# Track {X} Progress

## Step Ledger

(每 step 完成后追加一行,带时间戳)

### Step 1: Onboarding

- [ ] 加载 7 共享上下文
- [ ] 写 UNDERSTANDING.md
- [ ] 通过 checklist(4 段 + ≥200 字 + ≥5 约束 + ≥3 SPEC 引用)

### Step 2: PLAN

- [ ] 写 PLAN.md
- [ ] ≥3 设计决策
- [ ] ≥2 推翻方案

### Step 3: Implement

- [ ] 写代码 + unit test
- [ ] 只动 SPEC §8 钦定文件
- [ ] 实时更新 current_files

### Step 4: Self-test

- [ ] ruff check ✓
- [ ] ruff format --check ✓
- [ ] mypy --strict ✓
- [ ] interrogate ✓
- [ ] bandit ✓
- [ ] pip-audit ✓
- [ ] pytest unit + coverage ≥80% ✓
- [ ] pytest contract ✓
- [ ] pytest conformance ✓
- [ ] grep 33 约束 0-hit ✓

### Step 5: PR

- [ ] git commit + push
- [ ] gh pr create + body

### Step 5.5: L4b Local Claude Review

- [ ] headless claude --print 跑完
- [ ] post PR comment
- [ ] tally:{block: N, suggest: N, nit: N, approve: bool}

### §6.5 Verify Round 1

- [ ] spawn verify session(独立 worktree + cascade fallback)
- [ ] verifier_test.py 写 + 自跑通
- [ ] verifier_report.md 写 + 7 段 + 5+ 可疑点
- [ ] verdict: ?

### §6.5 L2 Revision Round N(如需)

- [ ] 读 REVISION_FEEDBACK.md L2 round N
- [ ] dev session fix
- [ ] commit + force push
- [ ] CI / L4b rerun
- [ ] verify round N+1

### §6.3 Auto-merge + Archive

- [ ] auto_approve 7-gate AUTO_APPROVE_FIRES
- [ ] gh pr merge --squash
- [ ] delete branch
- [ ] HANDOFF.md 写
- [ ] .agent-memory/SESSIONS/{date}-track-{X}.md 写
- [ ] _board.md / INDEX.yaml / CONTEXT.md update
- [ ] commit + push archive
