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

                <!-- Metrics -->
                <el-descriptions title="模型指标" :column="2" border size="small" style="margin-bottom: 20px">
                    <el-descriptions-item v-for="(val, key) in results.metrics" :key="key" :label="key">
                        {{ val.toFixed(4) }}
                    </el-descriptions-item>
                </el-descriptions>

                   <!-- ML Results -->
                <div v-if="results.importance">
                    <el-descriptions title="模型指标 (Metrics)" :column="2" border size="small" style="margin-bottom: 20px">
                        <el-descriptions-item v-for="(val, key) in results.metrics" :key="key" :label="key">
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
                        <template #default="scope">{{ scope.row.coef.toFixed(4) }}</template>
                    </el-table-column>
                    <el-table-column prop="p_value" label="P值">
                        <template #default="scope">
                            <span :style="{ fontWeight: scope.row.p_value < 0.05 ? 'bold' : 'normal', color: scope.row.p_value < 0.05 ? 'red' : 'inherit' }">
                                {{ scope.row.p_value < 0.001 ? '<0.001' : scope.row.p_value.toFixed(4) }}
                            </span>
                        </template>
                    </el-table-column>
                    <el-table-column v-if="config.model_type === 'logistic'" label="OR (95% CI)">
                        <template #default="scope">
                            {{ scope.row.or.toFixed(2) }} ({{ scope.row.or_ci_lower.toFixed(2) }}-{{ scope.row.or_ci_upper.toFixed(2) }})
                        </template>
                    </el-table-column>
                    <el-table-column v-if="config.model_type === 'cox'" label="HR (95% CI)">
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

const config = reactive({
    model_type: 'logistic',
    target: null, 
    features: []
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
