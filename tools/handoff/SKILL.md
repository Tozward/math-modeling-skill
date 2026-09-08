---
name: handoff
description: 数学建模项目的跨账号、跨会话和跨设备状态持久化与确定性恢复工具。
---

# Handoff

本工具只管理 `PROJECT_ROOT` 中的内部接力状态。

它不改变数学建模业务流程，也不替代：

- 建模手；
- 编程手；
- 论文手；
- M1/P1/P2/W1/W2 独立验收。

## 路径

- `HANDOFF_ROOT`：本文件所在目录。
- `SKILL_ROOT`：`HANDOFF_ROOT/../..`，只读。
- `PROJECT_ROOT`：用户数学建模项目目录，可写。

`SKILL_ROOT` 与 `PROJECT_ROOT` 必须不同。

## 原则

1. 对话历史不是项目权威状态。
2. 项目状态必须可以仅依靠磁盘文件恢复。
3. 已通过且输入未变化的门禁跨账号继续有效。
4. 文件变化使相应门禁状态变为 `STALE`。
5. 所有机械检查由确定性 Python 脚本完成，不消耗模型推理。
6. 本工具不得压缩、上传或发送项目。
7. 本工具生成的内部状态不得进入正式论文。

## 命令

实现脚本：

`scripts/handoff.py`

应提供：

- `init`
- `check`
- `record-gate`
- `invalidate`

具体语义见：

`../../references/跨账号接力协议.md`

## 渐进式加载

只有以下情况读取本文件：

- 用户明确启用跨账号接力；
- `PROJECT_ROOT/.handoff/GATE_STATE.json` 已存在；
- 用户要求恢复另一账号、会话或机器交接的项目。

普通单会话数学建模任务不需要加载本工具。
