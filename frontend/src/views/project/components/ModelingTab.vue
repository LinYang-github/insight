<template>
  <div v-if="!datasetId">
      <el-empty description="请先上传数据" />
  </div>
  <div v-else>
    <el-row :gutter="20">
       <el-col :span="10">
           <el-card shadow="hover">
               <template #header>
                   <span>模型配置</span>
               </template>
               <el-form label-position="top">
                   <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                       <span style="font-size: 14px; color: #606266; font-weight: 500;">变量配置 (Configuration)</span>
                       <el-tooltip content="智能推荐变量角色 (Auto-Suggest Roles)" placement="top">
                           <el-button type="primary" link @click="autoSuggestRoles" :icon="MagicStick">自动推荐</el-button>
                       </el-tooltip>
                   </div>
                   <el-form-item label="模型类型">
                       <el-select v-model="config.model_type" placeholder="选择模型" style="width: 100%">
                           <el-option v-for="opt in modelOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                       </el-select>
                   </el-form-item>
                   
                   <el-form-item label="目标变量 / 结局 (Target / Outcome)">
                       <template #label>
                            <span>目标变量 / 结局 (Target / Outcome)</span>
                            <el-tooltip content="您希望预测或研究的主要结果，例如“是否患病”、“生存时间”等。" placement="top">
                                <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                            </el-tooltip>
                       </template>
                       <template v-if="config.model_type !== 'cox'">
                           <el-select v-model="config.target" placeholder="选择目标变量" filterable style="width: 100%">
                               <el-option v-for="opt in targetOptions" :key="opt.value" :label="opt.label" :value="opt.value" :disabled="opt.disabled">
                                    <span v-if="opt.disabled" style="color: #ccc">{{ opt.label }} (Non-numeric)</span>
                                    <span v-else>{{ opt.label }}</span>
                               </el-option>
                           </el-select>
                       </template>
                       <template v-else>
                           <el-row :gutter="10">
                               <el-col :span="12">
                                   <el-select v-model="config.target.time" placeholder="时间变量 (Time)" filterable>
                                       <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                                   </el-select>
                               </el-col>
                               <el-col :span="12">
                                   <el-select v-model="config.target.event" placeholder="事件变量 (Event)" filterable>
                                       <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                                   </el-select>
                               </el-col>
                           </el-row>
                       </template>
                   </el-form-item>
                   
                   <el-form-item label="特征变量 (Covariates)">
                        <template #label>
                            <span>特征变量 (Covariates)</span>
                            <el-tooltip content="可能会影响结局的变量，包括您主要关心的变量和需要校正的混杂因素。" placement="top">
                                <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                            </el-tooltip>
                       </template>
                       <el-select v-model="config.features" multiple placeholder="选择特征变量" filterable style="width: 100%">
                           <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value">
                               <div style="display: flex; justify-content: space-between; align-items: center;">
                                   <span>{{ opt.label }}</span>
                                   <el-tooltip v-if="opt.status !== 'unknown'" :content="opt.msg" placement="right">
                                       <span :style="{
                                           display: 'inline-block',
                                           width: '8px',
                                           height: '8px',
                                           borderRadius: '50%',
                                           backgroundColor: opt.status === 'healthy' ? '#67C23A' : '#E6A23C',
                                           marginLeft: '8px'
                                       }"></span>
                                   </el-tooltip>
                               </div>
                           </el-option>
                       </el-select>
                       
                       <!-- VIF Alert -->
                        <el-alert
                            v-if="collinearityWarning"
                            :title="collinearityWarning"
                            type="warning"
                            show-icon
                            style="margin-top: 10px"
                            :closable="false"
                        />
                   </el-form-item>
                   
                   <!-- Reference Levels (Advanced) -->
                   <el-collapse v-if="selectedCategoricalVars.length > 0" style="margin-bottom: 20px; border: 1px solid #EBEEF5;">
                        <el-collapse-item title="基准组设置 (Reference Levels)" name="1">
                            <template #title>
                                <el-icon style="margin-right: 5px"><Setting /></el-icon> 基准组设置 (Reference Levels)
                            </template>
                            <div style="padding: 10px;">
                                <div v-for="v in selectedCategoricalVars" :key="v.name" style="margin-bottom: 10px;">
                                    <span style="font-size: 12px; color: #606266; display: block; margin-bottom: 4px;">{{ v.name }} Reference:</span>
                                    <el-select v-model="config.ref_levels[v.name]" placeholder="Default (First)" size="small" style="width: 100%">
                                        <el-option v-for="cat in v.categories" :key="cat" :label="cat" :value="cat" />
                                    </el-select>
                                </div>
                                <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                                    * 设置为基准的类别将在回归结果中作为对比参照（Intercept）。
                                </div>
                            </div>
                        </el-collapse-item>
                   </el-collapse>

                   <!-- Model Hyperparameters -->
                   <div v-if="['random_forest', 'xgboost'].includes(config.model_type)" style="background: #f5f7fa; padding: 10px; border-radius: 4px; margin-bottom: 18px;">
                        <span style="font-size: 12px; font-weight: bold; color: #606266; display: block; margin-bottom: 10px;">高级参数 (Advanced Params)</span>
                        <el-row :gutter="10">
                            <el-col :span="12">
                                <el-form-item label="树数量 (Trees)">
                                    <el-input-number v-model="config.model_params.n_estimators" :min="10" :max="1000" :step="10" size="small" style="width: 100%"/>
                                </el-form-item>
                            </el-col>
                            <el-col :span="12">
                                <el-form-item label="最大深度 (Depth)">
                                     <el-input-number v-model="config.model_params.max_depth" :min="1" :max="50" size="small" placeholder="Unlimited" style="width: 100%"/>
                                </el-form-item>
                            </el-col>
                             <el-col :span="12" v-if="config.model_type === 'xgboost'">
                                <el-form-item label="学习率 (Rate)">
                                     <el-input-number v-model="config.model_params.learning_rate" :min="0.001" :max="1.0" :step="0.01" size="small" style="width: 100%"/>
                                </el-form-item>
                            </el-col>
                        </el-row>
                   </div>
                   
                   <el-button type="primary" style="width: 100%" @click="runModel" :loading="loading">运行模型</el-button>
               </el-form>
           </el-card>
       </el-col>
       
       <el-col :span="14">
           <el-card shadow="hover" v-if="results">
                <template #header>
                    <div class="result-header">
                        <span>运行结果</span>
                        <div>
                             <el-button type="info" plain size="small" @click="copyMethodology" :icon="CopyDocument">复制方法学</el-button>
                             <el-button type="success" size="small" @click="exportResults">导出 Excel</el-button>
                        </div>
                    </div>
                </template>

                 <!-- Smart Interpretation Component -->
                 <InterpretationPanel
                    v-if="topResult"
                    :p-value="topResult.p_value"
                    :test-name="config.model_type.toUpperCase() + ' Model'"
                    :selection-reason="smartSummary"
                    :effect-size="topResult.effectSize"
                    :direction="topResult.desc"
                 />
                 
                 <!-- Fallback or Additional Diagnostics -->
                 <el-alert
                    v-if="smartSummary && !topResult"
                    title="模型诊断"
                    type="info"
                    show-icon
                    :closable="false"
                    style="margin-bottom: 20px"
                 >
                    <template #default>
                        <div style="white-space: pre-wrap; line-height: 1.6;">{{ smartSummary }}</div>
                    </template>
                 </el-alert>

                <!-- Metrics -->
                <el-descriptions title="模型指标" :column="2" border size="small" style="margin-bottom: 20px">
                    <el-descriptions-item v-for="(val, key) in results.metrics" :key="key">
                        <template #label>
                            <div style="display: flex; align-items: center;">
                                <span>{{ key }}</span>
                                <el-tooltip v-if="metricTooltips[key]" :content="metricTooltips[key]" placement="top">
                                    <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </div>
                        </template>
                        {{ typeof val === 'number' ? val.toFixed(4) : val }}
                    </el-descriptions-item>
                </el-descriptions>

                <!-- Result Tabs -->
                <el-tabs type="border-card">
                    <el-tab-pane label="模型详情 (Details)">
                        <!-- ML Results (Importance) -->
                        <div v-if="results.importance">
                             <h3>特征重要性 (Feature Importance - SHAP)</h3>
                             <el-table :data="results.importance" style="width: 100%" height="400" stripe border size="small">
                                <el-table-column prop="feature" label="变量名" />
                                <el-table-column prop="importance" label="重要性 (SHAP mean)">
                                    <template #default="scope">
                                        <el-progress :percentage="Math.min(scope.row.importance * 100 / maxImportance, 100)" :show-text="false" />
                                        {{ scope.row.importance.toFixed(5) }}
                                    </template>
                                </el-table-column>
                             </el-table>
                        </div>

                        <!-- Statistical Summary Table -->
                        <el-table v-else :data="results.summary" style="width: 100%" height="400" stripe border size="small">
                            <el-table-column prop="variable" label="变量" />
                            <el-table-column prop="coef" label="系数 (Coef)">
                                <template #header>
                                     <span>系数 (Coef)</span>
                                     <el-tooltip content="正值代表正相关（风险增加），负值代表负相关（风险降低）" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">{{ scope.row.coef.toFixed(4) }}</template>
                            </el-table-column>
                            <el-table-column prop="p_value" label="P值">
                                <template #header>
                                     <span>P值</span>
                                     <el-tooltip content="P < 0.05 通常认为具有统计学显著意义" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    <span :style="{ fontWeight: scope.row.p_value < 0.05 ? 'bold' : 'normal', color: scope.row.p_value < 0.05 ? 'red' : 'inherit' }">
                                        {{ scope.row.p_value < 0.001 ? '<0.001' : typeof scope.row.p_value === 'number' ? scope.row.p_value.toFixed(4) : scope.row.p_value }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column v-if="config.model_type === 'logistic'" label="OR (95% CI)">
                                <template #header>
                                     <span>OR (95% CI)</span>
                                     <el-tooltip content="优势比 (Odds Ratio)。OR > 1 代表风险增加，CI 不包含 1 代表显著。" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    {{ scope.row.or.toFixed(2) }} ({{ scope.row.or_ci_lower.toFixed(2) }}-{{ scope.row.or_ci_upper.toFixed(2) }})
                                </template>
                            </el-table-column>
                            <el-table-column v-if="config.model_type === 'cox'" label="HR (95% CI)">
                                <template #header>
                                     <span>HR (95% CI)</span>
                                     <el-tooltip content="风险比 (Hazard Ratio)。HR > 1 代表风险增加，CI 不包含 1 代表显著。" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    {{ scope.row.hr.toFixed(2) }} ({{ scope.row.hr_ci_lower.toFixed(2) }}-{{ scope.row.hr_ci_upper.toFixed(2) }})
                                </template>
                            </el-table-column>
                            
                             <!-- Diagnostics -->
                            <el-table-column v-if="['linear', 'logistic'].includes(config.model_type)" prop="vif" label="VIF" width="80">
                                <template #header>
                                     <span>VIF</span>
                                     <el-tooltip content="方差膨胀因子。VIF > 5 提示可能存在多重共线性。" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                            </el-table-column>

                             <el-table-column v-if="config.model_type === 'cox'" prop="ph_test_p" label="PH Test P" width="100">
                                <template #header>
                                     <span>PH Test P</span>
                                     <el-tooltip content="PH 假设检验 P 值。P < 0.05 提示违反比例风险假设" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    <span :style="{ fontWeight: scope.row.ph_test_p < 0.05 ? 'bold' : 'normal', color: scope.row.ph_test_p < 0.05 ? 'red' : 'inherit' }">
                                         {{ scope.row.ph_test_p }}
                                    </span>
                                </template>
                             </el-table-column>
                        </el-table>
                    </el-tab-pane>

                    <el-tab-pane label="评估图表 (Evaluation Plots)" v-if="results.plots">
                        <el-row :gutter="20">
                            <!-- ROC -->
                            <el-col :span="12" v-if="results.plots.roc" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="roc-plot"
                                    title="ROC Curve"
                                    :data="chartData.roc.data"
                                    :layout="chartData.roc.layout"
                                />
                            </el-col>
                            
                            <!-- Calibration -->
                            <el-col :span="12" v-if="results.plots.calibration" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="calibration-plot"
                                    title="Calibration Plot"
                                    :data="chartData.calibration.data"
                                    :layout="chartData.calibration.layout"
                                />
                            </el-col>
                            
                            <!-- DCA -->
                             <el-col :span="12" v-if="results.plots.dca" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="dca-plot"
                                    title="Decision Curve (DCA)"
                                    :data="chartData.dca.data"
                                    :layout="chartData.dca.layout"
                                />
                            </el-col>
                        </el-row>
                    </el-tab-pane>

                    <el-tab-pane label="假设检验 (Assumptions)">
                         <!-- Multicollinearity (Linear/Logistic) -->
                         <div v-if="['linear', 'logistic'].includes(config.model_type)">
                            <h3>多重共线性 (Multicollinearity) - VIF</h3>
                            <p style="font-size: 13px; color: #666; margin-bottom: 15px;">
                                <strong>标准:</strong> VIF < 5 为理想，VIF > 10 提示严重共线性。
                            </p>
                            <InsightChart
                                chartId="vif-plot"
                                title="Multicollinearity (VIF)"
                                :data="chartData.vif.data"
                                :layout="chartData.vif.layout"
                            />
                         </div>
                         
                         <!-- PH Assumption (Cox) -->
                         <div v-if="config.model_type === 'cox'">
                             <h3>PH 等比例风险假设 (Proportional Hazards Assumption)</h3>
                             <p style="font-size: 13px; color: #666; margin-bottom: 15px;">
                                <strong>标准:</strong> P > 0.05 代表满足假设 (好)。P < 0.05 代表违反假设 (需注意)。
                            </p>
                            <el-table :data="results.summary" style="width: 100%" stripe border size="small">
                                <el-table-column prop="variable" label="变量" />
                                <el-table-column prop="ph_test_p" label="PH Test P-value">
                                    <template #default="scope">
                                        <el-tag :type="scope.row.ph_test_p >= 0.05 ? 'success' : 'danger'">
                                            {{ scope.row.ph_test_p }}
                                        </el-tag>
                                    </template>
                                </el-table-column>
                                <el-table-column label="结论">
                                    <template #default="scope">
                                        <span v-if="scope.row.ph_test_p >= 0.05" style="color: #67C23A">• 满足假设</span>
                                        <span v-else style="color: #F56C6C">• 违反假设 (可能随时变)</span>
                                    </template>
                                </el-table-column>
                            </el-table>
                         </div>
                    </el-tab-pane>
                </el-tabs>
           </el-card>
       </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * ModelingTab.vue
 * 核心建模与评估主组件。
 * 
 * 职责：
 * 1. 提供多种统计/机器学习模型的配置界面（线性、逻辑、Cox、随机森林、XGBoost）。
 * 2. 调度后端建模服务并展示详细的模型参数（Coef, P-value, OR, HR）。
 * 3. 实现“智能解读”逻辑，将数值指标转化为医学研究可理解的文字结论。
 * 4. 渲染并集成 Plotly 图表进行模型评估（ROC, 校准曲线, DCA等）。
 */
import { ref, computed, watch, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'
import InterpretationPanel from './InterpretationPanel.vue'

import MethodologyGenerator from '../utils/MethodologyGenerator.js'
import InsightChart from './InsightChart.vue'

import { QuestionFilled, ArrowDown, Setting, CopyDocument, MagicStick } from '@element-plus/icons-vue'

const props = defineProps({
    projectId: { type: String, required: true },
    datasetId: { type: Number, default: null },
    metadata: { type: Object, default: null }
})

const loading = ref(false)
const results = ref(null)



const maxImportance = computed(() => {
    if (!results.value || !results.value.importance) return 1
    return Math.max(...results.value.importance.map(i => i.importance))
})

const metricTooltips = {
    'accuracy': '准确率：模型预测正确的样本占总样本的比例。',
    'auc': 'ROC曲线下面积：衡量二分类模型好坏，越接近1越好。0.5代表随机猜测。',
    'recall': '召回率：所有正例中被正确预测为正例的比例。',
    'f1': 'F1分数：精确率和召回率的调和平均数，综合衡量指标。',
    'r2': 'R平方：决定系数，表示模型解释了因变量方差的百分比。越接近1拟合越好。',
    'rmse': '均方根误差：预测值与真实值偏差的样本标准差。越小越好。',
    'cv_auc_mean': '5折交叉验证平均AUC：模型在未见数据上的平均表现，评估泛化能力。',
    'cv_auc_std': '5折交叉验证AUC标准差：评估模型表现的稳定性，值越小越稳定。',
    'aic': '赤池信息量：衡量模型拟合优度与参数复杂度的平衡，越小代表模型越精简有效。',
    'bic': '贝叶斯信息量：类似AIC，但对参数数量惩罚更重，常用于模型筛选，越小越好。',
    'c_index': '一致性指数：生存分析核心指标，衡量模型预测风险等级的准确性，越接近1越好。'
}

const modelOptions = [
    { label: '线性回归 (Linear Regression, OLS)', value: 'linear' },
    { label: '逻辑回归 (Logistic Regression)', value: 'logistic' },
    { label: 'Cox 比例风险回归 (Cox Proportional Hazards)', value: 'cox' },
    { label: '随机森林 (Random Forest)', value: 'random_forest' },
    { label: 'XGBoost', value: 'xgboost' }
]

const config = reactive({
    model_type: 'logistic',
    target: null, 
    features: [],
    ref_levels: {}, // { 'Sex': 'Female' }
    model_params: {
        n_estimators: 100,
        max_depth: null,
        learning_rate: 0.1
    }
})

const autoSuggestRoles = () => {
    if (!props.metadata) return
    const vars = props.metadata.variables
    const lowerVars = vars.map(v => ({...v, lower: v.name.toLowerCase()}))
    
    // 1. Suggest Model Type (Default Logistic if 'status'/'outcome' exists)
    // Keep current selection usually, or default to logistic if unknown.
    
    // 2. Identify Target
    let target = null
    let time = null
    let event = null
    
    // Heuristic Patterns
    const targetKeywords = ['status', 'event', 'outcome', 'death', 'died', 'recurrence', 'y', 'flag', 'label']
    const timeKeywords = ['time', 'duration', 'days', 'month', 'year', 'os', 'pfs', 'rfs']
    const idKeywords = ['id', 'no', 'code', 'name']
    
    if (config.model_type === 'cox') {
        const timeVar = lowerVars.find(v => timeKeywords.some(k => v.lower.includes(k) && !v.lower.includes('id')))
        if (timeVar) config.target.time = timeVar.name
        
        const eventVar = lowerVars.find(v => targetKeywords.some(k => v.lower.includes(k)))
        if (eventVar) config.target.event = eventVar.name
    } else {
        const targetVar = lowerVars.find(v => targetKeywords.some(k => v.lower.includes(k)))
        if (targetVar) config.target = targetVar.name
    }
    
    // 3. Identify Features (Covariates)
    // Exclude target(s), IDs, and likely non-covariates
    const currentTargets = []
    if (config.model_type === 'cox') {
        if (config.target.time) currentTargets.push(config.target.time)
        if (config.target.event) currentTargets.push(config.target.event)
    } else {
        if (config.target) currentTargets.push(config.target)
    }
    
    config.features = vars.filter(v => 
        !currentTargets.includes(v.name) && 
        !idKeywords.some(k => v.name.toLowerCase().includes(k)) &&
        v.unique_count > 1 // Exclude constants
    ).map(v => v.name)
    
    ElMessage.success('已根据变量名为您自动推荐配置')
}

// Collinearity Check Logic
let collinearityTimer = null
const checkingCollinearity = ref(false)
const collinearityWarning = ref(null)

const checkCollinearity = async () => {
    collinearityWarning.value = null
    if (config.features.length < 2) return
    
    checkingCollinearity.value = true
    try {
        const { data } = await api.post('/statistics/check-collinearity', {
            dataset_id: props.datasetId,
            features: config.features
        })
        
        if (data.status !== 'ok') {
            // Show persistent warning
            const first = data.report[0]
            collinearityWarning.value = `检测到共线性风险: ${first.message} (VIF=${first.vif.toFixed(1)})。建议移除该变量。`
        }
    } catch (e) {
        console.error("Collinearity check failed", e)
    } finally {
        checkingCollinearity.value = false
    }
}

watch(() => config.features, (newVal) => {
    collinearityWarning.value = null
    if (collinearityTimer) clearTimeout(collinearityTimer)
    collinearityTimer = setTimeout(() => {
        checkCollinearity()
    }, 1000) // Debounce 1s
})

const variableOptions = computed(() => {
    if (!props.metadata) return []
    return props.metadata.variables.map(v => {
        // Find health status
        const h = varHealthMap.value[v.name]
        return { 
            label: v.name, 
            value: v.name,
            type: v.type, // Added type for filtering
            status: h ? h.status : 'unknown',
            msg: h ? h.message : ''
        }
    })
})

const targetOptions = computed(() => {
    // For Linear Regression, Target must be numeric (continuous)
    if (config.model_type === 'linear') {
        return variableOptions.value.map(v => ({
            ...v,
            disabled: !['continuous', 'float', 'int'].includes(v.type)
        }))
    }
    return variableOptions.value
})

const varHealthMap = ref({})

const fetchHealthStatus = async () => {
    if (!props.metadata || !props.datasetId) return
    const allVars = props.metadata.variables.map(v => v.name)
    try {
        const { data } = await api.post('/statistics/check-health', {
            dataset_id: props.datasetId,
            variables: allVars
        })
        // Map to object
        const map = {}
        data.report.forEach(item => {
            map[item.variable] = item
        })
        varHealthMap.value = map
    } catch (e) {
        console.error("Health fetch failed", e)
    }
}

// Auto-trigger when metadata loads for the first time
watch(() => props.metadata, (newVal) => {
    if (newVal) {
        fetchHealthStatus()
        
        if (!config.target || !config.target.time) {
            // Only run if empty
            autoSuggestRoles()
        }
    }
}, { immediate: true })

const topResult = computed(() => {
    if (!results.value || !results.value.summary) return null
    
    // Find most significant variable
    const sigVars = results.value.summary.filter(v => v.p_value < 0.05)
    if (sigVars.length === 0) return null
    
    let top = null
    const type = config.model_type
    
    // Logic to pick "best" one
    if (type === 'logistic') {
        top = sigVars.reduce((prev, curr) => curr.or > prev.or ? curr : prev, sigVars[0])
    } else if (type === 'cox') {
         top = sigVars.reduce((prev, curr) => curr.hr > prev.hr ? curr : prev, sigVars[0])
    } else {
         top = sigVars.reduce((prev, curr) => Math.abs(curr.coef) > Math.abs(prev.coef) ? curr : prev, sigVars[0])
    }
    
    if (!top) return null
    
    let effect = null
    if (type === 'logistic') effect = top.or
    else if (type === 'cox') effect = top.hr
    
    return {
        p_value: top.p_value,
        effectSize: effect,
        desc: `变量 **${top.variable}** 对结果影响最为显著。`
    }
})

const smartSummary = computed(() => {
    if (!results.value) return ''
    const res = results.value
    const lines = []

    // 1. Variable Significance & Impact
    if (res.importance) {
        const topFeats = res.importance.slice(0, 3).map(f => f.feature).join(', ')
        lines.push(`Features: 模型最重要的前 3 个特征变量为：${topFeats}。`)
    } else if (res.summary) {
        const sigVars = res.summary.filter(v => v.p_value < 0.05)
        if (sigVars.length === 0) {
            lines.push('Variables: 未发现统计学显著 (P < 0.05) 的变量。')
        } else {
             const type = config.model_type
             let msg = `Variables: 发现 ${sigVars.length} 个显著变量。`
             
             let topVar = null
             if (type === 'logistic') {
                topVar = sigVars.reduce((prev, curr) => curr.or > prev.or ? curr : prev, sigVars[0])
                msg += `其中 **${topVar.variable}** 风险增加最为显著 (OR=${topVar.or.toFixed(2)}, P=${topVar.p_value < 0.001 ? '<0.001' : topVar.p_value.toFixed(3)})。`
            } else if (type === 'cox') {
                topVar = sigVars.reduce((prev, curr) => curr.hr > prev.hr ? curr : prev, sigVars[0])
                msg += `其中 **${topVar.variable}** 风险增加最为显著 (HR=${topVar.hr.toFixed(2)}, P=${topVar.p_value < 0.001 ? '<0.001' : topVar.p_value.toFixed(3)})。`
            } else {
                 topVar = sigVars.reduce((prev, curr) => Math.abs(curr.coef) > Math.abs(prev.coef) ? curr : prev, sigVars[0])
                 msg += `其中 **${topVar.variable}** 影响最大 (Coef=${topVar.coef.toFixed(2)}, P=${topVar.p_value < 0.001 ? '<0.001' : topVar.p_value.toFixed(3)})。`
            }
            lines.push(msg)
        }
    }

    // 2. Model Performance
    if (res.metrics) {
        if (res.metrics.auc) {
            const auc = parseFloat(res.metrics.auc)
            let grade = '无法评估'
            if (auc >= 0.9) grade = '极好 (Outstanding)'
            else if (auc >= 0.8) grade = '优秀 (Excellent)'
            else if (auc >= 0.7) grade = '良好 (Acceptable)'
            else if (auc >= 0.5) grade = '一般 (Poor)'
            else grade = '差 (Fail)'
            
            let perfMsg = `Performance: AUC = ${auc.toFixed(3)}，模型区分度 ${grade}。`
            if (res.metrics.cv_auc_mean) {
                perfMsg += ` 5折交叉验证平均 AUC = ${res.metrics.cv_auc_mean} (Std=${res.metrics.cv_auc_std})，泛化能力可靠。`
            }
            lines.push(perfMsg)
        } else if (res.metrics.c_index) {
             const cno = parseFloat(res.metrics.c_index)
             lines.push(`Performance: C-index = ${cno.toFixed(3)}。`)
        } else if (res.metrics.r2) {
             lines.push(`Performance: R-squared = ${parseFloat(res.metrics.r2).toFixed(3)}。`)
        }
    }

    // 3. Diagnostics Warnings
    if (res.summary) {
        // VIF Check
        const highVif = res.summary.filter(v => v.vif && v.vif !== '-' && parseFloat(v.vif) > 5)
        if (highVif.length > 0) {
            const vars = highVif.map(v => v.variable).join(', ')
            lines.push(`⚠️ Diagnostics: 检测到多重共线性 (VIF > 5): ${vars}。建议移除相关性过高的特征。`)
        }
        
        // PH Assumption Check
        const phFail = res.summary.filter(v => v.ph_test_p && v.ph_test_p !== '-' && parseFloat(v.ph_test_p) < 0.05)
        if (phFail.length > 0) {
             const vars = phFail.map(v => v.variable).join(', ')
             lines.push(`⚠️ Diagnostics: 违反 PH 等比例风险假设 (P < 0.05): ${vars}。建议使用分层 Cox 模型或含时变协变量的 Cox 模型。`)
        }
    }

    return lines.join('\n\n')
})

const runModel = async () => {
    if (!props.datasetId) return
    loading.value = true
    try {
        const { data } = await api.post('/modeling/run', {
            project_id: props.projectId,
            dataset_id: props.datasetId,
            ...config
        })
        if (data.results.status === 'failed') {
            results.value = null // Clear previous good results
            // Show diagnositic error
            ElMessage({
                message: data.results.message,
                type: 'error',
                duration: 10000,
                showClose: true,
                grouping: true
            })
            // Optionally, we could set a reactive 'errorState' to show a persistent alert in UI
            // But for now, a long duration Toast is consistent with user request "Give me a hint".
            return 
        }
        
        results.value = data.results
        ElMessage.success('模型运行成功')
        
        if (results.value.plots) {
            await nextTick()
            renderEvaluationPlots(results.value.plots)
        }
    } catch (error) {
        ElMessage.error(error.response?.data?.message || '模型运行失败')
    } finally {
        loading.value = false
    }
}

const selectedCategoricalVars = computed(() => {
    if (!props.metadata || !config.features || config.features.length === 0) return []
    return props.metadata.variables.filter(v => 
        config.features.includes(v.name) && 
        v.type === 'categorical' && 
        v.categories && v.categories.length > 0
    )
})

const copyMethodology = () => {
    // Generate text
    const text = MethodologyGenerator.generate(config, results.value)
    navigator.clipboard.writeText(text).then(() => {
        ElMessage.success('方法学段落已复制到剪贴板')
    }).catch(err => {
        ElMessage.error('复制失败')
    })
}

const chartData = reactive({
    roc: { data: [], layout: {} },
    calibration: { data: [], layout: {} },
    dca: { data: [], layout: {} },
    vif: { data: [], layout: {} }
})

const renderEvaluationPlots = (plots) => {
    // ROC Curve
    if (plots.roc) {
        chartData.roc.data = [
            {
                x: plots.roc.fpr,
                y: plots.roc.tpr,
                mode: 'lines',
                name: `AUC = ${plots.roc.auc.toFixed(3)}`,
                line: { color: 'blue' }
            },
            {
                x: [0, 1], y: [0, 1],
                mode: 'lines',
                name: 'Random',
                line: { dash: 'dash', color: 'gray' }
            }
        ]
        chartData.roc.layout = {
            xaxis: { title: 'False Positive Rate' },
            yaxis: { title: 'True Positive Rate' }
        }
    }

    // Calibration Curve
    if (plots.calibration) {
        chartData.calibration.data = [
            {
                x: plots.calibration.prob_pred,
                y: plots.calibration.prob_true,
                mode: 'lines+markers',
                name: 'Model',
                line: { color: 'red' }
            },
            {
                x: [0, 1], y: [0, 1],
                mode: 'lines',
                name: 'Perfectly Calibrated',
                line: { dash: 'dash', color: 'gray' }
            }
        ]
        chartData.calibration.layout = {
            xaxis: { title: 'Mean Predicted Probability', range: [0, 1] },
            yaxis: { title: 'Fraction of Positives', range: [0, 1] }
        }
    }

    // DCA Plot
    if (plots.dca) {
        const maxY = Math.max(...plots.dca.net_benefit_model, ...plots.dca.net_benefit_all)
        chartData.dca.data = [
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_model,
                mode: 'lines',
                name: 'Model',
                line: { color: 'red', width: 2 }
            },
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_all,
                mode: 'lines',
                name: 'Treat All',
                line: { color: 'gray', dash: 'dash' }
            },
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_none,
                mode: 'lines',
                name: 'Treat None',
                line: { color: 'black' }
            }
        ]
        chartData.dca.layout = {
            xaxis: { title: 'Threshold Probability', range: [0, 1] },
            yaxis: { title: 'Net Benefit', range: [-0.05, maxY + 0.05] }
        }
    }

    // VIF Plot
    if (plots.vif) {
        chartData.vif.data = [{
            x: plots.vif.variables,
            y: plots.vif.vif_values,
            type: 'bar',
            marker: {
                color: plots.vif.vif_values.map(v => v > 5 ? 'red' : '#409EFF')
            }
        }]
        chartData.vif.layout = {
             title: 'VIF Values',
             shapes: [{
                type: 'line',
                x0: -0.5, x1: plots.vif.variables.length - 0.5,
                y0: 5, y1: 5,
                line: { color: 'red', width: 2, dash: 'dash' }
             }]
        }
    }
}

const exportResults = async () => {
     try {
        const { data } = await api.post('/modeling/export', {
            project_id: props.projectId,
            dataset_id: props.datasetId,
            ...config
        })
        window.open(data.download_url, '_blank')
        ElMessage.success('导出成功')
    } catch (error) {
        ElMessage.error('导出失败')
    }
}

// Removed downloadPlot function as it is now handled by InsightChart component
// const downloadPlot = async (divId, filename, format = 'png') => { ... }
</script>



<style scoped>
.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    font-weight: bold;
    color: #606266;
}
</style>
