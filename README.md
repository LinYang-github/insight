# Insight Platform (Insight 平台)

**让医学科研统计不再是“黑盒”**

Insight 是一个专为临床医生和医学生设计的**透明化 (White-box)** 科研数据分析平台。我们不仅仅提供 P 值，更提供直观的**自然语言解读**和**决策依据**，帮助非统计学背景的用户理解数据背后的故事。

---

## 🌟 核心亮点 (Highlights)

### 1. 拒绝“黑盒”统计 (De-blackboxing)
- **智能决策透明化**: 系统不仅告诉你 P 值，还会告诉你**“为什么选这个检验方法”**。
  - *例如*: "选择了 Welch's T-test，因为 Levene 检验显示方差不齐 (P<0.05)。"
- **自然语言结果解读**: 自动将晦涩的统计学术语翻译为临床语言。
  - *例如*: <font color="green">"差异显著 (P=0.032): 实验组的恢复速度显著快于对照组。"</font>
- **方法学一键复制**: 自动生成符合期刊要求的方法学描述 (Methodology)，支持一键复制。

### 2. 预测模型全生命周期 (Modeling Lifecycle)
- **高级评价指标**: 支持 time-dependent AUC, NRI (净重新分类指数), IDI (综合判别改善指数)。
- **多模型对比**: 直观对比 Logistic / Cox / XGBoost 等不同模型的预测效能。
- **临床决策支持**: 自动生成**列线图 (Nomogram)** 及其配套的 **Web 风险计算器**。

---

## 🛠 功能模块 (Modules)

| 模块 | 功能描述 | 核心特性 |
| :--- | :--- | :--- |
| **Data Readiness** | 数据准备与清洗 | 缺失值插补、变量生成 (eGFR等)、CKD 分期自动标记 |
| **EDA** | 探索性分析 | 交互式分布图、相关性矩阵、基础描述统计 |
| **Table 1** | 基线特征表 | 自动假设检验 (Auto-Testing)、三线表导出、显著性高亮 |
| **Advanced Modeling** | 高级建模 | 限制性立方样条 (RCS)、分层亚组分析、竞争风险模型 (CIF) |
| **Longitudinal** | 纵向/长轴分析 | 线性混合模型 (LMM)、轨迹聚类 (Trajectory)、变异度指标 (ARV/CV) |
| **Validation** | 模型验证与对比 | DCA 曲线、校准曲线 (Calibration)、模型间增量价值评估 (NRI/IDI) |

---

## 💻 技术栈 (Tech Stack)

### Backend (Python / Flask)
- **Framework**: Flask (RESTful API)
- **Engine**: 
  - `DuckDB`: 高性能大文件数据读取
  - `Pandas / NumPy`: 数据处理与矩阵运算
- **Analysis**: 
  - `SciPy / Statsmodels`: 传统统计推断
  - `Lifelines`: 核心生存分析引擎
  - `XGBoost / SHAP`: 机器学习建模与可解释性
- **Reports**: `ReportLab` (自动化 PDF 报告生成)

### Frontend (Vue 3 / Vite)
- **Core**: Vue 3 (Composition API)
- **UI Library**: Element Plus
- **Viz**: Plotly.js (高性能交互式科研绘图)
- **State**: Pinia

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
- Python 3.9+ (建议使用虚拟环境)
- Node.js 18+

### 2. 后端启动
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
flask db upgrade

# 启动服务 (默认端口 5000)
python run.py
```

### 3. 前端启动
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

---

## 📂 目录结构
```text
insight/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── statistics_service.py # 统计检验核心 (含 Auto-Test 逻辑)
│   │   │   ├── advanced_modeling_service.py # RCS, CIF, Nomogram 逻辑
│   │   │   ├── longitudinal_service.py # 混合模型与聚类
│   │   │   └── validation_service.py # NRI, IDI, AUC 计算器
│   │   └── api/            # API 路由分发
│   └── tests/              # 统计逻辑单元测试
├── frontend/
│   ├── src/views/project/components/
│   │   ├── TableOneTab.vue     # 基线表
│   │   ├── AdvancedModelingTab.vue # RCS / 亚组 / Nomogram
│   │   ├── LongitudinalTab.vue    # 长轴分析
│   │   ├── ModelComparisonTab.vue # 模型对比
│   │   └── InsightChart.vue    # 封装的 Plotly 绘图组件
```

---

## 📝 开发规范
- **语言规范**: 后端核心统计逻辑需包含中英文双语注释 (详见 `docs/code-comments.md`)。
- **设计标准**: 遵循 Insight Design System (IDS) 规范，确保 UI 符合医学期刊审美。

---

## 🛡️ License
MIT License. Copyright (c) 2026 Insight Platform.
