/**
 * 模型评估指标的 Tooltip 说明
 */
export const METRIC_TOOLTIPS = {
    'accuracy': '准确率：模型预测正确的样本占总样本的比例。',
    'auc': 'ROC曲线下面积：衡量二分类模型好坏，越接近1越好。0.5代表随机猜测。',
    'recall': '召回率：所有正例中被正确预测为正例的比例。',
    'f1': 'F1分数：精确率和召回率的调和平均数，综合衡量指标。',
    'r2': 'R平方：决定系数，表示模型解释了因变量方差的百分比。越接近1拟合越好。',
    'rmse': '均方根误差：预测值与真实值偏差的样本标准差。越小越好。',
    'cv_auc_mean': '5折交叉验证平均AUC：模型在未见数据上的平均表现，评估泛化能力。',
    'cv_auc_std': '5折交叉验证AUC标准差：评估模型表现的稳定性，值越小越稳定。',
    'aic': '赤池信息量：衡量模型拟合优度与参数复杂度的平衡，越小代表模型越精简有效。',
    'bic': '贝叶斯信息量：类似 AIC，但对参数数量惩罚更重，常用于模型筛选，越小越好。',
    'c_index': '一致性指数：生存分析核心指标，衡量模型预测风险等级的准确性，越接近 1 越好。',
    'log_likelihood': '对数似然 (Log-Likelihood)：越高越好，表示模型对数据的解释程度。',
    'n_events': '事件数 (Events)：分析中观察到的终点事件总数。',
    'ph_global_p': '全局等比例风险检验 P 值：用于评估整个模型是否满足 Cox 模型的比例风险假定。P < 0.05 提示违反假定。'
}

/**
 * 支持的模型类型选项
 */
export const MODEL_OPTIONS = [
    { label: '线性回归 (Linear Regression, OLS)', value: 'linear' },
    { label: '逻辑回归 (Logistic Regression)', value: 'logistic' },
    { label: 'Cox 比例风险回归 (Cox Proportional Hazards)', value: 'cox' },
    { label: '随机森林 (Random Forest)', value: 'random_forest' },
    { label: 'XGBoost', value: 'xgboost' }
]
