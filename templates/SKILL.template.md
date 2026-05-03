# SKILL.md — {Project} 开发流程编排器

> 这是 SKILL 抽象模板。改 {Project} / {layer-name} 等占位符成你的项目名词。
> 完整可参考 harness-dev SKILL(harness 项目实战版,~1300 行)。

---

## §0 你是谁

你是 {project}-dev SKILL 的执行器。用户在 Claude Code 输入 `/{project}-dev <mode> <args>`,
你按本文档协议执行。**严格按步骤,不要跳步,不要省略**。

不在 {project} 工作目录? → 报错 + 提示 user cd 到对的目录。

---

## §1 命令路由表

```
/{project}-dev <command> [args]

主流程命令:
  develop {track}       开发 Agent 5-step
  verify  {track}       Verifier Agent 4-step (强制非 Dev 模型)
  review  {pr}          用户看 5 路报告决策

辅助命令:
  freeze  {track}       冻结 SPEC.md → SPEC_FROZEN.md
  status                查全局状态
  pause   [{track}]     暂停
  resume  [{track}]     续命
  cancel  {track}       取消
  inject  {track} {text}   注入提示(软中断)
```

未识别命令 → 输出本路由表 + 让 user 选。

---

## §2 启动前置检查(任何命令前先做)

按顺序检查,任一失败立即报错并停止:

```
1. 当前 cwd 在 {project} monorepo?
   - 检查存在:tasks/_contracts/ + {project}/ARCHITECTURE.md
   - 不在 → 报错"not in {project} monorepo, cd 到根目录"

2. 当前命令需要什么前置?
   develop/verify/review/cancel/inject → 必须有 track 参数
   freeze → 必须 SPEC.md 存在

3. 识别当前 worktree
   - cwd 在 ../{project}-track-X/ → 当前 track = X
   - cwd 在主仓库 → 多 track 操作
```

---

## §3 共享上下文加载(每次 mode 命令必读 7 份)

```
1. CLAUDE.md(项目根,如存在)
2. {project}/ONBOARDING.md(协作规则)
3. {project}/DEV_SPEC.md(代码规范 + N 审查)
4. {project}/CRITIQUE_HISTORY.md §9(33 条修改约束)
5. .agent-memory/INDEX.yaml(项目记忆入口)
6. tasks/_board.md(全局状态)
7. tasks/track-{X}/SPEC_FROZEN.md(你的具体任务,已 frozen)
```

**verify 模式额外限制**:
- 禁止读 packages/X/src/(开发 agent 的实现)
- 禁止读 tasks/track-{X}/UNDERSTANDING.md / PLAN.md
- 禁止读 packages/X/tests/unit/(Dev 自测)

---

## §4 mode: develop {track}

### §4.1 启动检查 + 断点检测

```
1. tasks/track-{X}/SPEC_FROZEN.md 存在? → 否则 abort:"先 /{project}-dev freeze {track}"
2. 当前 worktree 是否对应 track? → 否则 abort:"cd ../{project}-track-{X} 再来"
3. 检测断点:tasks/track-{X}/PROGRESS.md 是否存在?
   - 不存在 → 全新跑 5 step
   - 存在 → 读 status:
     - "step_N_done" → 从 step N+1 续
     - "paused" → 续命模式(注入 resume prompt)
     - alert_level=needs_human → abort,提示 user 介入(避免 LLM 又跑乱)
```

### §4.2 自动闭环铁律(关键!)

向自己注入这段 system prompt:

```
🔒 自动闭环铁律(禁止问 user 中间决策)

SKILL §6.4 / §6.5 / §10 设计为全自动闭环。
你必须严格按 SKILL 跑,不要给 user 4 选项 / 5 选项 / "ACK 一下" 停下来等回答。

✅ 正例:
- L4 total_block=0 → 直接进 §6.5 verify
- L4 有 BLOCK → 直接 §6.4 revision max 3 轮
- L2 verdict=pass + 0 blocks + boundary clean → §6.3 auto_merge
- L2 needs_revision / reject → 直接 §6.5 L2 revision max 3 轮

❌ 反例(违反铁律):
- "4 选项 A/A+/B/C 选哪个" — 改回自动选最 sane default

⚠️ 关键 — 不要 "End of Shift passive"(实测教训):

step 5 + 5.5 跑完后,你必须立刻继续:
1. 自己检查 PROGRESS.md l4b_tally.block
2. 如果 total_block (L1 + L4a + L4b) == 0 → 立刻同 session 内调 /{project}-dev verify {track}
3. verify 完读 verdict,继续 §6.5 闭环
4. 每次 push round-N commit 后 → 立刻同 session 内重跑 step 5.5 L4b + 自查是否进 §6.5

只有 4 种情况可以 mention user:
1. L4b boundary check 抓到 G1 类越权
2. §6.4 max_rounds: 3 用尽
3. §6.5 max_l2_rounds: 3 用尽
4. system error(API 502 retry exhausted / 上游 contracts bug 阻塞 step 4 等)

其余 100% 自动。

user-on-the-loop 不是 user-in-the-loop:
user 启动 dev session 后 walk away,只在 dashboard 红/黄闪烁时介入。
```

### §4.3 5-step 流程(详见 [02-skill-orchestration/README.md](../02-skill-orchestration/README.md))

#### Step 1:Onboarding → UNDERSTANDING.md
#### Step 2:PLAN → PLAN.md(≥3 决策 + ≥2 推翻)
#### Step 3:Implement → 只动 SPEC §8 钦定文件
#### Step 4:Self-test → 13 工具全过 + 33 grep 0-hit
#### Step 5:PR → commit + push + gh pr create
#### Step 5.5:L4b headless claude --print 自审

---

## §5 mode: verify {track}

### §5.1 启动检查(强制约束 + 模型级联)

```
1. PR 已提交? (PROGRESS.status == pr_submitted)
2. worktree 隔离(独立 ../workbench-verifier-{X}/ + 物理删除 dev impl/test/思考过程)
3. 模型级联:
   - try 1: codex CLI(优先)
   - fallback: claude --print --model opus
   - both fail: abort + 提示 install
```

### §5.2 4-step 流程(详见 [03-quality-gates/README.md](../03-quality-gates/README.md))

#### Step 1:Read-only Onboard → verifier_understanding.md
#### Step 2:Independent Test → verifier_test.py(≥5 positive + ≥5 xfail)
#### Step 3:Run on Dev Impl
#### Step 4:Report → verifier_report.md(7 段 + 5+ 可疑点 + tally)

---

## §6 §6.4 §6.5 §6.6 §6.7 闭环

### §6.4 L4 BLOCK 自动闭环(max_rounds=3)
### §6.5 L2 Verifier 自动闭环(max_l2_rounds=3)
### §6.6 phase 收敛(0 blocker + 0 serious 才 pass)
### §6.7 regression test 永久 lock

详见 [03-quality-gates/README.md](../03-quality-gates/README.md)

---

## §7 SPEC freeze 机制

### §7.1 freeze method

```bash
# /{project}-dev freeze {track}
SPEC_PATH="tasks/track-{X}/SPEC.md"
SHA256=$(sha256sum $SPEC_PATH | awk '{print $1}')

cat > tasks/track-{X}/SPEC_FROZEN.md <<EOF
---
spec_sha256: $SHA256
frozen_at: $(date -u +%FT%TZ)
track: track-{X}
source: SPEC.md
freeze_method: {project}-dev §7.1
---

# SPEC_FROZEN — 见 SPEC.md(此文件锁内容,改 SPEC 须 re-freeze)

冻结后任何 SPEC.md 修改都使本文件 sha256 失效;Dev / Verifier 必须 re-freeze 才能继续。

实际任务正文请直接读 \`SPEC.md\`(同目录)。
EOF
```

### §7.2 sha256 mismatch 处理

dev / verifier 跑命令时校验:
```bash
ACTUAL=$(sha256sum tasks/track-{X}/SPEC.md | awk '{print $1}')
EXPECTED=$(grep "spec_sha256" tasks/track-{X}/SPEC_FROZEN.md | awk '{print $2}')
if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "SPEC drift detected. Re-freeze required."
    exit 1
fi
```

---

## §10 auto_approve 7-condition gate

详见 [03-quality-gates/README.md](../03-quality-gates/README.md) auto_approve 章节。

```python
def auto_approve_check(progress):
    return all([
        progress.l1_ci_passed,
        progress.l4b_tally.block == 0,
        progress.l2_tally.verdict == "pass",
        progress.l2_tally.blocks == 0,
        progress.boundary_check_passed,
        progress.revision_round <= MAX_ROUNDS,        # 3
        progress.l2_revision_round <= MAX_L2_ROUNDS,  # 3
    ])
```

全过 → §6.3 auto_merge + archive。
任一 fail → 进 §6.4 / §6.5 revision 闭环 / mention user。

---

## §11 cascade fallback(关键弹性)

```bash
# 任何调用 codex 的地方,都要套 cascade fallback
if codex login status 2>&1 | grep -q "Logged in" \
   && codex_model_response=$(codex exec "$prompt" 2>&1); then
    model_used="codex/gpt-5.5"
    # success path
else
    # codex fail (401 / quota / refresh_token_reused)
    model_used="claude/opus-4.7"  # cascade fallback
    claude --print --model opus "$prompt" > $output_file
fi
```

写进 PROGRESS.md `verifier_model_used` 字段(审计 + 后期统计)。

---

## §12 实战教训(SKILL 设计的反思)

详见 [../lessons-learned/](../lessons-learned/):

- LLM compliance bugs 4 种 form
- API stream timeout(ping pong + canary retry)
- force push 安全(--force-with-lease)
- self-criticism 入 PLAN §X 防重蹈

---

## 本 SKILL 的总长度参考

harness-dev SKILL(实战完整版):**~1300 行**
- §0-§3 元数据 + 路由 + 共享上下文加载:~150 行
- §4 develop mode:~400 行(含 5-step + 闭环铁律)
- §5 verify mode:~200 行
- §6.4 §6.5 §6.6 §6.7 闭环:~300 行
- §10 auto_approve:~80 行
- §11 cascade fallback:~50 行
- 实战教训 + appendix:~120 行

如果你的项目较简单,可以从 ~500 行的 minimal SKILL 开始,撞到问题再加。
