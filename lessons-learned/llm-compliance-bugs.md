# LLM Compliance Bugs(4 种 form 实战案例)

LLM 不 100% 听 SKILL prompt 是事实(实战 30% 概率)。本文档列 harness v3 ~100h 实战遇到的 **4 种 LLM compliance bug form** + 兜底策略。

## 核心结论

> **不要寄望 prompt 加严格能根治** → 加 **dispatcher daemon 30s polling 兜底** + **main session /loop 监控** 双保险。

---

## Form (a):passive 等 trigger

### 症状

Dev session step 5 push 完 PR OPEN,L4b 跑完 0 BLOCK,**但 dev session 没自调 §6.5 verify**,session active 但什么都不做(等 trigger)。

### 实战出处

harness console-backend / fix-k1 / fix-k3-k4 多次实战:dev session step 5.5 完成后写"End of Shift passive,等待 verify trigger" → 等了 1 小时没人触发。

### 兜底

1. **Dispatcher Path 2**:30s polling status 含 `pr_submitted` 等且 `last_update` 30+ min 没变 → 自动 spawn `claude --print "/{project}-dev verify {track}"`
2. **Main session /loop 监控**:周期性扫 PROGRESS.md,撞这个 pattern 代办 spawn

### 防御 prompt(写进 SKILL §4.2)

```
⚠️ 关键 — 不要 "End of Shift passive"(2026-04-30 ledger 实测教训):

step 5 + 5.5 跑完后,你必须立刻继续:
1. 自己检查 PROGRESS.md l4b_tally.block(L4b 已写),不等任何人触发
2. 如果 total_block (L1 + L4a + L4b) == 0 → 立刻在同一 session 内调用 /{project}-dev verify {track} 开 §6.5 verify
3. verify 完读 verdict,继续 §6.5 闭环
4. 每次 push round-N commit 后(包括 amend/force-push)→ 立刻同 session 内重跑 step 5.5 L4b + 自查是否进 §6.5

反例(实测犯的错):
- step 5 push 完报告 "End of Shift passive,等待 verify trigger" → 等了 1 小时没人触发
- main session 不得不手工 spawn verify

正例:
- step 5 push → 同 session 自跑 step 5.5 → 自跑 §6.5 verify → 看 verdict 自跑 round 1 fix → ...直到 pass + auto_merge
- 全程 0 user input
```

---

## Form (b):问 user 中间决策

### 症状

Dev session step 1 onboarding 写完 SPEC ack 5 选项 → **死等 stdin**。但 hidden cmd.exe spawn 的 dev session **永远接不到 stdin**(没 stdin 通道)。

### 实战出处

harness console-frontend / fix-k5:dev session step 1 写"我建议方向 A,user ack 一下" → hidden 跑的 session 死等。

### 兜底

1. **唯一办法**:user 自己开**新 visible Claude Code session** 在 worktree 内输 `go`(实战 console-frontend 这样解决)
2. **预防 prompt 加"禁止问 user 中间决策"铁律**(详见 SKILL §4.2)

### 防御 prompt(写进 spawn dev session 的 prompt)

```
🔒 自动闭环铁律(禁止问 user 中间决策)

✅ 正例:
- L4 total_block=0 → 直接进 §6.5 verify(不问"要不要先看 dashboard")
- L4 有 BLOCK → 直接 §6.4 revision max 3 轮(不问"approve / revision / reject 哪个")
- L2 verdict=pass + 0 blocks + boundary clean → 自动 §6.3 merge(不问 user)

❌ 反例(违反铁律):
- "4 选项 A/A+/B/C 选哪个" / "选 codex 还是 opus" / "ACK 重测" — 改回自动选最 sane default
```

---

## Form (c):PROGRESS.md 写非标值

### 症状

Dev session 把 status 写成非标值(比如 `pr_submitted_l4b_done` 而不是 `pr_submitted` 或 `verify_in_progress`),**dispatcher regex 不识别变体卡死**。

### 实战出处

harness console-backend status `pr_submitted_l4b_done` / fix-k3-k4 last_update 写未来 UTC → dispatcher v4 regex `^pr_submitted$` exact match 不识别 → Path 2 stuck detection 失效。

### 兜底

1. **dispatcher regex 用前缀 match**(不要 exact)— `^pr_submitted` 而不是 `^pr_submitted$`
2. **PROGRESS.md status 字段 enum 严格定义**(详见 templates/PROGRESS.template.md)
3. **L4b 自审 prompt 加 PROGRESS schema check**(boundary check 时验 status 字段值)

### dispatcher v5 修复(harness 实战)

```powershell
# v4(exact match,卡死 30%):
if ($progress -match "status:\s*pr_submitted$") { ... }

# v5(prefix match,catch 100%):
if ($progress -match "status:\s*(pr_submitted|step_5_done|verify_done)") { ... }
```

---

## Form (d):verify session 卡 cascade fallback 决策

### 症状

verify session 撞 codex 401 → 应该 cascade fallback opus,但 verify session **给 user 5 选项让她拍板用 Opus**(违反铁律 form (b)),verifier_report 没真生成。

### 实战出处

harness frontend retry2:codex 401 → verify session 给 user 5 选项让她选用 Opus / 重试 codex / halt → user 没在线 → 卡死。

### 兜底

1. **cascade fallback 写硬规则**(不要给 LLM 选项):
   ```bash
   if codex login status 2>&1 | grep -q "Logged in"; then
       spawn="codex exec"
   else
       spawn="claude --print --model opus"  # 自动 fallback,不问
   fi
   ```
2. **如果 verify session 真卡了**:main session 检测到 verifier_report.md 没出 + verify session active 30+ min → 兜底 kill + spawn 新 verify session 强制 opus

---

## 4 种 form 速查卡

| Form | 症状 | 实战频率 | 兜底 |
|---|---|---|---|
| (a) passive 等 trigger | step 5 push 完不自调 verify | ~30% | dispatcher Path 2 + /loop 监控 |
| (b) 问 user 中间决策 | dev session 死等 stdin | ~10% | 必 visible session 介入 + SKILL §4.2 prompt |
| (c) PROGRESS.md 非标值 | dispatcher regex 不识别 | ~20% | regex 前缀 match + status enum 严格 |
| (d) cascade 卡决策 | verify 给 user 5 选项 | ~5% | cascade 硬编码 + main 兜底 kill |

---

## 综合策略(harness 实战通过)

```
Layer 1: SKILL prompt 写 "自动闭环铁律" + "禁问 user 中间决策" + "禁 End of Shift passive"
                ↓ (80% 听话)
Layer 2: dispatcher daemon 30s polling 3 path 兜底
                ↓ (catch 大部分 form (a) (c))
Layer 3: /loop dynamic mode 主 session 监控
                ↓ (catch 行为级异常)
Layer 4: User 偶尔 mention(撞 4 mention 情况才打扰)
```

实战:Phase 1.5 14 sub-task,**100% 跑通**,user 实际介入 ~10h。

---

## 不要做的事

❌ "再加更严格的 prompt 就能 100% 听话" — 错。LLM 不是确定性的,30% 概率不听。

❌ "每次撞 bug 就让 user 介入" — 错。Long-running 项目必崩。

✅ 接受 LLM 30% 不听话是事实 + 多层防御 + dispatcher 兜底 + main session 监控。
