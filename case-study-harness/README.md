# Case Study:harness v3 项目

本方法论的实战来源。100+ 小时,30+ PR auto_merged,5 fix-batch,5 phase 架构验证。

---

## 项目背景

**harness v3** = 企业级 Agent 工作台(Enterprise Agent Workbench)
- v5 11 层架构(K0 Adapter / K1 Runtime / K2 Memory / K3 Action / K4 Feedback / K5 Governance / K6 Evolution + 横切 ledger / activity / time / errors)
- 17 主 track + 14 Phase 1.5 验证 sub-task
- Python 3.11+ + asyncio + Pydantic v2 + SQLite WAL
- 仓库:jaysu66/harness(private)

---

## 实战数据

| 维度 | 数据 |
|---|---|
| 总时长 | ~100 小时(2026-04-29 → 2026-05-03) |
| Merged PRs | 30+ |
| auto_approve 误 merge | **0**(7-gate 100% 命中) |
| boundary check 拦截 | 2 次(dev 试图绕 mypy) |
| LLM compliance bug 实战 | 7 次 form (a)/(b)/(c)/(d)mix |
| Dispatcher daemon 兜底 | 5 次 spawn verify 救场 |
| API stream timeout 恢复 | 1 次大规模(3 路同时撞,~75 min 恢复) |
| User 实际介入时间 | ~10 小时(其余全自动) |

---

## 时间线(简化版)

详见 [timeline.md](timeline.md)

```
Day 1(~04-29):17 主 track 全 merged(完成 Phase 0/1/2/3/4)
Day 2(~04-30):Phase 1.5 启动 — errors-test-completeness / findings-protocol / console-backend
Day 3(~05-01):fix-batch-1(5 个 fix)+ console-frontend / fix-k3-k4
Day 4(~05-02):fix-k5(round 1 cascade fallback)+ phase-1-bootstrap 启动 + 撞 6 finding
Day 5(~05-03):
  - fix-batch-2(R1, 4 个 fix)→ phase-1 重跑撞 K3
  - fix-batch-3(R2, 3 个 fix)→ phase-1 重跑撞 K3 SQLite lock
  - fix-batch-4(R3, 1 个 SQLite single-conn)→ phase-1 重跑 17/18 pass
  - 1 行 K3 fix → phase-1 0 finding 收敛
  - phase-1 PR #31 merged → phase-2 spawn → 撞 4 finding
  - fix-batch-5(纯架构决策,0 代码改)→ phase-2 round 1 进行中
  - phase-3/4/5 并行 spawn 加速
```

---

## 关键 Pattern 实战验证

### Pattern 1:fail-greedy + fix-batch 集中修复

phase-1 撞 6 finding → architect 集中起 fix-batch-2(4 个 fix SPEC)→ user ack → 4 路并行 dev session ~3h 全 merged → phase-1 重跑。

**vs serial 单独修每个 finding**:节省 ~3 倍时间(~3h vs ~10h serial)。

### Pattern 2:auto_approve 7-gate

30+ PR 全 7-gate 自动判,0 误 merge。每个 PR auto-merge 决策 < 1 秒(7 个布尔 AND)。

vs human review:每 PR ~5-15 min review,30 PR 累积 2.5-7.5h user 时间。

### Pattern 3:跨模型 Verifier(cascade fallback)

7 次 codex 401 / quota / refresh_token_reused → cascade fallback 到 opus → 全部成功 verify。

vs 单模型(只用 claude):同质化偏见,L2 验收漏抓 11 类 dev 自检漏的问题。

### Pattern 4:Dispatcher daemon 兜底 LLM compliance bug

5 次 dev session passive 等 trigger / PROGRESS 写非标值 → daemon 30s polling 自动 spawn verify → 救场。

vs 没 daemon:user 必须每次手动 spawn → 长跑必崩。

---

## 关键失败 + 如何修

详见 [../lessons-learned/](../lessons-learned/)

| 失败 | 修复 |
|---|---|
| fix-k1 PR #25 round 1 squash-merge 时 codex spawn fail → 直接 merge 没等 verify | PR #37 后续补 4 件事(B1+R1+R2+R3),并加 cascade fallback 强制 |
| phase-1 重跑撞 K3 SQLite lock(fix-batch-2 R1 实施改 fire-and-forget → sync await) | fix-batch-4 R3 SQLite single-conn cache + asyncio.Lock |
| fix-batch-2 R1 SPEC 把 "caller 必须传" 当 backward-compat | fix-batch-3 R2 改为 "default-on,显式传是高级用法",+ self-criticism 入 PLAN §7 |
| phase-2 SPEC 跟 governance-sandbox HANDOFF §4.1 deferred 决策打架 | fix-batch-5 SPEC §5.3 split + self-criticism 入 PLAN §8 |
| 3 路 verify session 同时撞 stream timeout | 等 75 min + ping pong + canary retry |

---

## 数字看 ROI

如果不用本方法,完全 user 主导:
- 30 PR × ~2-3h dev + ~1h review = 90-120 小时
- + 5 fix-batch 撞架构 bug 每次 4-8h debug = 20-40 小时
- + 长跑卡死手动救场 ~10-20 小时

**预估 user 时间:120-180 小时**

实际 user 时间:**~10 小时**

**节省:90%+ user time,12-18 倍效率**。

---

## 项目状态(2026-05-03)

- ✅ Phase 0/1/2/3/4 全完(16 主 track merged)
- ✅ Phase 1.5 fix-batch + console:9/9 merged
- ✅ Phase 1.5 phase-1-bootstrap done
- 🟡 Phase 1.5 phase-2-correctness round 1 进行中(fix-batch-5 SPEC fix)
- 🟡 Phase 1.5 phase-3/4/5 并行加速 spawn 中
- ⏳ Phase 2 业务层(workbench-backend / 真业务 agent 集成测试)

---

## 给读者的话

本方法论是**实战出来的,不是设计出来的**。

每条原则、每个机制、每个 prompt 都对应 harness 实战中的具体 fail 案例。如果你撞类似问题,大概率本 repo 有对应解。

如果你撞 repo 没覆盖的问题,欢迎提 PR,把你的 lesson learned 加进 [../lessons-learned/](../lessons-learned/)。
