# Force Push Safety(rebase + force-with-lease)

## 核心规则

> ⚠️ **永远用 `--force-with-lease` 而不是 `--force`**
> ⚠️ **永远不 force push 到 main / master**
> ⚠️ User 明确授权才 force push,不要默认行为

---

## 何时需要 force push

### 场景 1:rebase 后 push round N fix

dev session round 1 fix → rebase main(为了拿最新依赖)→ commit history rewrite → 必须 force push 才能更新 PR。

```bash
git fetch origin --quiet
git rebase origin/main
git push --force-with-lease origin feat/track-{TRACK}
```

### 场景 2:amend 修上一个 commit

```bash
git commit --amend
git push --force-with-lease origin feat/track-{TRACK}
```

### 场景 3:revert 错的 commit

```bash
git reset --hard HEAD~1
git push --force-with-lease origin feat/track-{TRACK}
```

---

## `--force-with-lease` vs `--force`

### `--force-with-lease`(推荐)

```bash
git push --force-with-lease origin feat/track-X
```

行为:
- **检查 remote 是否被别人 update 过**
- 有 update → reject(防你覆盖别人的 commit)
- 无 update → 安全 force push

### `--force`(危险)

```bash
git push --force origin feat/track-X  # 别用!
```

行为:
- **盲目覆盖 remote**(不管别人有没有 push)
- 多人协作时:你 push 之后另一个 dev 已经 push 了 commit X → 你 force push 覆盖了 X → X 永远丢

---

## 何时绝对不 force push

### Rule 1:main / master / production branch — 永远不

```bash
# 错!
git push --force origin main

# 错!
git push --force-with-lease origin master
```

如果撞错的 commit 进 main,**revert 一个新 commit** 而不是 force push:

```bash
git revert <commit-sha>
git push origin main  # 普通 push,加 revert commit
```

### Rule 2:别人正在用的 branch — 不

如果你的 PR branch 有 reviewer 在 review,force push 会让 reviewer 之前看的内容失效。先沟通再 force push。

### Rule 3:已 merged 的 commit — 不

merged 进 main 的 commit 永远在 history,不要试图删除。撞错 → revert 一个新 commit。

---

## 实战出处

harness phase-1 worktree 实战:
- round 1 commits 写在 base = `d7ed94e`(早期 commit)
- 后来 main 上 fix-batch-2/3/4 各 5 个 commit 进 main
- 我代办 rebase phase-1 → HEAD 重新基于 main 最新 → commits 改变 sha
- `git push --force-with-lease` 覆盖 remote(remote 仍是早 base)

实战命令:
```bash
cd ../harness-track-arch-validation-phase-1-bootstrap
git fetch origin --quiet
git rebase origin/main 2>&1 | tail -5
# Successfully rebased and updated refs/heads/feat/track-arch-validation-phase-1-bootstrap.

git push --force-with-lease origin feat/track-arch-validation-phase-1-bootstrap 2>&1 | tail -3
# To https://github.com/jaysu66/harness.git
#  + f71249d...9c56b7d feat/track-arch-validation-phase-1-bootstrap -> feat/track-arch-validation-phase-1-bootstrap (forced update)
```

---

## main session 代办 force push 决策流

```
我撞需要 force push:
  ↓
是 main / master / production?
  ↓ Yes → 拒绝 + 用 revert commit 代替
  ↓ No
是 user 已 ack 的 round N fix?
  ↓ No → 等 user 授权 / brief 给 user
  ↓ Yes
有 reviewer 在 review 这个 PR?
  ↓ Yes → 提示 user 先告诉 reviewer
  ↓ No
跑 git push --force-with-lease(不要 --force)
  ↓
remote update detected? (force-with-lease 失败)
  ↓ Yes → 不强推,fetch + rebase 重试
  ↓ No → success
```

---

## 速查卡

```
✅ git push --force-with-lease origin feat/track-X   (rebase 后,user 已 ack round N fix)
✅ git revert <sha> + git push origin main           (撞错的 main commit)
❌ git push --force origin <anything>                (盲目覆盖,危险)
❌ git push --force-with-lease origin main           (永远不 force push main)
❌ git reset --hard origin/main(已有 commits)        (会丢 work)
```
