# Track {X}: {Layer Name}

> 用户填这个模板。完成后 freeze 校验 + sha256 lock。
> 12 段必备,每段非空。

---

## §1 一句话目标

(读完知道这个 sub-task 做什么。≤ 50 字)

例:实施 K0 Model Adapter,让业务代码统一通过 ModelAdapter 调用 LLM,不直接 import anthropic / openai。

---

## §2 你是谁(给 Dev Agent 看)

你是 {AI/CLI 名字} session,被分配到 Track {X}。你做这一个 sub-task,不碰其他 track 的代码。

---

## §3 涉及的层 / 模块

(选 1-2 层。3 层以上要拆 sub-task)

- [ ] (layer 1)
- [ ] (layer 2)
- [ ] 横切 ledger / activity / gateway / ...

---

## §4 关联文档(必读)

- [ ] {project}/ONBOARDING.md(项目入门)
- [ ] {project}/DEV_SPEC.md §1-§7(代码规范 + N 审查)
- [ ] {project}/CRITIQUE_HISTORY.md §9(33 条修改约束)
- [ ] {project}/ARCHITECTURE.md §2.{你的层}(技术选型)
- [ ] {project}/REQUIREMENTS.md §3.{你的层}(功能需求)
- [ ] tasks/_contracts/{你的层}_contract.py(必读,实施这个 Protocol)
- [ ] tasks/_contracts/errors.py(异常层级)
- [ ] tasks/_contracts/types.py(共享类型)
- [ ] (其他 track 的 HANDOFF.md,如有依赖)

---

## §5 任务步骤(给 Dev Agent 跑 step 3 用)

(列 ≥ 3 个步骤,每个步骤 1-2 行说明)

1. (步骤 1)
2. (步骤 2)
3. (步骤 3)
...

---

## §6 验收标准(每条必过,可粘贴 shell 命令)

### §6.1 代码质量

```bash
ruff check src/{你的层}/
ruff format --check src/{你的层}/
mypy --strict src/{你的层}/
interrogate --fail-under 100 src/{你的层}/
bandit -r src/{你的层}/        # 0 high
pip-audit                      # 0 critical
```

### §6.2 接口契约

- [ ] (实现的类) 通过 isinstance(类, {ProtocolName}) 检查
- [ ] (其他契约要求,从 contract docstring 抄)

### §6.3 测试

```bash
pytest -m unit tests/unit/{你的层}/
pytest -m unit --cov=X.{你的层} --cov-fail-under=80
pytest -m contract tests/contract/test_{你的层}_contract.py
pytest -m conformance tests/conformance/test_{你的 scenario}.py
```

### §6.4 关联 conformance scenario

- [ ] (列出本 sub-task 必跑通的 scenario,例:a2 / a3 / b1)

### §6.5 Observability

- [ ] (列出关键操作必写 ledger 的检查,grep 查 SELECT)
- [ ] (列出 Activity Stream emit 必带的事件类型)

### §6.6 33 条约束(强制 0-hit)

```bash
! grep -rn "datetime.utcnow" src/{你的层}/    # 0 hit
! grep -rn "print(" src/{你的层}/             # 0 hit (除 docstring)
! grep -rn "except Exception" src/{你的层}/   # 0 hit (除 re-raise)
! grep -rn "raise Exception\|raise RuntimeError" src/{你的层}/  # 0 hit
```

(根据具体 sub-task 加更多 33 条约束相关 grep)

---

## §7 依赖

### 你依赖什么(必须存在才能开始)
- [ ] tasks/_contracts/ 全部冻结 ✓
- [ ] (其他 track 的 HANDOFF.md,如有)

### 谁依赖你(完成后通知)
- Track {Y}:等你的 (...) 接口
- Track {Z}:等你的 HANDOFF

---

## §8 产出物清单(完成后必须交付)

### 代码文件
- [ ] src/X/{你的层}/__init__.py
- [ ] src/X/{你的层}/(其他 .py)

### 测试文件
- [ ] tests/unit/{你的层}/test_*.py
- [ ] tests/conformance/test_{scenario}.py(如新加)
- [ ] tests/contract/test_{你的层}_contract.py

### 文档
- [ ] tasks/track-{X}/HANDOFF.md(给下游 track 看,自动生成 + 你审)

---

## §9 反清单(绝对不要做)

(≥ 5 条具体,不是"别写烂代码"这种空话。每条对应 33 条修改约束之一或反范式)

- [ ] ✗ 修改 tasks/_contracts/ 已冻结的文件
- [ ] ✗ 修改 .github/workflows/* / pyproject.toml ruff 配置区
- [ ] ✗ datetime.utcnow()(用 utc_now)
- [ ] ✗ print() 当 log(用 structlog)
- [ ] ✗ except Exception 静默吞错
- [ ] ✗ raise Exception / raise RuntimeError(用具体子类)
- [ ] ✗ 直接 import anthropic / openai
- [ ] ✗ 在 K 层使用业务名词(发票/客户/订单)
- [ ] ✗ 同 PR 改 ≥ 2 个架构层
- [ ] ✗ TODO/FIXME 留到 main

---

## §10 Verifier 任务段(给独立 Verifier Agent 看)

### 10.1 你是 Verifier

你不能读:
- [ ] src/X/{你的层}/(已物理删除)
- [ ] tasks/track-{X}/UNDERSTANDING.md / PLAN.md
- [ ] tests/unit/{你的层}/(Dev 自测)

你只能读:
- [ ] tasks/track-{X}/SPEC_FROZEN.md
- [ ] tasks/_contracts/*.py
- [ ] {project}/DEV_SPEC.md
- [ ] {project}/CRITIQUE_HISTORY.md §9

模型:codex/gpt-5.5(优先) → claude/opus-4.7(fallback)

### 10.2 你要写的 acceptance test(verifier_test.py)

#### Positive case(SPEC 验收标准映射,≥ 5 个)

1. (Positive 1: ...)
2. (Positive 2: ...)
3. (Positive 3: ...)
4. (Positive 4: ...)
5. (Positive 5: ...)

#### Negative case(故意应失败的,≥ 5 个,用 @pytest.mark.xfail)

1. (Negative 1: 调白名单外 method 应抛 PermissionDeniedError)
2. (Negative 2: ...)
3. (Negative 3: ...)
4. (Negative 4: ...)
5. (Negative 5: ...)

### 10.3 你要跑的 conformance

```bash
pytest -m conformance tests/conformance/test_{X}.py
pytest -m conformance(全套,确认不破坏 baseline)
```

### 10.4 你要交付的

- tasks/track-{X}/verifier_test.py(独立 test,自跑通过)
- tasks/track-{X}/verifier_report.md(7 段,含 5+ 可疑点)
- tasks/track-{X}/verifier_understanding.md(≥ 100 字)

最后一行机器可读 tally:
```
<!-- l2-tally: {"verdict": "pass|needs_revision|reject", "blocks": N, "suggestions": N, "model": "..."} -->
```

---

## §11 工作量估计

- 代码:~XXX 行
- 测试:~XXX 行
- 文档:HANDOFF.md ~XX 行
- Dev Agent 预计 ⏱: X-X 小时
- Verifier Agent 预计 ⏱: 30-60 分钟

---

## §12 完成标志(可粘贴 bash)

```bash
cd packages/X

# 全过 = sub-task 完成
ruff check . && ruff format --check . && \
mypy --strict src/X/{你的层} && \
interrogate --fail-under 100 src/X/{你的层} && \
bandit -r src/X/{你的层} && \
pip-audit && \
pytest -m unit tests/unit/{你的层}/ --cov=X.{你的层} --cov-fail-under=80 && \
pytest -m contract tests/contract/test_{你的层}_contract.py && \
pytest -m conformance tests/conformance/test_{X}.py && \
! grep -rn "datetime.utcnow" src/X/{你的层}/ && \
! grep -rn "print(" src/X/{你的层}/ && \
echo "✓ {track-X} acceptance done"
```

全过 → 提 PR。

---

## 给 Reviewer 的笔记(Dev Agent 实施时填)

### 我做架构决定的地方
- (Dev Agent step 2 写 PLAN.md 时填,这里 link 过去)

### 我推翻过的方案
- (同上)

### 留给后续 sub-task 的 TODO
- (Dev Agent step 5 提 PR 时填)

---

**SPEC 状态**:draft / **frozen** / done
**Frozen sha256**:(自动填,freeze 时算)
**Frozen 时间**:(自动填)
