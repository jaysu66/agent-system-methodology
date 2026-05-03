# API Stream Timeout(transient,~1h 内自然恢复)

## 症状

Verify session / dev session 长跑(30+ min)撞:

```
API Error: Stream idle timeout - partial response received
```

## 实战出处

harness Phase 1.5 实战(2026-05-01 14:30):**3 路 verify session 同时撞 stream timeout 死**(fix-k1 retry / frontend retry / fix-k3-k4 dev),全部 partial response。

## 核心结论

> **不要立即激进 retry。等 30-60 min 自然恢复,然后用 ping pong 测试 + canary retry。**

**激进重 spawn 在 API 没恢复时只会再死一次,~10k token 浪费 / session。**

---

## 应对协议

### Step 1:撞 stream timeout 时 — 不立即 retry

```
立即:
- 不 kill spawned session(让它自己撞 retry exhaust 退)
- 标 PROGRESS.md alert_level: api_timeout(临时)
- 等 30-45 min
```

### Step 2:30-45 min 后 — ping pong 测 API

```bash
# 单调用判 API 是否恢复(成本 ~100 token)
claude --print "respond with one word: pong" 2>&1 | head -3
# expected: "pong"
```

如 timeout / partial → 等更长(60+ min)再测;长期不通(2-4h+)mention user。

### Step 3:pong 通 — canary retry 1 个

```
代办 retry 1 个 canary(选 ROI 最高的:L4b done + approve true 那个):
- spawn 同样 prompt(重 spawn,新 PID)
- 等 30-60 min 看是否成功

如成功 → batch retry 剩下死掉的 session(3 路同时 spawn)
如还撞 timeout → 再等 60+ min(API 还没恢复)
```

### Step 4:批量 retry

```bash
# 3 路同时 spawn(当 API 已确认恢复)
for track in fix-k1-fix fix-frontend-fix fix-k3-k4-fix; do
    spawn_dev_session $track
done
```

实战 harness:**等 ~75 min 自然恢复 + ping pong succeed + 批量 retry 4 路全成功**(fix-k1 直接 merge,fix-ledger / fix-k3-k4 后续也通过)。

---

## 为什么不立即 retry

每个 dev session ~50K-100K tokens 跑一轮。激进 retry 期间 API 没恢复 → 每次都 partial → 浪费 ~10K token / 次 / session。

3 路同时 retry × 5 次 = ~150K-200K wasted token,而且加重 API 负载延缓恢复。

**等 + ping pong + canary** 模式总成本 < 5K token,success rate ~90%。

---

## 防御:写进 SKILL §11 cascade fallback

```
撞 stream timeout 时,不要 raw raise:

1. 第一次撞 → log 然后 wait 30s 自动 retry 1 次
2. 第二次撞 → wait 5 min 后 retry 1 次
3. 第三次撞 → 标 PROGRESS.md alert_level: api_timeout + 退出 session(让 main session 监控接手)

不要无限 retry — wastes token + 加重 API 负载。
```

---

## API 全崩 vs 单点 timeout 区分

| 现象 | 判断 | 应对 |
|---|---|---|
| 1 路 timeout,其他 OK | 单点 partial(可能 prompt 太长 / 模型瞬时 spike) | retry 1 次 + 3 路 ping pong |
| 3 路全 timeout | API 全崩 | 等 30-60 min + ping pong + canary |
| ping pong fail 4h+ | API 长期 down | mention user(SKILL §4.2 mention 5)|

---

## 实战时间线(harness 2026-05-01)

```
14:30  3 路 verify session 同时撞 stream timeout
14:35  我标 PROGRESS api_timeout + 退掉 session,等
15:00  ping pong → still timeout,继续等
15:45  ping pong → "pong" ✓ API 恢复
15:50  canary spawn fix-k1 verify retry → 30 min 后 verdict pass
16:25  批量 retry 剩 3 路 → 全成功
17:30  4 路全 merged
```

总恢复时间 ~3h(75 min wait + 30 min canary + 30-60 min 批量)。如果激进 retry,可能需要 5-8h + 多花 100K token。
