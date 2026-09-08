# 数学建模项目 Agent 协议

本文件是项目常驻运行指令。保持简洁。
对话历史不是项目权威状态。

## 路径

`PROJECT_ROOT`：当前项目仓库根目录。

`SKILL_ROOT`：

`$HOME/MathModelingWorkspace/skills/math-modeling-skill`

`SKILL_ROOT` 只读；所有比赛产物和内部状态只写入 `PROJECT_ROOT`。

## 主 Skill

数学建模工作开始前读取：

`$HOME/MathModelingWorkspace/skills/math-modeling-skill/SKILL.md`

严格执行其渐进式加载规则。

禁止一次性递归加载整个 Skill。

原有工作流保持不变：

`建模手 → 编程手 → 论文手`

固定门禁仍只有：

`M1 → P1 → P2 → W1 → W2`

不得新增固定门禁。

## 权威项目状态

跨账号、会话或设备恢复时，权威状态依次为：

1. 实际项目文件；
2. 本地 Git 历史；
3. `CURRENT_TASK.md`；
4. `.handoff/GATE_STATE.json`；
5. `DECISIONS.md`；
6. `HANDOFF.md`；
7. `AI使用日志.md`。

聊天记录、共享链接和深度链接仅供人工参考，不是恢复依赖。

## 恢复协议

新会话、新账号或新设备接手后：

1. 运行确定性的 handoff 检查；
2. 核验 `.handoff/SKILL.lock`；
3. 读取 `CURRENT_TASK.md`；
4. 读取 `.handoff/GATE_STATE.json`；
5. 读取 `HANDOFF.md`；
6. 检查 Git HEAD 和 working tree；
7. 只读取 `CURRENT_TASK.md` 引用的决策条目；
8. 判断当前阶段；
9. 只加载当前阶段真正需要的 Skill 文件；
10. 从 `Next Action` 继续。

确定性检查命令：

    python "$HOME/MathModelingWorkspace/skills/math-modeling-skill/tools/handoff/scripts/handoff.py" \
      check \
      --skill-root "$HOME/MathModelingWorkspace/skills/math-modeling-skill" \
      --project-root . \
      --strict

不得因为换账号或缺少历史对话而重做仍然有效的工作。

## 门禁连续性

门禁状态只能是：

`NOT_STARTED / PENDING / PASS / FAIL / BLOCKED / STALE`

跨账号本身不会使 `PASS` 失效。

只有门禁保护的输入或产物发生实质变化时，相关 `PASS` 才失效并变为 `STALE`。

不得静默把 `FAIL`、`BLOCKED` 或 `STALE` 改为 `PASS`。

不得重新执行仍然有效的已通过门禁。

## 当前任务

`CURRENT_TASK.md` 是当前工作点的简明权威记录。

保持短小，只记录：

- 当前阶段和目标；
- 门禁摘要；
- 相关决策 ID；
- 权威输入和输出；
- 已知问题；
- `Next Action`；
- `Do Not Redo`。

完成一个实质性工作单元后简短更新一次。

## 决策

`DECISIONS.md` 采用只追加模式。

不得静默改写旧决策。

改变旧决策时新增条目，并通过 `Supersedes` 指向被替代决策。

## 接力

`HANDOFF.md` 只记录最近一棒做了什么，不替代 `CURRENT_TASK.md`。

准备换账号前：

1. 停止启动新的长任务；
2. 完成安全检查点；
3. 更新状态文件；
4. 运行 handoff 检查；
5. 将重要修改提交到项目本地 Git。

文件压缩和传输由参赛队员人工完成，本 Skill 不操作。

## AI 使用日志

`AI使用日志.md` 采用只追加模式，按实际发生情况及时记录。

不得事后凭猜测补造历史记录。

## 内部状态边界

以下内容属于内部工作状态，不得进入正式论文：

- 门禁状态和 Subagent 回执；
- `CURRENT_TASK.md`；
- `DECISIONS.md`；
- `HANDOFF.md`；
- `.handoff/`；
- Git/hash/checkpoint；
- 内部质检术语。

官方要求的 AI 使用声明或详情，应依据真实 `AI使用日志.md`
和当届官方规则另行整理。

## 详细协议

只有需要处理跨账号恢复、异常状态或接力规则争议时，再读取：

`$HOME/MathModelingWorkspace/skills/math-modeling-skill/references/跨账号接力协议.md`
