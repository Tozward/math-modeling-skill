# Team Extensions

本文件只面向本仓库维护者。

它不是运行时 Skill、不是 Agent 指令、不是比赛项目文件，也不得加入任何渐进式运行时加载路径。

当前 fork 基于：

- upstream project: `XiaoMaColtAI/math-modeling-skill`
- upstream version: `1.3.0`
- upstream baseline commit: `03c06743516432673671c9a2ffea9cfa6074a76d`
- baseline tag: `baseline-upstream-1.3.0`

团队分支：

`team/cumcm-2026`

---

## 一、保持不变的上游核心协议

本 fork 不改变以下基础架构。

### 三个固定角色

- 建模手
- 编程手
- 论文手

没有增加第四个固定角色。

### 五个固定门禁

`M1 → P1 → P2 → W1 → W2`

没有增加：

- AI 门禁；
- 合规门禁；
- 接力门禁；
- 第六门禁。

### 原固定交付物

各角色原有固定交付物语义保持不变。

新增的：

- gate evidence；
- handoff state；
- review records；
- AI 使用日志；

均属于内部状态或支撑流程，不应被误认为新的论文固定交付物。

### 只读 / 可写边界

`SKILL_ROOT`：

只读。

`PROJECT_ROOT`：

比赛项目与运行产物写入位置。

---

## 二、扩展 1：跨账号连续工作

新增：

- `references/跨账号接力协议.md`
- `tools/handoff/SKILL.md`
- `tools/handoff/scripts/handoff.py`
- `tools/handoff/templates/`

目的：

让不同 ChatGPT/Codex 账号、会话或设备继续同一个项目时，
不依赖聊天历史恢复状态。

权威状态来自：

- 项目文件；
- 本地 Git；
- `.handoff/GATE_STATE.json`；
- `.handoff/SKILL.lock`；
- `CURRENT_TASK.md`；
- `DECISIONS.md`；
- `HANDOFF.md`。

账号、会话或设备发生变化本身，
不得导致已经有效的门禁 PASS 被重新执行。

---

## 三、扩展 2：评审规则优先级

新增：

`references/评审规则优先级.md`

外部规则与评审说法分为：

- A — `VERIFIED_OFFICIAL`
- B — `VERIFIED_EXTERNAL`
- C — `HEURISTIC`
- D — `UNVERIFIED`

基本关系：

`A > B > C > D`

该体系的作用是阻止：

- 外部提示词冒充官方规则；
- 往届规则冒充当届规则；
- 经验数字被硬编码；
- 未核验信息直接制造 FAIL；
- 获奖概率被包装成官方评分。

---

## 四、扩展 3：M1 模型适配性终检

新增：

`references/roles/建模手/references/模型适配性终检.md`

来源之一：

`数学建模论文AI模型适配性检查提示词！（已修改）`

但没有原样复制该提示词。

吸收的主要内容：

- 题意与子问题闭环；
- 模型适配性；
- 复杂度必要性；
- 真创新 / 伪创新；
- 假设；
- 约束；
- 参数可确定性；
- 验证设计；
- 模型适用范围；
- 实现可行性。

M1 只检查设计是否值得进入实现阶段。

实际代码、收敛、结果、敏感性和复现仍属于 P1/P2。

---

## 五、扩展 4：P2 结果可靠性终检

新增：

`references/roles/编程手/references/结果可靠性终检.md`

重点检查：

- 权威输入；
- 数据预处理实际执行；
- M1 模型合同与代码一致性；
- 求解状态；
- 参数来源；
- 数值和量纲；
- 边界；
- 必要的验证；
- 误差；
- 敏感性；
- 稳健性；
- 合理的基线比较；
- 图表与结果真实性；
- 关键数字证据链；
- 独立复现。

没有机械规定：

- 所有模型必须交叉验证；
- 所有参数必须调优；
- 所有项目必须有基线；
- 所有模型必须 Monte Carlo；
- 所有模型必须泛化测试。

---

## 六、扩展 5：W2 全维度论文终审

新增：

`references/roles/论文手/references/评委全维度终审.md`

主要来源之一：

`数学建模论文全维度自查与获奖预测提示词！（标准版）`

吸收其完整论文评审思想，
但删除或降级了未经核验的所谓官方标准。

W2 覆盖：

1. 摘要与第一信息面；
2. 问题重述与分析；
3. 假设、符号与定义；
4. 模型与数学表达；
5. 算法与求解叙述；
6. 结果；
7. 图表；
8. 验证；
9. 误差、敏感性和稳健性；
10. 模型评价与适用范围；
11. 创新与贡献；
12. 数据与证据；
13. 文献；
14. 附录、代码与复现支撑；
15. 格式、匿名和合规；
16. 全文一致性与提交准备度。

不输出获奖概率。

需要总体质量概括时，
只允许使用内部：

`S / A / B / C`

准备度，
且不能映射奖项等级。

---

## 七、扩展 6：CUMCM 2026 末期 Profile

新增：

- `references/contests/cumcm/2026/README.md`
- `references/contests/cumcm/2026/官方规则清单.md`
- `references/contests/cumcm/2026/AI合规与真实性.md`

设计原则：

只在：

- CUMCM 2026 W2；
- 最终论文；
- 支撑材料；
- 最终提交；

阶段加载。

不得把该 Profile 注入：

- M1；
- P1；
- P2；

的普通建模和编程上下文。

这样避免竞赛行政规则和 AI 合规说明消耗上下文并干扰核心数学、代码与结果推理。

---

## 八、三个外部提示词的最终归属

### 模型适配性提示词

主要进入：

- M1 模型适配性终检；
- P2 结果可靠性终检。

### 全维度论文提示词

主要进入：

- W2 评委全维度终审。

### 2026 国赛 AI 全自动自查表

只保留真正有价值且经过规则核验的：

- 最终格式；
- 匿名；
- 数据真实性；
- 数值一致性；
- AI 最终声明与支撑材料；

相关思想。

没有保留其：

- AI 文风检测；
- 固定摘要 800–1000 字；
- 正文 20–32 页；
- 固定假设数量；
- 未经核验的一票否决；
- 其他伪官方硬规则。

---

## 九、渐进加载原则

新增内容必须继续遵守上游 progressive loading。

禁止为了“完整”：

- 启动时读取全部 review 文件；
- M1 同时读取 P2/W2；
- P2 同时读取 W2；
- 普通竞赛读取 CUMCM 2026 Profile；
- 建模阶段读取最终 AI 交付规则；
- 运行时读取本文件。

`TEAM_EXTENSIONS.md` 永远只用于仓库维护。

---

## 十、测试原则

任何后续维护至少应保证：

- 原 upstream tests 继续通过；
- handoff tests 通过；
- review extension tests 通过；
- 五门禁语义未改变；
- 新 review 文件仍是条件加载；
- CUMCM 2026 Profile 没有进入建模手或编程手；
- `TEAM_EXTENSIONS.md` 没有进入任何运行时路由；
- 外部提示词中的经验数字没有重新升级成官方硬规则。

---

## 十一、上游更新时

未来同步 upstream 时：

1. 先记录新的 upstream commit；
2. 对比 `baseline-upstream-1.3.0..upstream`；
3. 优先保留上游对核心 Skill 的 bug fix 和能力增强；
4. 重新检查三角色和五门禁是否发生语义变化；
5. 再逐项重新应用或调整本 fork 扩展；
6. 运行完整测试；
7. 不通过测试不得更新团队稳定标签。

不要直接用整文件覆盖的方式升级，
否则容易把渐进加载、handoff 或 review 扩展静默删除。

---

## 十二、版本识别

根 `VERSION` 保留 upstream 的：

`1.3.0`

原因：

该字段继续表示上游 Skill 基线版本。

团队 fork 的完整稳定状态通过 Git commit/tag 标识。

计划稳定标签：

`cumcm-2026-team-v1`

`.handoff/SKILL.lock`
应锁定实际正在使用的 Skill Git commit，
而不是仅依赖 `VERSION`。
