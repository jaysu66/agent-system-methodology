# HANDOFF.md — Track {X}

> Dev Agent step 5(merge 后)写,给下游 sub-task 看。
> 4 段必备:做了什么 / 已知限制 / 下游怎么接 / 系统问题(实时记)

---

## §1 做了什么

(简洁,1-3 段)

实施 X 接口,在 src/X/{你的层}/ 加了:
- A.py(line 1-100):...
- B.py(line 1-50):...

Closes finding F-XXX-{name}(原 PHASE-N 撞的 finding,如有)。

---

## §2 已知限制(deferred,留给 Phase 2 / 业务层)

(明文列出本 sub-task 没做但相关的事 — 防 architect 起 SPEC 时跟 HANDOFF 打架)

1. **限制 1**:本实施 X 接口走的是 Phase 1 in-process 路径,Phase 2 接 sub-process 时需要升级 Y。Trigger:Phase 2 业务层启动时。
2. **限制 2**:...
3. **限制 3**:...

---

## §3 下游怎么接

### 下游 sub-task 怎么 import 我的代码

```python
from X.{你的层} import (
    PublicClass,
    PublicFunction,
)
```

### 下游 sub-task 用我的接口要注意

- 必须在 `__init__()` 时传 `ledger=` 给 PublicClass(否则 fallback warn-once,observability 缺)
- 调 `method(trace_id=..., **params)` 必须传 `trace_id`(三级 resolve:显式 > contextvar > fallback warn-once)
- {其他 caller 必知的契约}

### 上游链:谁的 HANDOFF 你也要看

- track-{Y}:加了 Z 接口,我用了
- track-{W}:加了 V Protocol,我实施了

---

## §X 系统问题(实时记 — 每个 dev session 必填段)

> **关键**:每个 dev session 跑过程中撞到的 SKILL/tooling/workflow 卡点,**实时**记在这里。
> 跑完一波集中给 architect / main session 看,决定哪些是真痛点要修,哪些 nice-to-have。
>
> 不要事后凭记忆补 — 实时记不漏细节。

### 卡点 1:(简短描述)

- **症状**:dev session 跑到 step X 撞 Y,error 内容 "..."
- **workaround**:改 Z 后通过(临时方案)
- **根因 hypothesis**:SKILL §X.Y 设计漏了 ...
- **建议**:fix-batch 时改 SKILL / tooling / SPEC

### 卡点 2:...

### 卡点 3:...

---

(本 HANDOFF.md 由 dev agent 在 §6.3 archive 阶段自动生成,user / architect 后续 review)
