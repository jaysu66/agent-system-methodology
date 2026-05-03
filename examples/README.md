# Examples

实战示例从 harness v3 项目提取(脱敏简化版),对应方法论的核心 pattern。

---

## 例 1:完整 Sub-task 闭环(fix-k5 PR #30)

**说明** harness fix-k5-observer PR #30 完整周期,展示 SKILL §4 5-step + L4b + §6.5 verify + §6.4 §6.5 revision + §6.3 auto_merge + archive 全流程。

**关键时间线**:
```
03:00Z  user 给 4 决策 ack(Q1=D, Q2=A, Q4=ACK)
03:01Z  main session 代办 inject + spawn dev session
03:30Z  dev step 1 onboarding 完(读 7 共享上下文 + UNDERSTANDING.md)
04:10Z  dev step 2 PLAN 完(22.7KB,6 步设计 + 3 关键决策 + 2 推翻)
04:40Z  dev step 3 implement 完(改 sandbox.py + hitl_local.py + governance/__init__ + pyproject psutil 依赖 + 5 个 test 文件)
04:50Z  dev step 4 self-test 13 工具全过
04:55Z  dev step 5 PR #30 提交 @ commit 8ee3587
05:00Z  dev step 5.5 L4b headless claude 自审(0 BLOCK / 2 SUGGEST / 3 NIT, approve=true)
05:05Z  dev §6.5 spawn verify session(codex 401 → cascade opus)
05:25Z  verify round 1 verdict: needs_revision(1 BLOCK SP-1: tz-aware @field_validator missing)
05:30Z  dev §6.5 round 1 fix(加 2 个 classmethod validator)+ push round 1 commit
05:35Z  CI/L4b round 1 重跑 → 全过
05:40Z  dev re-spawn verify round 2(opus)
06:00Z  verify round 2 verdict: pass
06:01Z  dev §10 auto_approve 7-gate AUTO_APPROVE_FIRES
06:02Z  gh pr merge --squash → main 6cf160e
06:05Z  dev §6.3 archive(写 HANDOFF + .agent-memory/SESSIONS/)
06:10Z  archive commit + push → main 46a7c71
06:11Z  dispatcher v5 path 3 检测到 fix-k5 done → 但 fix-k5 是末端无下游,不 spawn
06:12Z  dev session exit
```

**user 介入次数**:1 次(决策 4 个 SPEC 疑问)
**总时长**:~3 小时
**round 数**:1 round revision

详见 [pr-30-full-cycle.md](pr-30-full-cycle.md)(完整 PR body + verifier_report + L4b review)。

---

## 例 2:fail-greedy + fix-batch 模式(phase-1 → fix-batch-2 → R2 → R3 → 收敛)

**说明** harness phase-1-bootstrap 撞 6 finding → 4 轮 fix-batch 收敛 → phase-1 0 finding → phase-2 spawn 完整周期。

**关键时间线**:
```
T+0     phase-1 dev session spawn(架构验证 fail-greedy)
T+30m   phase-1 跑 18 tests:12 pass + 6 xfail(record_and_continue 记 6 finding)
T+35m   alert_level: needs_human_batch_review → mention user
T+45m   user 看 brief → ping architect "起 fix-batch-2 SPEC, closes 001/003/005/007;013/019 关闭"
T+1h    architect SPEC PR #32 出来(6 文件 +1409 -2,4 fix SPEC)
T+1h05  user ack → main session merge PR #32 + 4 worktree + spawn 4 dev session
T+1h35  4 PR (#33/#34/#35/#36) 全 OPEN
T+2h    fix-batch-2 R1 4 PR 全 merged(1 路 hang 在 gh merge 我代办)
T+2h30  phase-1 rebase + 重跑 → 14 pass + 4 xfail(K2/K0 解,K1/K3 仍 xfail)
T+2h35  我诊断:fix-batch-2 R1 SPEC 把"caller 必须传"当 backward-compat,phase-1 没改调用
T+2h45  user 选 B → ping architect "起 fix-batch-3 R2 SPEC"
T+3h    architect SPEC PR #38 出来(3 R2 fix SPEC,改 default-on)
T+3h05  user ack → 我代办 merge + spawn 3 R2 dev session
T+4h    3 R2 PR (#39/#40/#41) 全 merged(0 revision 一次过)
T+4h30  phase-1 rebase + 重跑 → 16 pass + 2 xfail(K3 仍 xfail,新错:SQLite locked)
T+4h35  我诊断:R2 改 sync await ledger.append → SQLite race lock
T+4h45  user ack 起 fix-batch-4 R3
T+5h    architect SPEC PR #42 出来(SQLite single-conn cache + asyncio.Lock)
T+5h05  user ack → 我代办 merge + spawn R3 dev session
T+5h35  R3 PR #43 merged(round 0 一次过)
T+5h45  phase-1 rebase + 重跑 → 16 pass + 2 xfail(K3 还在!发现 test 没传 trace_id)
T+5h50  我代办 1 行 K3 fix(test 加 trace_id=)
T+5h55  phase-1 17 pass + 1 deferred xfail(K6 SPEC 钦定)→ 0 serious
T+6h    我代办 commit + force-with-lease push round 3 + gh pr merge phase-1 PR #31
T+6h05  phase-1 done @ main b6c8d10
T+6h10  我代办 spawn phase-2-correctness dev session
```

**user 介入次数**:4 次(选 B + 3 次 fix-batch ack)
**总时长**:~6 小时
**fix-batch 轮数**:4 轮(2 / 3 R2 / 4 R3 / 1 行 K3 fix)

---

## 例 3:LLM compliance bug 兜底(fix-batch-5 round 1 hang 在 commit)

**说明** dev session 写完 round 1 fix(SPEC.md 改动)但 hang 在 git commit + push 步,我代办 commit + force push 救场。

**关键时间线**:
```
T+0     fix-batch-5 dev session spawn
T+30m   step 1-4 跑完(快路径)
T+35m   step 5 PR #46 提交
T+40m   step 5.5 L4b timeout(headless claude 5 min 超时)
T+42m   §6.5 verify round 1 跑(opus,codex 401 cascade)
T+50m   verify round 1 verdict: needs_revision(0 BLOCKS + 2 serious + 3 minor SPEC drift)
T+55m   dev session 写完 SPEC.md round 1 fix(改 status enum + audit-row contract + cov path)
T+50m   dev session **hang** — git status M files 但 0 unpushed commits
T+1h20  user 问 check 状态
T+1h21  我诊断:dev session hang 在 commit + push 步(LLM compliance bug form (a))
T+1h22  我代办 git commit + force push round 1 commit 423e484
T+1h23  CI / L4b 重跑触发,verify round 2 等触发
```

**关键观察**:
- LLM 写完 SPEC.md 后 hang 在 commit 命令(form (a) 变体)
- 救场关键:main session /loop 监控 + user 主动问 check
- 兜底命令:`git add ... && git commit -m '...' && git push --force-with-lease`

详见 [../lessons-learned/llm-compliance-bugs.md](../lessons-learned/llm-compliance-bugs.md) form (a) 章节。

---

## 例 4:并行加速(phase-2 卡住 → spawn phase-3/4/5 并行)

**说明** phase-2 PR 卡 fix-batch-5 SPEC fix 期间,user 要求加速 → spawn phase-3/4/5 并行 dev session,提前撞 finding 一次性 batch review。

**决策依据**:
- phase-3/4/5 跟 phase-2 一样独立 acceptance test 套(不写新代码)
- 它们之间无 implementation 依赖
- 撞类似 finding 一次性给 architect batch 比 serial 快 3-4 倍

**关键时间线**:
```
T+0     phase-2 dev session 跑完撞 4 finding,fix-batch-5 SPEC 在 round 1 fix
T+1h20  user 问"能不能并行更多"
T+1h25  我代办 spawn phase-3-robustness / phase-4-concurrency / phase-5-adversarial 三路并行
T+1h26  3 worktree + 3 dev session active
T+~3h   3 phase 各自跑完,撞 N + M + K finding
T+~3h+30m 我整合 brief → user 一次性 batch review → architect 起 fix-batch-6/7/...
```

**预计 saved time**:~6-12h(serial 跑 phase-3 → done → phase-4 → done → phase-5 估 12-20h vs 并行 ~5-8h)

---

## 例 5:跨 session 文件 IPC(architect 起 SPEC → user ack → main 代办 merge)

**说明** 3 个 session(architect / user / main)零口述,全靠 git PR + 文件传递。

**流程**:
```
1. architect session(user 另开)写 SPEC.md
2. architect 跑 git push origin architect/fix-finding-batch-N-{...}
3. architect 跑 gh pr create(PR #N 出来)
4. architect copy PR # 给 user
5. user 把 PR # 转给 main session(我)
6. 我跑 gh pr view {N} 拉 PR body / files 列表 / CI status
7. 我做 sanity review(对照 SPEC §X.Y / fix-batch 模式 / boundary 等)
8. 我写 brief 给 user(等 1 字 ack)
9. user 回 "ack"
10. 我代办 gh pr merge {N} --squash + delete branch + git pull origin main
11. 我代办 git worktree add 4 个 worktree + spawn 4 dev session
12. dev session 自跑 5-step + L4b + verify + auto_merge
13. dispatcher daemon 检测 fix-batch 全 merged → spawn 下游
```

**关键设计**:user 不需要 copy 大段文本,只输入 1 字 "ack" / "选 A"。所有上下文走 git。

---

## 怎么用这些例子

### 你刚开始 setup

读例 1(完整 sub-task 闭环)→ 你知道 dev session 该长什么样 + 期待什么时间线。

### 你撞质量问题(verify needs_revision)

读例 1 round 1 fix → 你知道 §6.5 revision 闭环怎么走。

### 你撞 dev session hang

读例 3(LLM compliance bug 兜底)→ 你知道怎么救场。

### 你想加速(serial 太慢)

读例 4(并行加速)→ 你知道何时违反 SKILL serial 设计加速。

### 你不知道怎么协调 architect / user / main 3 角色

读例 5(跨 session 文件 IPC)→ 你知道完整决策流。

---

## 完整版示例(待补)

如果你想看更详细的:
- [pr-30-full-cycle.md](pr-30-full-cycle.md):fix-k5 PR #30 完整 PR body + verifier_report + L4b review(待补)
- [phase-1-fail-greedy-cycle.md](phase-1-fail-greedy-cycle.md):phase-1-bootstrap 完整 RESULTS.md + 6 finding 文件(待补)
- [fix-batch-3-r2-spec.md](fix-batch-3-r2-spec.md):fix-batch-3 R2 真实 SPEC(脱敏)(待补)

社区 PR 欢迎补这些详细案例。
