# 模块 2:SKILL 编排(让 agent 自跑 0 介入到完成)

## 这个模块解决什么

你 SPEC 写完了,要让 dev agent 自己跑通 5 step + 自审 + verify + auto_merge,**全程 0 user 介入**。

常见痛点:
- ❌ Agent 不读 context 直接 implement → 写歪
- ❌ Agent step 1 死在 stdin 等 user 决策
- ❌ Agent step 5 push 完不自动跑 verify("End of Shift passive")
- ❌ Agent 撞 fail 直接 abort → 不进 revision 闭环
- ❌ Session 中断后无法续跑
- ❌ Agent 自己跑出来 `gh pr merge` 但 7-gate 没通过就 merge 了

本模块给你 **3 个工具**:

1. **5-step 标准工作流** — 强制顺序 + 每步必产产出物
2. **自动闭环铁律** — 4 条禁令防 LLM compliance bug
3. **Checkpoint 恢复机制** — 中断后从 PROGRESS.md 续

---

## 1. 5-step 标准工作流

### 全流程

```
用户(或 main session)spawn dev session
  ↓
[Pre-flight] /harness-dev freeze {track}      # SPEC.md sha256 lock → SPEC_FROZEN.md
  ↓
[Step 1] Onboarding(读 7 共享上下文 + 写 UNDERSTANDING.md)
  ↓
[Step 2] PLAN(写 PLAN.md ≥ 3 设计决策 + ≥ 2 推翻方案)
  ↓
[Step 3] Implement(只动 SPEC §8 钦定文件)
  ↓
[Step 4] Self-test(13 工具全过 + 33 grep 反清单 0-hit)
  ↓
[Step 5] PR(commit + push + gh pr create + PR body 模板)
  ↓
[Step 5.5] L4b Local Claude Review(headless claude --print 自审 + boundary check)
  ↓
[§6.5] Verify spawn(独立 worktree + cascade fallback 模型)
  ↓
[§6.4 §6.5] 自动 revision 闭环(max 3 轮 each)
  ↓
[§10] auto_approve 7-gate
  ↓
[§6.3] gh pr merge --squash + delete branch + archive(memory + commit + push)
  ↓
[Sub-task done,exit]
```

### Step 1:Onboarding

**目的**:让 agent 读完上下文再写代码,不要"上手就 implement"。

**强制读**(7 份):
1. `CLAUDE.md`(项目根,简短入口)
2. `docs/{你的项目}/ONBOARDING.md`(协作规则)
3. `docs/{你的项目}/DEV_SPEC.md`(代码规范 + N 审查)
4. `docs/{你的项目}/CRITIQUE_HISTORY.md` §9(33 条修改约束)
5. `.agent-memory/INDEX.yaml`(项目记忆入口)
6. `tasks/_board.md`(全局状态)
7. `tasks/track-{X}/SPEC_FROZEN.md`(你的具体任务,已 frozen)

**产出**:`tasks/track-{X}/UNDERSTANDING.md`,4 段必有标题:
- ## 我理解的任务(≥ 200 字,引用 SPEC ≥ 3 处)
- ## 关键约束(≥ 5 条)
- ## 我的疑问(如有 SPEC 不清楚处)
- ## 计划方向(高层方法,先想再 PLAN 细化)

**通过 checklist**(自动校验):
- [ ] 文件存在
- [ ] 4 段必有标题
- [ ] "## 我理解的任务" ≥ 200 字
- [ ] "## 关键约束" ≥ 5 条
- [ ] 引用 SPEC §X.Y 至少 3 处

任一 fail → 重写 UNDERSTANDING.md。

### Step 2:PLAN

**目的**:逼 agent 把设计决策写出来,防止"跳过思考直接写代码"。

**产出**:`tasks/track-{X}/PLAN.md`,4 段:
- ## 任务步骤(≥ 3 步,每步 4 段:改什么 / 为什么 / 验收 / 风险)
- ## 关键设计决策(≥ 3 条)
- ## 推翻过的方案(≥ 2 条)
- ## 留给后续 sub-task 的 TODO

**通过 checklist**:
- [ ] ≥ 3 步骤,每步 4 段
- [ ] ≥ 3 设计决策
- [ ] ≥ 2 推翻方案

### Step 3:Implement

**目的**:写代码 + 写 unit test。**只动 SPEC §8 钦定文件**。

**boundary 自检**:
- ✗ 改 contracts/* / .github/* / pyproject.toml ruff/mypy 段 → STOP
- ✗ 改其他 sub-task 实施 → STOP
- ✗ 33 约束(datetime.utcnow / print / except Exception / ...)→ STOP

**实时记录**:每个文件写完更新 `PROGRESS.md` `current_files: [...]`

### Step 4:Self-test

**目的**:13 工具全过 + 33 grep 反清单 0-hit。

**13 工具**(任一非 0 退出 = fail):
```bash
ruff check .                                     # 1
ruff format --check .                            # 2
mypy --strict src/{你的层}                       # 3
interrogate --fail-under 100 src/{你的层}        # 4
bandit -r src/{你的层}                           # 5
pip-audit                                        # 6
pytest -m unit tests/unit/{你的层}/              # 7
pytest -m unit --cov-fail-under=80               # 8
pytest -m contract tests/contract/test_X.py      # 9
pytest -m regression tests/regression/           # 10(如有)
pytest -m conformance                            # 11
! grep -rn "datetime.utcnow" src/{你的层}/        # 12(0 hit)
! grep -rn "print(" src/{你的层}/                # 13(0 hit,排除 docstring)
```

**fail 处理**:
- 输出 fail 详情
- PROGRESS.md `status: step_3_redo, fail_count: N`
- 回 Step 3 改
- fail_count ≥ 3 → 标 `needs_human` + mention user

### Step 5:PR

**目的**:commit + push + gh pr create。

**自动操作**:
```bash
git add {SPEC §8 钦定文件}
git commit -m "{track-X}: {一句话}

Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin feat/{track-X}
gh pr create --title "{track-X}: {layer}" --body "$(cat templates/PR_BODY.md.rendered)"
```

**约束自检**:
- [ ] commit message 含 sub-task ID
- [ ] 没改 .github/workflows/* / contracts/* / pyproject.toml ruff 段
- [ ] 没改其他 sub-task 代码

### Step 5.5:L4b Local Claude Review

**目的**:headless `claude --print` 跑独立审查,**走 user Max 订阅 0 额外费用**。替代 GitHub workflow 方案。

**自动跑**:
```bash
PR_N=$(awk -F': ' '/^pr_number/ {print $2}' PROGRESS.md)
claude --print "你是 PR #$PR_N 的独立 reviewer。

第一步:跑 \`gh pr diff $PR_N\` 拿 diff
第二步:读 docs/DEV_SPEC.md / CRITIQUE_HISTORY.md §9 / ARCHITECTURE.md §1.1

**第三步(BOUNDARY CHECK — 优先于 4 维度审,任一命中直接 🔴 BLOCK)**:
跑 \`gh pr diff $PR_N --name-only\`,如出现以下任一直接 BLOCK:
- 根 pyproject.toml(workspace root)
- packages/X/pyproject.toml 的 [tool.mypy*] / [tool.ruff*] 段
- .github/workflows/*
- contracts/*.py(architect 领地)

**特别警惕** [[tool.mypy.overrides]] module=\"contracts.*\" ignore_errors = true 这类绕过反清单行为。

重点审 4 维度,引用具体 file:line:
1. 设计 — 架构 / 跨层耦合 / 单一职责 / 33 约束
2. 可维护性 — 6 个月后能看懂 / 命名 / docstring
3. 一致性 — 错误处理 / 日志
4. 文档 — README / HANDOFF / CHANGELOG

输出 Markdown:
- 🔴 BLOCK / 🟡 SUGGEST / 🟢 NIT / ✅ APPROVE if 全 NIT

最后一行机器可读 tally:
\`<!-- l4b-tally: {\"block\": N, \"suggest\": N, \"nit\": N, \"approve\": bool} -->\`
" > local_l4b_review.md

# post 成 PR 评论
gh pr comment $PR_N --body "$(printf '🤖 **L4b Local Claude Review**\n\n%s' "$(cat local_l4b_review.md)")"
```

**约束**:
- 头一行**不能**有 `@claude` mention(避免触发其他 GitHub App webhook)
- 最大允许 8000 token output;超了截断
- claude headless 进程超时 5 min → 杀掉 + 标 `l4b: timeout`(不阻塞)

**更新 PROGRESS.md**:`l4b: done|failed|truncated|timeout, l4b_tally: {...}`

### §6.5 Verify Spawn(详见模块 3)

dev session **自调** spawn verify session(独立 worktree + cascade fallback 模型)。

### §10 auto_approve 7-gate(详见模块 3)

dev session 跑 7-gate 检查,全过 → `gh pr merge --squash` + archive。

---

## 2. 自动闭环铁律(SKILL §4.2)

### 4 条禁令

写在 SKILL prompt 里,强制 dev agent 遵守:

```
🔒 自动闭环铁律(禁止问 user 中间决策)

SKILL §6.4 / §6.5 / §10 设计为全自动闭环。
你必须严格按 SKILL 跑,不要停下来等 user 答:

✅ 正例:
- L4 total_block=0 → 直接进 §6.5 verify(不问"要不要先看 dashboard")
- L4 有 BLOCK → 直接 §6.4 revision max 3 轮(不问"approve / revision / reject 哪个")
- L2 verdict=pass + 0 blocks + boundary clean → 写 PROGRESS auto_approved + 自动 merge(不问 user)
- L2 needs_revision / reject → 直接 §6.5 L2 revision max 3 轮(不问 user)

❌ 反例(违反铁律):
- "4 选项 A/A+/B/C 选哪个" / "选 codex 还是 opus" / "ACK 重测" — 改回自动选最 sane default

⚠️ 关键 — 不要 "End of Shift passive"(实测教训):

step 5 + 5.5 跑完后,你必须立刻继续:
1. 自己检查 PROGRESS.md l4b_tally.block,不等任何人触发
2. 如果 total_block (L1 fail + L4a + L4b) == 0 → 立刻在同一 session 内调 /harness-dev verify {track} 开 §6.5 verify
3. verify 完读 verdict,继续 §6.5 闭环(needs_revision → 改 → push;pass → §6.3 archive + auto_approve gh pr merge)
4. 每次 push round-N commit 后(包括 amend/force-push)→ 立刻同 session 内重跑 step 5.5 L4b + 自己 check 是否进 §6.5

反例(实测犯的错):
- step 5 push 完报告 "End of Shift passive,等待 verify trigger" → 等了 1 小时没人触发
- main session 不得不手工 spawn verify

正例(做对的):
- step 5 push → 同 session 自跑 step 5.5 → 自跑 §6.5 verify → 看 verdict 自跑 round 1 fix → ...直到 pass + auto_merge
- 全程 0 user input,SKILL 自闭合

只有 4 种情况可以 mention user(写 PROGRESS.md alert_level: needs_human + 通知):

1. 越权违规检测(L4b §5.5 boundary check 抓到 G1 类反清单行为)
2. §6.4 max_rounds: 3 用尽,L4 闭环没收敛
3. §6.5 max_l2_rounds: 3 用尽,L2 仍 reject
4. system error(API 502 retry exhausted / SQLite lock / cascade 全 fail / 上游 contracts bug 阻塞 step 4 等)

其余 100% 自动:dev 5 step / step 5.5 L4b / §6.4 auto-revision / §6.5 auto-verify / auto_approve / §6.3 archive + commit + push。

user-on-the-loop 不是 user-in-the-loop:user 启动 dev session 后 walk away,只在 dashboard 红/黄闪烁时介入。
```

---

## 3. Checkpoint 恢复机制

### SPEC_FROZEN.md sha256 lock

**目的**:防 SPEC drift(architect 改了 SPEC,dev 还按老 SPEC 实施)。

**实施**:
```yaml
# SPEC_FROZEN.md 头
---
spec_sha256: 6226d371b055307c142f048ac98fa26098ae6846d9846a7fe368e0da2366b743
frozen_at: 2026-05-03T00:00:00Z
track: track-fix-phase1-007-r3
source: SPEC.md
freeze_method: harness-dev §7.1
---
```

dev / verifier 跑命令时 verify sha256 跟 SPEC.md 一致。不一致 → abort + 提示"SPEC drift,re-freeze"。

### PROGRESS.md status 状态机

**目的**:中断恢复(session 死了 / user kill / 电脑重启后续跑)。

**status 字段流**:
```
unstarted → step_1_in_progress → step_1_done
         → step_2_in_progress → step_2_done
         → step_3_in_progress → step_3_done
         → step_4_in_progress → step_4_done
         → step_5_in_progress → pr_submitted
         → pr_submitted_l4b_done
         → verify_round_N_in_progress → verify_round_N_done
         → l2_revision_round_N_pushed
         → auto_approving → auto_approved → archive_committed → done
```

**SKILL §4.1 启动检查**:
```python
PROGRESS = read_yaml("tasks/track-{X}/PROGRESS.md")

if not PROGRESS.exists:
    全新跑 5 step
elif PROGRESS.status.startswith("step_") and PROGRESS.status.endswith("_done"):
    从 step (N+1) 续
elif PROGRESS.status == "paused":
    续命模式(注入 resume prompt)
elif PROGRESS.alert_level == "needs_human":
    abort + 提示 user 介入(避免 LLM 又跑乱)
```

### 完整 PROGRESS.md 模板

见 [../templates/PROGRESS.template.md](../templates/PROGRESS.template.md)

---

## 实操 Checklist:写 SKILL 时

- [ ] 5-step 顺序固定,每步必产 .md 产出物
- [ ] 每步通过 checklist 自动校验(任一 fail 重做)
- [ ] step 5.5 L4b 用 headless `claude --print`(不要 GitHub Actions workflow)
- [ ] 自动闭环铁律 4 条禁令写进 prompt
- [ ] PROGRESS.md status 字段定义清晰
- [ ] checkpoint 恢复逻辑(SKILL §4.1 启动检查)
- [ ] 4 mention user 情况明文列

---

## 下一步

- [../templates/SKILL.template.md](../templates/SKILL.template.md) — SKILL.md 完整抽象模板
- [../templates/PROGRESS.template.md](../templates/PROGRESS.template.md) — PROGRESS.md 模板
- [../03-quality-gates/README.md](../03-quality-gates/README.md) — verify + auto_approve 7-gate 细节
- [../lessons-learned/llm-compliance-bugs.md](../lessons-learned/llm-compliance-bugs.md) — 4 种 dev 不听话 form 实战案例
