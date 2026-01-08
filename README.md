# Insight Platform (Insight 平台)

**简单、可解释的医学科研数据建模平台**

Insight 是一个专为医学生和科研人员设计的低门槛统计建模工具。它允许用户通过直观的 Web 界面上传数据、配置模型参数，并获取符合论文发表要求的统计结果（包括三线表导出）。平台核心关注统计方法的正确性与结果的可解释性。

---

## 🌟 核心功能 (Features)

*   **项目化管理**: 支持多项目并行管理，数据与模型配置隔离。
*   **低代码建模**: 无需编写 Python/R 代码，通过交互式表单完成建模。
*   **多格式支持**: 支持上传 `.csv`, `.xlsx`, `.xls` 文件，自动识别编码 (UTF-8, GBK, Latin1)。
*   **核心统计模型**:
    *   **Linear Regression**: 线性回归分析。
    *   **Logistic Regression**: 逻辑回归 (输出 OR 值及 95% CI)。
    *   **Cox Proportional Hazards**: 生存分析 (输出 HR 值及 95% CI)。
*   **论文级导出**: 支持将模型结果直接导出为 Excel 文件，包含 P 值、系数、置信区间等关键指标。
*   **交互式可视化**: (Post-MVP) 集成 Plotly 图表展示。

## 🛠 技术栈 (Tech Stack)

### Backend (后端)
*   **Core**: Python 3.9+, Flask
*   **Database**: SQLite (SQLAlchemy ORM)
*   **Data Science**: Pandas, NumPy, Statsmodels, Lifelines
*   **Authentication**: JWT (JSON Web Tokens)

### Frontend (前端)
*   **Framework**: Vue 3 + Vite
*   **UI Library**: Element Plus (Admin Layout)
*   **State Management**: Pinia
*   **HTTP Client**: Axios

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
确保本地已安装：
*   Python 3.9+
*   Node.js 16+
*   Git

### 2. 后端启动
```bash
# 1. 克隆项目
git clone https://github.com/your-repo/insight.git
cd insight

# 2. 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
flask db upgrade

# 5. 启动服务 (默认端口 5000)
export FLASK_APP=backend/run.py
flask run
```

### 3. 前端启动 (开发模式)
```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
```

> **注意**: 生产环境下，运行 `npm run build` 构建前端资源后，Flask 会自动托管 `frontend/dist` 目录下的静态文件，无需独立运行前端服务。

---

## 📂 目录结构

```text
insight/
├── backend/                # 后端代码
│   ├── app/
│   │   ├── api/            # REST API 接口
│   │   ├── services/       # 核心统计逻辑 (DataService, ModelingService)
│   │   └── models/         # 数据库模型 (User, Project)
│   ├── run.py              # 启动入口
│   └── config.py           # 配置文件
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── layout/         # 通用布局 (Sidebar + Header)
│   │   ├── views/          # 页面组件 (Dashboard, ModelingTab)
│   │   └── stores/         # 状态管理
│   └── vite.config.js
└── requirements.txt        # Python 依赖
```

---

## 📝 使用指南

1.  **注册/登录**: 创建新账号并登录系统。
2.  **创建项目**: 在仪表盘点击 "新建项目"。
3.  **上传数据**: 进入项目 -> "数据管理" -> 上传 CSV/Excel 文件。
4.  **运行模型**:
    *   切换到 "统计建模" 标签页。
    *   选择模型类型 (如 Logistic 回归)。
    *   指定 **目标变量** (Y) 和 **特征变量** (X)。
    *   点击 "运行模型"。
5.  **导出结果**: 在结果面板点击 "导出 Excel" 下载分析报告。

---

## 🛡️ License

MIT License. Copyright (c) 2026 Insight Platform.
