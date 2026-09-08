---
name: handoff
description: 数学建模项目的跨账号、跨会话、跨设备及意外中断状态持久化与确定性恢复工具。
---

# Handoff

本工具只管理 `PROJECT_ROOT` 中的内部接力状态。

它不改变数学建模业务流程，也不替代：

- 建模手；
- 编程手；
- 论文手；
- M1/P1/P2/W1/W2 独立验收。

## 路径

- `HANDOFF_ROOT`：本文件所在目录；
- `SKILL_ROOT`：`HANDOFF_ROOT/../..`，只读；
- `PROJECT_ROOT`：用户比赛项目目录，可写。

`SKILL_ROOT` 与 `PROJECT_ROOT` 必须是两个独立 Git 仓库。

## 原则

1. 对话历史不是项目权威状态。
2. 项目必须可以仅依赖磁盘文件恢复。
3. 长语义工作开始前先写 `ACTIVE_WORK`。
4. 有意义的中间进展使用轻量 checkpoint。
5. 意外中断后优先恢复未完成 atomic unit，不重新规划整个阶段。
6. 已通过且输入未变化的 Gate 跨账号继续有效。
7. 文件变化使相关 Gate 失效规则仍由原协议管理。
8. 确定性检查不消耗模型推理。
9. 本工具不压缩、上传或发送比赛项目。
10. 内部 handoff 状态不得进入正式论文。

## 状态文件

机器状态包括：

- `.handoff/SKILL.lock`
- `.handoff/GATE_STATE.json`
- `.handoff/ACTIVE_WORK.json`
- `.handoff/gate-evidence/`

其中：

`ACTIVE_WORK.json`

专门保存可以承受模型、客户端、连接或账号突然中断的即时恢复点。

## 命令

实现：

`scripts/handoff.py`

命令：

- `init`
- `check`
- `begin-work`
- `checkpoint`
- `finish-work`
- `record-gate`
- `invalidate`

### begin-work

在较大的语义工作开始前写入：

- stage；
- objective；
- atomic unit；
- first next action；
- 输入；
- 预期输出；
- 当前 Git/working-tree 快照。

### checkpoint

保存：

- 当前 Git HEAD；
- working tree；
- 新 next action；
- 涉及文件及 SHA-256；
- 可选 note。

### finish-work

结束当前 atomic unit，
保存最近完成内容与下一动作。

它不代表任何 Gate PASS。

## 恢复

如果 `check` 检测：

`ACTIVE_WORK = IN_PROGRESS`

必须保留 dirty working tree，
从记录的 `next_action` 继续。

如果上一工作已 `finish-work` 但尚未完成 Git checkpoint，
先完成持久化收尾，再开始新任务。

详细语义见：

`../../references/跨账号接力协议.md`

## 渐进式加载

只有以下情况读取本文件：

- 用户启用跨账号接力；
- `PROJECT_ROOT/.handoff/` 已存在；
- 用户恢复其他账号、会话或机器留下的项目；
- 项目启用了抢占安全工作记录。

普通无需接力的单会话任务不必加载本工具。
