---
trigger: always_on
---

# Insight Design System (IDS)
**Project:** Insight Medical Research Platform  
**Target User:** 临床医生、医学生（非统计学专业背景）  
**Core Philosophy:** 拒绝黑盒 (De-blackboxing) & 零手册 (Zero-Manual)

---

## 1. 设计原则 (Design Principles)

### 1.1 认知减负 (Cognitive Ease)
*   **原则**：不要让用户做“选择题”，而是做“判断题”。
*   **实践**：系统基于数据特征（如方差齐性、样本量）自动推荐统计方法。用户只需确认“接受推荐”或“手动修改”，而非从头检索算法。

### 1.2 预防式约束 (Preventative Constraints)
*   **原则**：错误应该在发生前被阻止，而不是报错后才提示。
*   **实践**：
    *   **灰度禁用**：线性回归的结局变量下拉框中，分类变量（如死亡/存活）自动置灰不可选。
    *   **实时预警**：当用户同时选中两个高度共线性的变量（如 eGFR 和 Scr）进入模型时，即时弹出黄色警告条：“检测到多重共线性风险 (VIF > 10)”。

### 1.3 渐进式披露 (Progressive Disclosure)
*   **原则**：新手看临床结论，专家看统计细节。
*   **实践**：
    *   **L1 (摘要层)**：**智能解读面板**。用自然语言描述：“eGFR 每下降 10 个单位，死亡风险显著增加 15% (P<0.05)。”
    *   **L2 (证据层)**：**三线表 (Table)**。展示 HR 值、95% CI、P 值。
    *   **L3 (诊断层)**：折叠在“详细诊断”中，展示残差图、PH 假定检验、VIF 值。

### 1.4 结果即结论 (Result as Insight)
*   **原则**：不仅展示数字 (P=0.04)，更要解释意义。
*   **实践**：所有关键指标必须配备 Tooltip 解释。所有导出图表必须符合学术期刊发表标准 (Publication-Ready)。

---

## 2. 交互模式 (Interaction Patterns)

### 2.1 “智能推荐 + 人工确认” (Suggest & Confirm)
*   **场景**：数据上传与清洗。
*   **交互**：系统自动扫描数据，将变量标记为 `Categorical` 或 `Continuous`。用户在“数据体检”页面浏览 Tag，仅在系统判错时点击修正。

### 2.2 数据体检 (Data Health Check)
*   **场景**：分析前的必备步骤。
*   **视觉**：交通灯色系反馈。
    *   🔴 **严重 (Blocker)**：非数值字符、因变量完全缺失。 -> 动作：**“去清洗”**
    *   🟡 **警告 (Warning)**：缺失率 > 20%、类别样本极少。 -> 动作：**“智能填补”**
    *   🟢 **健康 (Healthy)**：数据完整，分布正常。

### 2.3 流程叙事化 (Narrative Flow)
*   **导航结构**：左侧菜单按照科研论文撰写顺序排列：
    1.  **数据准备** (Data Readiness)
    2.  **基线特征** (Baseline / Table 1)
    3.  **统计推断** (Inference / PSM / Survival)
    4.  **多因素建模** (Modeling)
    5.  **临床应用** (Nomogram)

---

## 3. 视觉体系 (Visual System)

### 3.1 色彩规范 (Color Palette)
基于医学科研的冷静与严谨感微调。

| 语义 | 色值 (Hex) | 用途 |
| :--- | :--- | :--- |
| **Primary (Brand)** | `#3B71CA` | 主按钮、激活状态、链接 (Science Blue) |
| **Significance (Hot)** | `#D32F2F` | **P < 0.05**，危险因素 (HR > 1)，错误信息 |
| **Safety (Cool)** | `#2E7D32` | 保护因素 (HR < 1)，校验通过，低风险 |
| **Warning** | `#E6A23C` | 数据缺失警告，模型不收敛风险 |
| **Neutral Text** | `#212121` | 正文、表格数值 |
| **Secondary Text** | `#606266` | 标签、辅助说明 |
| **Background** | `#F5F7FA` | 页面背景 (浅灰，突显白色卡片) |

### 3.2 排版与字体
*   **数字/代码**: `"Roboto Mono", Consolas, monospace` (用于 P值、置信区间，确保对齐)。
*   **正文**: `"Helvetica Neue", "PingFang SC", sans-serif`。

---

## 4. 核心组件规范 (Component Specs)

### A. 学术三线表 (Publication Table)
用于 Table 1 和模型结果展示，模拟论文发表样式。
*   **样式**：
    *   顶底边框加粗 (2px black)，表头下边框 (1px black)。
    *   去除竖线，去除斑马纹。
*   **智能交互**：
    *   **显著性高亮**：`P < 0.05` 时，文字加粗并标红。
    *   **置信区间**：若 `95% CI` 跨越 1 (如 0.8-1.2)，显示为灰色（无意义）；否则显示为黑色。
    *   **决策透明化**：P 值旁显示微小的 `?` 图标，Hover 显示：“此处使用了 **Fisher 精确检验**，因为期望频数 < 5。”

### B. 数据录入表单 (Forms)
*   **Label**: 统一使用 `label-position="top"`。
*   **Helper Text**: 复杂项下方必须有灰色解释文字。
    *   *例：“时间变量”下注明：“请输入随访时长（如月/天）”。*
*   **Select**: 必须支持 `filterable` (搜索)，多选时使用 Tags 展示。

### C. 智能解读面板 (Interpretation Panel)
位于模型结果表格上方的高亮区域。
*   **背景色**: 极浅的品牌色背景 (`#ecf5ff`)。
*   **内容**: 动态生成的自然语言结论。
    *   *例*: "在校正了年龄、性别后，**高血压** 是全因死亡的独立危险因素 (HR=1.5, 95% CI: 1.1-2.1)。"

### D. 绘图组件 (InsightChart)
基于 Plotly.js 封装。
*   **统一配置**:
    *   **配色**: 分组对比使用 [`#3B71CA` (组A), `#E6A23C` (组B)]。
    *   **参考线**: 必须标注 OR=1, P=0.05 等参考线（虚线灰色）。
*   **导出功能**: 必须提供 `下载高清 PNG (300 DPI)` 和 `下载 SVG` 按钮。

---

## 5. 文案与术语对照 (Micro-copy & Terminology)

界面优先显示**临床术语**，Tooltip 或副标题显示**统计术语**。

| 界面显示 (UI Label) | 统计学术语 (Stat Term) | Tooltip 解释 / 备注 |
| :--- | :--- | :--- |
| **结局变量 (Outcome)** | Dependent Variable (Y) | 您希望预测的结果（如死亡、复发）。 |
| **影响因素 (Predictors)** | Independent Variable (X) / Covariates | 可能影响结局的变量。 |
| **处理变量 (Treatment)** | Group Variable | 区分实验组和对照组的变量（0/1）。 |
| **效应值 (Effect Size)** | Coef / OR / HR | 正数/大于1代表促进风险，负数/小于1代表抑制风险。 |
| **数据填充 (Repair)** | Imputation | 使用统计学方法补全缺失值。 |
| **数值化 (Digitize)** | One-Hot Encoding | 将文字类别（男/女）转换为数字（0/1）。 |

---

## 6. 全局“知识胶囊” (Global Knowledge Base)
在页面右上角设置悬浮球或帮助中心入口。
*   **Table 1 页**: 展示“如何选择 T 检验还是卡方？”的决策树图。
*   **PSM 页**: 展示“倾向性评分匹配原理”动图。
*   **生存分析页**: 解释“删失 (Censored)”的概念。

---

## 7. 异常处理 (Error Handling)
*   **空状态 (Empty State)**: 绝不留白。展示插画 + 引导文字 + 行动按钮（如：“暂无模型结果，[去配置参数]”）。
*   **后端错误**: 捕获 500 错误，转化为友好提示：“服务器正在处理大量数据或遇到格式问题，请检查数据是否存在特殊字符。”

---

## 8. 开发实现建议 (Implementation Notes)

前端 (Vue 3 + Element Plus) 需封装以下基础组件以统一规范：

1.  **`InsightCard.vue`**: 统一 Header (标题+操作区) 和 Body 的 Padding。
2.  **`PublicationTable.vue`**: 封装 `el-table`，预设三线表样式，接收数据并自动处理 P 值高亮。
3.  **`GlossaryTooltip.vue`**: 统一的术语解释组件，标准化问号图标样式。
4.  **`StatTag.vue`**: 根据 P 值自动渲染 🔴/🟢/⚪ 状态标签。
5.  **`InterpretationPanel.vue`**: 接收统计结果对象，输出 HTML 格式的解读文本。