---
trigger: always_on
---

# Insight 平台代码注释规范 (v1.0)

## 1. 核心原则 (Core Principles)

1.  **Why > How**：注释应重点解释**“为什么要这么写”**（业务背景、统计学原理），而不仅仅是翻译代码逻辑。
2.  **医学与代码的映射**：涉及统计学术语（如 KM曲线、Cox回归、OR值）时，必须在注释中体现医学含义，便于非统计背景的开发者理解。
3.  **即时更新**：代码修改时，注释必须同步更新。错误的注释比没有注释更可怕。
4.  **语言规范**：
    *   **简单逻辑**：英文 (English)。
    *   **复杂业务/统计原理**：推荐使用**中文 (Chinese)**，确保团队成员对数学逻辑理解无歧义。

---

## 2. 后端规范 (Backend - Python)

后端涉及大量的数据清洗 (`Pandas`) 和建模 (`Statsmodels`/`Lifelines`)，注释需侧重于**数据流转**和**算法假设**。

### 2.1 模块与文件注释 (Module Docstring)
每个 `.py` 文件的顶部必须包含文件用途说明。

```python
"""
app.services.modeling_service.py

负责核心统计模型的调度与执行。
包含数据完整性校验、策略模式的模型分发以及结果的标准化格式化。
"""
```

### 2.2 函数/方法注释 (Function/Method Docstring)
采用 **Google Style** 或 **NumPy Style** 文档字符串。
**强制要求**：
*   **Args**: 参数及其期望的数据类型/结构（尤其是 DataFrame 需要包含哪些列）。
*   **Returns**: 返回值的结构（特别是复杂的字典结构）。
*   **Raises**: 可能抛出的统计学错误（如矩阵奇异、完美共线性）。

**示例 (参考 `modeling/linear.py`):**

```python
def fit(self, df: pd.DataFrame, target: str, features: list, params: dict) -> dict:
    """
    拟合线性回归模型 (OLS)。

    Args:
        df (pd.DataFrame): 训练数据，必须已完成缺失值处理。
        target (str): 因变量列名 (Y)。
        features (list): 自变量列名列表 (X)。
        params (dict): 模型超参数（如正则化项，本模型暂未使用）。

    Returns:
        dict: 标准化的结果字典，包含 'summary' (系数表) 和 'metrics' (R2, AIC)。

    Raises:
        ValueError: 当数据存在完全多重共线性导致矩阵不可逆时抛出。
    """
    # ... code ...
```

### 2.3 统计逻辑注释 (Statistical Logic)
在涉及数学运算、特定的统计检验选择时，必须注明原因。

**示例 (参考 `statistics_service.py`):**

```python
# 假设检验选择逻辑：
# 如果只有两组，使用 Welch's T-test (不假设方差相等)，比标准 T-test 更稳健。
# 如果超过两组，使用 ANOVA 单因素方差分析。
if len(groups) == 2:
    stat, p = stats.ttest_ind(group_data[0], group_data[1], equal_var=False)
else:
    stat, p = stats.f_oneway(*group_data)
```

### 2.4 数据处理注释
对于 Pandas 的链式操作或复杂的 Mask 逻辑，需解释意图。

```python
# 过滤逻辑：
# 1. 剔除目标变量为空的行（无法训练）
# 2. 仅保留数值型列用于计算相关性矩阵
df_clean = df.dropna(subset=[target])
numeric_df = df_clean.select_dtypes(include=[np.number])
```

---

## 3. 前端规范 (Frontend - Vue 3)

前端主要负责交互和数据可视化 (`Plotly`)，注释需侧重于**组件职责**、**数据流向**和**视图逻辑**。

### 3.1 组件注释 (Component Annotation)
在 `<script setup>` 顶部简述组件功能。

**示例 (参考 `views/project/ProjectWorkspace.vue`):**

```javascript
<script setup>
/**
 * ProjectWorkspace.vue
 * 项目工作台主布局。
 * 
 * 职责：
 * 1. 管理左侧导航栏（数据 -> 清洗 -> 统计 -> 建模）。
 * 2. 维护当前选中的 Dataset 上下文。
 * 3. 处理子组件触发的 Dataset 更新事件。
 */
import { ref, onMounted } from 'vue'
// ...
```

### 3.2 复杂交互逻辑
对于复杂的函数，特别是涉及 Plotly 图表配置或数据转换的，需要详细注释。

**示例 (参考 `components/SurvivalTab.vue`):**

```javascript
/**
 * 将后端返回的 KM 数据转换为 Plotly 格式。
 * 
 * @param {Array} plotData - 后端返回的分组数据 [{name: 'GroupA', times: [], probs: []}, ...]
 * @description
 * KM 曲线是阶梯状 (Step Function)，因此 line.shape 必须设为 'hv' (Horizontal-Vertical)。
 */
const renderPlot = (plotData) => {
    const traces = []
    plotData.forEach(g => {
        traces.push({
            x: g.times,
            y: g.probs,
            mode: 'lines',
            name: g.name,
            line: { shape: 'hv' }, // 关键配置：阶梯线
            type: 'scatter'
        })
    })
    // ...
}
```

### 3.3 模板区块注释 (Template Blocks)
在 `template` 中，使用 HTML 注释标记主要的 UI 区域，特别是布局复杂的页面。

```html
<template>
  <div class="survival-container">
    <el-row :gutter="20">
        <!-- ============================== -->
        <!-- 左侧：参数配置面板 (Config Panel) -->
        <!-- ============================== -->
        <el-col :span="6">
            <el-card>...</el-card>
        </el-col>

        <!-- ============================== -->
        <!-- 右侧：结果展示面板 (Plot Panel)  -->
        <!-- ============================== -->
        <el-col :span="18">
            <el-card>...</el-card>
        </el-col>
    </el-row>
  </div>
</template>
```

---

## 4. 特殊标记 (Tags)

为了方便追踪技术债务和待办事项，请统一使用以下标记：

*   `TODO(User)`: 待实现的功能。
    *   `# TODO(Dev1): 添加 Cox 回归的分层分析支持`
*   `FIXME(User)`: 代码存在隐患，需要修复，但暂不影响主流程。
    *   `# FIXME(Dev2): 当前 CSV 解析未处理 GBK 编码，需增强鲁棒性`
*   `NOTE`: 重要的提示或反直觉的逻辑。
    *   `# NOTE: Plotly 导出图片时，SVG 格式不支持自定义字体`
*   `HACK`: 权宜之计的代码，未来应重构。

---

## 5. 术语对照表 (Terminology)

在注释中涉及以下概念时，请保持术语一致性，避免歧义：

| 开发者术语 (Variable/Code) | 注释标准用语 (Comment) |
| :--- | :--- |
| `target` / `y` | 结局变量 / 因变量 |
| `features` / `covariates` / `X` | 特征变量 / 协变量 / 混杂因素 |
| `impute` | 缺失值填补 (非“填充”) |
| `encode` | 数值化 / 因子化 / 独热编码 |
| `censored` | 删失 (Survival Analysis 特有) |
| `event` | 终点事件 |
| `coef` | 回归系数 |
| `intercept` | 截距 |
| `singular matrix` | 奇异矩阵 (通常指多重共线性) |

---

## 6. 示例：一份完美的 Pull Request 代码片段

**File: `backend/app/services/preprocessing_service.py`**

```python
def impute_data(df, strategies):
    """
    根据指定策略处理 DataFrame 中的缺失值。
    
    Args:
        df (pd.DataFrame): 原始数据集。
        strategies (dict): 策略字典，格式 { "col_name": "mean"|"median"|"mode"|"drop" }。
    
    Returns:
        pd.DataFrame: 处理后的新 DataFrame。
    """
    # 使用 copy 避免修改原始内存数据
    df = df.copy()

    for col, method in strategies.items():
        if col not in df.columns:
            continue
            
        # NOTE: drop 会删除整行，可能导致样本量急剧减少，需前端给予用户警告
        if method == 'drop':
            df = df.dropna(subset=[col])
            
        elif method == 'mean':
            if pd.api.types.is_numeric_dtype(df[col]):
                val = df[col].mean()
                df[col] = df[col].fillna(val)
            else:
                # 容错：非数值列无法计算均值，回退到众数或跳过
                pass 
                
        # ... 其他策略
                    
    return df
```