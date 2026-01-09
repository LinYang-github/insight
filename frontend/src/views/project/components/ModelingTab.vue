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
                   <el-form-item label="模型类型">
                       <el-select v-model="config.model_type" placeholder="选择模型" style="width: 100%">
                           <el-option v-for="opt in modelOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                       </el-select>
                   </el-form-item>
                   
                   <el-form-item label="目标变量 (Outcome)">
                       <template v-if="config.model_type !== 'cox'">
                           <el-select v-model="config.target" placeholder="选择目标变量" filterable style="width: 100%">
                               <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
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
                       <el-select v-model="config.features" multiple placeholder="选择特征变量" filterable style="width: 100%">
                           <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                       </el-select>
                   </el-form-item>

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
                        <el-button type="success" size="small" @click="exportResults">导出 Excel</el-button>
                    </div>
                </template>

                 <!-- Smart Summary -->
                 <el-alert
                    v-if="smartSummary"
                    title="智能解读 (Smart Insights)"
                    type="success"
                    :description="smartSummary"
                    show-icon
                    :closable="false"
                    style="margin-bottom: 20px"
                 />

                <!-- Metrics -->
                <el-descriptions title="模型指标" :column="2" border size="small" style="margin-bottom: 20px">
                    <el-descriptions-item v-for="(val, key) in results.metrics" :key="key" :label="key">
                        {{ val.toFixed(4) }}
                    </el-descriptions-item>
                </el-descriptions>

                   <!-- ML Results -->
                <div v-if="results.importance">
                    <el-descriptions title="模型指标 (Metrics)" :column="2" border size="small" style="margin-bottom: 20px">
                        <el-descriptions-item v-for="(val, key) in results.metrics" :key="key">
                            <template #label>
                                <span>{{ key }}</span>
                                <el-tooltip v-if="metricTooltips[key]" :content="metricTooltips[key]" placement="top">
                                    <el-icon style="margin-left: 4px; color: #909399; cursor: pointer"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </template>
                            <template v-if="typeof val === 'number'">{{ val.toFixed(4) }}</template>
                            <template v-else>{{ val }}</template>
                        </el-descriptions-item>
                    </el-descriptions>
                    
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
                                {{ scope.row.p_value < 0.001 ? '<0.001' : scope.row.p_value.toFixed(4) }}
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
                </el-table>
           </el-card>
       </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'

import { QuestionFilled } from '@element-plus/icons-vue'

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
    'rmse': '均方根误差：预测值与真实值偏差的样本标准差。越小越好。'
}

const config = reactive({
    model_type: 'logistic',
    target: null, 
    features: [],
    model_params: {
        n_estimators: 100,
        max_depth: null,
        learning_rate: 0.1
    }
})

watch(() => config.model_type, (newType) => {
    if (newType === 'cox') {
        config.target = { time: null, event: null }
    } else {
        config.target = null
    }
})

const modelOptions = [
    { label: '逻辑回归 (Logistic)', value: 'logistic' },
    { label: '线性回归 (Linear)', value: 'linear' },
    { label: 'Cox 生存分析', value: 'cox' },
    { label: '随机森林 (Random Forest)', value: 'random_forest' },
    { label: 'XGBoost', value: 'xgboost' }
]

const variableOptions = computed(() => {
    if (!props.metadata) return []
    return props.metadata.variables.map(v => ({ label: v.name, value: v.name }))
})

const smartSummary = computed(() => {
    if (!results.value) return ''
    const res = results.value

    // ML Models (RF, XGB)
    if (res.importance) {
        const topFeats = res.importance.slice(0, 3).map(f => f.feature).join(', ')
        return `模型最重要的前 3 个特征变量为：${topFeats}。该模型的 ${res.task === 'classification' ? '准确率(Accuracy)' : '拟合优度(R2)'} 为 ${res.metrics.accuracy?.toFixed(2) || res.metrics.r2?.toFixed(2)}。`
    }

    // Statistical Models
    if (res.summary) {
        const sigVars = res.summary.filter(v => v.p_value < 0.05)
        if (sigVars.length === 0) {
            return '未发现统计学显著 (P < 0.05) 的变量。模型可能需要更多样本或调整特征。'
        }

        const type = config.model_type
        let msg = `发现 ${sigVars.length} 个显著变量。`
        
        // Find most impactful
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
        return msg
    }
    return ''
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
        results.value = data.results
        ElMessage.success('模型运行成功')
    } catch (error) {
        ElMessage.error(error.response?.data?.message || '模型运行失败')
    } finally {
        loading.value = false
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
</script>

<style scoped>
.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
</style>
