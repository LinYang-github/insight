---
trigger: always_on
---

# Insight Design System (IDS) v1.0
**Project:** Insight Medical Research Platform  
**Target User:** 医学生、临床医生（统计学非专业人士）  
**Core Values:** 专业信赖 (Professional)、循循善诱 (Guided)、清晰可释 (Interpretable)

---

## 1. 设计原则 (Design Principles)

1.  **认知减负 (Cognitive Ease)**
    *   **原则**：不要让用户做选择题，而是做判断题。能自动推断的参数（如根据Y值类型自动推荐模型）绝不让用户手动选。
    *   **实践**：复杂参数折叠在“高级设置”中，默认只展示核心参数。

2.  **结果即结论 (Result as Insight)**
    *   **原则**：不要只展示冷冰冰的数字（P=0.04），要提供解释（P<0.05，差异显著）。
    *   **实践**：所有统计表格必须支持“三线表”样式，所有关键指标必须配备 Tooltip 解释。

3.  **流程叙事化 (Narrative Flow)**
    *   **原则**：将数据分析过程视作撰写一篇论文：数据 -> 基线 -> 方法 -> 结果。
    *   **实践**：左侧导航栏采用线性叙事结构，状态指示灯明确当前进度。

---

## 2. 色彩体系 (Color System)

基于 Element Plus 默认色板进行微调，使其更具“医学科研”的冷静与严谨感。

### 品牌色 (Primary)
用于主按钮、激活状态、关键引导。
*   **Science Blue**: `#3B71CA` (比默认Element Blue更深沉一点，显得更稳重)
    *   *Hover*: `#5A8FDE`
    *   *Active*: `#2D5AA8`

### 功能色 (Functional)
用于统计显著性、警告及状态反馈。
*   **Significance Red (显著/风险升高)**: `#D32F2F` (用于 P<0.05 或 OR>1 的高亮)
*   **Safety Green (安全/保护因素)**: `#2E7D32` (用于 OR<1 或 校验通过)
*   **Warning Orange**: `#ED6C02` (用于数据缺失警告、模型不收敛风险)
*   **Info Gray**: `#0288D1` (用于中性提示、帮助文档链接)

### 中性色 (Neutrals)
用于文本、边框、背景，保证长时间阅读不疲劳。
*   **Text Primary**: `#212121` (正文、表格数值)
*   **Text Regular**: `#616161` (标签、辅助说明)
*   **Text Placeholder**: `#9E9E9E`
*   **Border**: `#E0E0E0`
*   **Background (Body)**: `#F5F7FA` (浅灰背景，突显白色卡片)

---

## 3. 排版与字体 (Typography)

强调数字的可读性与表格的整洁度。

*   **Font Family**:
    *   优先：`"Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif`
    *   **数字/代码专用**: `"Roboto Mono", Consolas, monospace` (用于 P值、置信区间、代码片段)

*   **字号规范**:
    *   **H1 (页面标题)**: 24px / Bold / #212121
    *   **H2 (卡片标题)**: 18px / Medium / #212121
    *   **H3 (分析结果摘要)**: 16px / Bold / Science Blue
    *   **Body (正文/表格)**: 14px / Regular / #212121
    *   **Small (辅助文字/Tooltip)**: 12px / Regular / #616161

---

## 4. 核心组件规范 (Component Guidelines)

### A. 布局容器 (Cards & Layout)
所有的功能模块都应包裹在卡片中，形成清晰的视觉区块。

*   **Card Style**:
    *   `border-radius: 8px`
    *   `box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05)` (极简阴影)
    *   `border: 1px solid #EBEEF5`
*   **Header**:
    *   左侧：标题 + (可选) 状态徽章。
    *   右侧：主要操作区（如“导出 Excel”、“运行模型”）。

### B. 表格 (Tables) - 核心交互
科研数据的展示形式是重中之重。

1.  **数据预览模式 (Data View)**:
    *   用于“数据管理”、“清洗”页面。
    *   样式：`stripe` (斑马纹), `border` (全边框), `size="small"`。
    *   交互：表头固定，支持列宽拖拽。

2.  **学术发表模式 (Publication View)**:
    *   用于“Table 1”、“模型结果”页面。
    *   样式：模拟**三线表 (Three-line Table)**。
        *   顶底边框加粗 (2px black)。
        *   表头下边框 (1px black)。
        *   去除竖线边框。
        *   去除斑马纹背景。
    *   **显著性高亮**：
        *   当 `P < 0.05` 时，文字加粗并标红 (`#D32F2F`)。
        *   置信区间 `(95% CI)` 如果跨越 1 (如 0.8-1.2)，显示为灰色（无意义）；如果不跨越 1，显示为黑色（有意义）。

### C. 数据录入表单 (Forms)
减少用户焦虑。

*   **Label**: 统一使用 `label-position="top"`，确保长变量名也能完整显示。
*   **Select**:
    *   必须支持 `filterable` (可搜索)，因为变量名可能很多。
    *   对于多选框（如选择协变量），使用 Tag 模式展示已选项。
*   **Helper Text**:
    *   每个复杂表单项下方必须有灰色的解释性文字。
    *   *例如：“处理变量 (Treatment)”下方注明：“请选择区分实验组和对照组的变量（通常为0/1）”。*

### D. 反馈与引导 (Feedback & Guide)

*   **Loading**:
    *   短时间 (<1s)：按钮 loading。
    *   长时间 (>1s)：**骨架屏 (Skeleton)** 或 **进度条**，并配有文字（“正在进行倾向性评分匹配...”）。
*   **Empty State**:
    *   绝不展示空白。
    *   内容：插画 + 解释文字 + **行动按钮**（如：“暂无模型结果，[去配置参数]”）。

---

## 5. 数据可视化规范 (Data Viz)

使用 Plotly.js，但需统一配置以符合医学审美。

*   **配色板**:
    *   **分组对比**: [`#3B71CA` (组A), `#E6A23C` (组B), `#67C23A` (组C)]
    *   **生存曲线**: 必须清晰区分不同线条，且线条稍粗 (width: 2.5)。
*   **图表元素**:
    *   **坐标轴**: 必须有明确的 Label 和 Unit。
    *   **置信区间**: 使用半透明填充 (Opacity 0.2)。
    *   **参考线**: 必须标注参考线（如 OR=1, P=0.05, AUC=0.5），使用虚线灰色。
*   **导出**:
    *   提供按钮：`下载高清 PNG (300 DPI)` 和 `下载 SVG (矢量)`。

---

## 6. 文案与微交互 (Micro-copy & Terminology)

建立“中英对照”与“人话翻译”标准。

| 开发者术语 (Dev) | 界面显示 (UI) | 解释/提示 (Tooltip) |
| :--- | :--- | :--- |
| **Project** | **科研项目** | |
| **Dataset** | **数据集** | 上传的 Excel 或 CSV 文件 |
| **Feature** | **变量 (Variables)** | 您采集的患者指标 |
| **Target / Label** | **结局变量 (Outcome)** | 您主要研究的结果（如死亡、发病）|
| **Imputation** | **缺失值填补** | 自动补全空缺的数据 |
| **Encoding** | **数值化处理** | 将文字（男/女）转换为数字（0/1） |
| **Correlation** | **相关性分析** | 查看变量之间是否相互关联 |
| **Coefficient** | **效应值 (Coef)** | 正数代表促进，负数代表抑制 |
| **Hazard Ratio (HR)** | **风险比 (HR)** | HR > 1 代表风险增加 |
| **Epochs** | **迭代轮次** | 越大越准，但速度越慢 |

---

## 7. 图标系统 (Iconography)

使用 Element Plus Icons，赋予特定语义：

*   📂 `Folder` / `Document`: 项目与数据。
*   🪄 `MagicStick`: 自动清洗、智能推荐。
*   🏥 `FirstAidKit` (或 `Box`): 数据体检/修复。
*   📈 `TrendCharts`: 统计建模。
*   ⚖️ `ScaleToOriginal` (或 `Connection`): 倾向性匹配 (PSM)。
*   ⏳ `Timer`: 生存分析。
*   📥 `Download`: 导出报告/图片。

---

## 8. 开发实现建议 (Implementation Notes)

为了在 Vue 3 + Element Plus 中快速落地此规范，建议封装以下基础组件：

1.  **`InsightCard.vue`**: 统一封装 Header, Body, Footer 样式。
2.  **`InsightTable.vue`**: 封装 `el-table`，通过 prop `mode="publication"` 自动切换为三线表样式。
3.  **`HelpIcon.vue`**: 封装 `el-tooltip` + `QuestionFilled` 图标，统一问号的大小、颜色和提示文字的排版。
4.  **`StatTag.vue`**: 根据传入的 P 值自动渲染红色/绿色/灰色的 Tag。