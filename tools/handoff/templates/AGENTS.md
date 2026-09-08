# 数学建模项目 Agent 协议

本文件是项目常驻运行指令。保持简洁。

对话历史不是项目权威状态。

## 路径

`PROJECT_ROOT`：

当前比赛项目 Git 仓库根目录。

`SKILL_ROOT`：

`$HOME/MathModelingWorkspace/skills/math-modeling-skill`

`SKILL_ROOT` 只读。

所有比赛产物和内部状态只写入 `PROJECT_ROOT`。

## 主 Skill

数学建模工作开始前读取：

`$HOME/MathModelingWorkspace/skills/math-modeling-skill/SKILL.md`

严格执行其渐进式加载规则。

禁止一次性递归加载整个 Skill。

原有工作流保持：

`建模手 → 编程手 → 论文手`

固定门禁仍只有：

`M1 → P1 → P2 → W1 → W2`

不得新增固定门禁。

---

## 权威项目状态

恢复项目时，权威状态依次为：

1. 实际项目文件；
2. 本地 Git 历史；
3. `.handoff/ACTIVE_WORK.json`；
4. `CURRENT_TASK.md`；
5. `.handoff/GATE_STATE.json`；
6. `DECISIONS.md`；
7. `HANDOFF.md`；
8. `AI使用日志.md`。

聊天记录、共享链接和深度链接只供人工参考。

---

## 每次新会话首先执行

先运行：

    python "$HOME/MathModelingWorkspace/skills/math-modeling-skill/tools/handoff/scripts/handoff.py" \
      check \
      --skill-root "$HOME/MathModelingWorkspace/skills/math-modeling-skill" \
      --project-root . \
      --strict

然后核验：

`.handoff/SKILL.lock`

### 若 ACTIVE_WORK = IN_PROGRESS

视为上一会话可能被意外中断。

此时必须：

1. 保留现有 working tree；
2. 不得 checkout、reset、clean 或覆盖未提交文件；
3. 不得重新执行 `begin-work`；
4. 读取 `ACTIVE_WORK.json` 中：
   - `objective`
   - `atomic_unit`
   - `next_action`
   - `last_checkpoint`
   - `touched_files`
5. 检查相关实际文件；
6. 只加载继续该原子工作真正需要的 Skill 内容；
7. 从 `next_action` 继续；
8. 出现新的有价值进展后执行 `checkpoint`；
9. 原子工作真正完成后执行 `finish-work`。

不得因为原对话消失而重新规划整个阶段。

### 若 check 报告上一工作已 finish-work 但尚未建立 Git checkpoint

先：

1. 保留全部现有修改；
2. 根据 `last_completed` 完成必要的 `CURRENT_TASK.md` 更新；
3. 检查实际产物；
4. 建立本地 Git checkpoint；
5. 再开始下一原子工作。

### 若 ACTIVE_WORK = IDLE 且没有待收尾状态

按 `CURRENT_TASK.md` 的 `Next Action` 正常继续。

---

## 抢占安全工作原则

假设模型、客户端、连接或账号额度可以在任意时刻中断。

因此任何较大的语义工作都必须先留下恢复记录。

### 必须 begin-work 的工作

开始以下类型的工作前必须先执行 `begin-work`：

- 一个新的模型设计或模型比较单元；
- 一段需要持续推理的数学推导；
- 一个独立代码模块或求解器实现；
- 一组正式结果计算或验证；
- 一项重要结果解释；
- 一个论文章节或一组相互关联章节的实质写作；
- 一次较大的 W1/W2 修订单元；
- 其他一旦中断后重新推理会明显浪费额度的工作。

以下机械操作不要求单独 begin-work：

- 单纯读取文件；
- Git/status/hash 检查；
- 已确定命令的短执行；
- 小型格式修正；
- 极短的单点查询。

---

## 原子工作大小

一个 `atomic_unit` 应足够小，使得：

> 即使本会话立刻终止，新账号也能仅依靠磁盘状态继续，而无需重新完成大量推理。

推荐粒度例如：

- 比较某一子问题的候选模型；
- 冻结一个核心假设集合；
- 完成一个求解模块；
- 完成一次参数/边界验证；
- 生成并核验一组结果表；
- 完成一个论文主要章节；
- 核验一类关键主张—证据关系。

禁止把：

- 整个 M1；
- 整个 P2；
- 整篇论文；
- 整个 W2；

作为一个巨大的 `atomic_unit`。

---

## begin-work

长任务开始前，先执行：

    python "$HOME/MathModelingWorkspace/skills/math-modeling-skill/tools/handoff/scripts/handoff.py" \
      begin-work \
      --project-root . \
      --stage "<当前阶段>" \
      --objective "<本阶段目标>" \
      --atomic-unit "<当前原子工作>" \
      --next-action "<第一步具体动作>"

必要时追加：

- `--input`
- `--expected-output`
- `--actor`

`begin-work` 成功之后再开始昂贵推理。

如果已经存在 `IN_PROGRESS` 工作，不得覆盖。

---

## checkpoint

不按固定分钟数 checkpoint。

在出现有意义、可恢复的语义进展后 checkpoint，例如：

- 模型路线已经比较完一部分；
- 关键假设已经确定；
- 一个代码模块已经可运行；
- 一组结果已经生成；
- 一个关键结论已经核验；
- 一个章节已经形成稳定版本。

执行：

    python "$HOME/MathModelingWorkspace/skills/math-modeling-skill/tools/handoff/scripts/handoff.py" \
      checkpoint \
      --project-root . \
      --next-action "<中断后应直接执行的下一动作>"

对于当前实际涉及的重要文件，使用：

`--touch <文件>`

可重复提供。

`next_action` 必须具体到新账号无需重新思考“现在应该干什么”。

---

## finish-work

原子工作真正完成后执行：

    python "$HOME/MathModelingWorkspace/skills/math-modeling-skill/tools/handoff/scripts/handoff.py" \
      finish-work \
      --project-root . \
      --summary "<本原子工作已完成什么>" \
      --next-action "<下一原子工作是什么>"

必要时使用：

`--touch`

记录主要产物。

`finish-work` 不等于 Gate PASS。

M1/P1/P2/W1/W2 的语义仍完全由原门禁协议决定。

---

## 完成后的持久化

完成一个重要原子工作后：

1. 必要时更新 `CURRENT_TASK.md`；
2. 检查产物；
3. 在内容达到清晰语义边界时建立本地 Git checkpoint。

不需要为每次轻量 `checkpoint` 创建 Git commit。

但在：

- 准备切换账号；
- 准备换机器；
- 一个重要 atomic unit 已结束；
- Gate PASS；
- 重要模型决策冻结；

时应优先建立 Git checkpoint。

---

## CURRENT_TASK

`CURRENT_TASK.md` 记录较稳定的项目级当前状态。

它不承担每个推理步骤的实时日志功能。

原子工作正在进行时：

`.handoff/ACTIVE_WORK.json`

是即时恢复点。

原子工作完成后再简短更新 `CURRENT_TASK.md`。

---

## 门禁连续性

门禁状态只能是：

`NOT_STARTED / PENDING / PASS / FAIL / BLOCKED / STALE`

跨账号本身不会使 `PASS` 失效。

只有被验收输入或产物发生实质变化时，
相关 PASS 才失效。

不得：

- 静默把 FAIL 改为 PASS；
- 静默把 BLOCKED 改为 PASS；
- 静默把 STALE 改为 PASS；
- 因为新账号不了解历史而重做仍有效的 Gate。

---

## 正常主动接力

准备主动换账号时：

1. 不再启动新的长 atomic unit；
2. 若当前工作能安全完成，执行 `finish-work`；
3. 若无法完成，至少执行一次 `checkpoint`；
4. 更新必要的 `CURRENT_TASK.md`；
5. 更新 `HANDOFF.md`；
6. 运行 handoff `check`；
7. 建立适当的本地 Git checkpoint；
8. 完整传输项目目录。

若仍保留 `IN_PROGRESS`，
下一账号必须按异常恢复协议继续该工作，
不能另起炉灶。

---

## 文件传输

传输必须保留：

- 实际项目文件；
- 隐藏的 `.git/`；
- 隐藏的 `.handoff/`；
- 未提交的 working tree 文件。

因此不得只传 Git commit 中已经跟踪的文件。

压缩、AirDrop、U 盘或其他私下传输由参赛队员人工完成。

---

## 决策

`DECISIONS.md` 只追加。

推翻旧决策时新增条目并用 `Supersedes` 指向旧决策。

---

## AI 使用日志

`AI使用日志.md` 按真实发生情况追加。

不得事后凭猜测补造历史记录。

---

## 内部状态边界

以下内容不得进入正式论文：

- Gate 状态；
- Subagent 回执；
- `CURRENT_TASK.md`；
- `DECISIONS.md`；
- `HANDOFF.md`；
- `.handoff/ACTIVE_WORK.json`；
- `.handoff/GATE_STATE.json`；
- Git/hash/checkpoint；
- 内部质检术语。

官方要求的 AI 使用声明另按当届规则整理。

---

## 详细协议

仅在跨账号恢复、异常状态或规则争议时再读取：

`$HOME/MathModelingWorkspace/skills/math-modeling-skill/references/跨账号接力协议.md`
