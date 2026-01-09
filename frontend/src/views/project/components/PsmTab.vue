<template>
  <div class="psm-container">
    <StepWizard 
        :steps="steps" 
        v-model="activeStep" 
        :loading="loading"
        :disable-next="disableNext"
        @finish="activeStep = 0"
    >
        <!-- Step 1: Treatment Selection -->
        <template #step1>
            <div class="wizard-step">
                <h3>选择处理组变量 (Select Treatment)</h3>
                <p class="step-desc">请选择区分"实验组"和"对照组"的二分类变量（0/1）。系统将基于此变量进行匹配。</p>
                
                <el-form label-position="top">
                    <el-form-item label="处理组变量 (Treatment Variable)">
                        <el-select v-model="config.treatment" placeholder="Binary (0/1)" filterable size="large" style="width: 100%; max-width: 400px;">
                             <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>
                </el-form>
                
                <el-alert
                    v-if="config.treatment"
                    :title="`已选择: ${config.treatment}`"
                    type="success"
                    :closable="false"
                    show-icon
                >
                    <div>请确认该变量中：Selected=1 (Experimental), Other=0 (Control)</div>
                </el-alert>
            </div>
        </template>

        <!-- Step 2: Covariates Selection -->
        <template #step2>
            <div class="wizard-step">
                <h3>选择协变量 (Select Covariates)</h3>
                <p class="step-desc">请选择那些即影响分组、又影响结果的混杂因素。匹配后，两组在这些变量上将达到均衡。</p>
                
                <el-form label-position="top">
                    <el-form-item label="协变量 (Confounders / Covariates)">
                        <el-select v-model="config.covariates" multiple placeholder="Select Covariates" filterable size="large" style="width: 100%;">
                             <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>
                    
                     <el-form-item>
                        <el-checkbox v-model="config.save" border>匹配成功后，自动保存为新数据集</el-checkbox>
                    </el-form-item>
                </el-form>
                
                <el-alert
                    title="操作指南"
                    type="info"
                    show-icon
                    :closable="false"
                >
                    <div style="font-size: 13px; color: #606266; line-height: 1.6;">
                        <li><b>推荐策略</b>: 纳入所有基线特征（User Baseline），特别是已知对预后有影响的因素。</li>
                        <li><b>避免</b>: 不要纳入受治疗影响的变量（中间变量）。</li>
                    </div>
                </el-alert>
            </div>
        </template>

        <!-- Step 3: Result & Diagnostics -->
        <template #step3>
            <div class="wizard-step result-step" v-loading="loading">
                <div v-if="results">
                     <el-result icon="success" title="匹配完成" :sub-title="`匹配成功！共匹配 ${results.stats.n_matched} 例。`">
                     </el-result>

                     <el-alert v-if="results.new_dataset_id" title="新数据集已保存" type="info" show-icon style="margin-bottom: 20px" />
                     
                     <h4>均衡性诊断表 (Balance Table)</h4>
                     <el-table :data="results.balance" style="width: 100%; margin-bottom: 20px;" border stripe>
                        <el-table-column prop="variable" label="协变量" />
                        <el-table-column prop="smd_pre" label="匹配前 SMD">
                            <template #header>
                                <span>匹配前 SMD</span>
                                <el-tooltip content="Standardized Mean Difference (标准化均数差)，衡量原始组间的差异。" placement="top">
                                    <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </template>
                            <template #default="scope">{{ scope.row.smd_pre.toFixed(3) }}</template>    
                        </el-table-column>
                        <el-table-column prop="smd_post" label="匹配后 SMD">
                            <template #header>
                                <span>匹配后 SMD</span>
                                <el-tooltip content="匹配后两组间的差异。理想情况下应 < 0.1，表明达到高度均衡。" placement="top">
                                    <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </template>
                            <template #default="scope">
                                <span :style="{ fontWeight: 'bold', color: scope.row.smd_post < 0.1 ? 'green' : 'red' }">
                                    {{ scope.row.smd_post.toFixed(3) }}
                                </span>
                            </template>
                        </el-table-column>
                         <el-table-column label="评估">
                            <template #default="scope">
                                <el-tag :type="scope.row.smd_post < 0.1 ? 'success' : 'warning'">
                                    {{ scope.row.smd_post < 0.1 ? 'Balanced' : 'Unbalanced' }}
                                </el-tag>
                            </template>
                        </el-table-column>
                     </el-table>
                     
                     <h4>协变量平衡图 (Love Plot)</h4>
                     <div id="love-plot" style="width: 100%; height: 500px;"></div>
                </div>
                <div v-else-if="!loading" style="text-align: center; color: gray;">
                    准备就绪，系统正在进行匹配计算...
                </div>
            </div>
        </template>
    </StepWizard>
  </div>
</template>

<script setup>
/**
 * PsmTab.vue
 * 倾向性评分匹配 (PSM) 组件 - 向导版。
 */
import { ref, reactive, computed, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'
import StepWizard from './StepWizard.vue'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const emit = defineEmits(['dataset-created'])

const loading = ref(false)
const results = ref(null)
const activeStep = ref(0)

const config = reactive({
    treatment: null,
    covariates: [],
    save: false
})

const steps = [
    { title: '设定组别', description: '选择处理组变量', slot: 'step1' },
    { title: '选择协变量', description: '选择需平衡的混杂因素', slot: 'step2' },
    { title: '匹配诊断', description: '查看匹配效果与平衡性', slot: 'step3' }
]

const variableOptions = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables.map(v => ({ 
        label: v.name, 
        value: v.name 
    }))
})

// Control next button
const disableNext = computed(() => {
    if (activeStep.value === 0) return !config.treatment
    if (activeStep.value === 1) return config.covariates.length === 0
    return false
})

// Watch step change to trigger calculation
watch(activeStep, (newStep, oldStep) => {
    if (newStep === 2 && oldStep === 1) {
        runPSM()
    }
})

const runPSM = async () => {
    loading.value = true
    results.value = null
    
    try {
        const { data } = await api.post('/statistics/psm', {
            dataset_id: props.datasetId,
            ...config
        })
        
        results.value = data
        
        if (data.new_dataset_id) {
            emit('dataset-created', data.new_dataset_id)
            ElMessage.success({
                message: "匹配成功！已为您生成并自动切换至匹配后的新数据集版本。",
                duration: 5000
            })
        }
        
        // Render Love Plot
        nextTick(() => {
            if (data.balance) renderLovePlot(data.balance)
        })
        
    } catch (error) {
        ElMessage.error(error.response?.data?.message || "匹配失败")
        // Go back to prev step if failed?
        activeStep.value = 1 
    } finally {
        loading.value = false
    }
}

const renderLovePlot = (balanceData) => {
    // balanceData: [{variable, smd_pre, smd_post}, ...]
    const sorted = [...balanceData].sort((a,b) => Math.abs(a.smd_pre) - Math.abs(b.smd_pre));
    
    const vars = sorted.map(d => d.variable);
    const pre = sorted.map(d => Math.abs(d.smd_pre));
    const post = sorted.map(d => Math.abs(d.smd_post));
    
    const trace1 = {
        x: pre,
        y: vars,
        mode: 'markers',
        name: 'Unmatched',
        marker: { color: '#F56C6C', size: 10, symbol: 'circle-open' }, // Red open circle
        type: 'scatter'
    };
    
    const trace2 = {
        x: post,
        y: vars,
        mode: 'markers',
        name: 'Matched',
        marker: { color: '#67C23A', size: 10, symbol: 'circle' }, // Green filled circle
        type: 'scatter'
    };
    
    const layout = {
        title: 'Covariate Balance (Love Plot)',
        xaxis: { 
            title: 'Absolute Standardized Mean Difference (SMD)', 
            range: [0, Math.max(0.2, ...pre) + 0.1],
            zeroline: true
        },
        yaxis: { 
            title: '',
            automargin: true 
        },
        shapes: [
            {
                type: 'line',
                x0: 0.1, x1: 0.1,
                y0: 0, y1: 1, yref: 'paper',
                line: { color: 'gray', width: 1, dash: 'dash' }
            }
        ],
        margin: { l: 150, r: 20, t: 40, b: 40 },
        legend: { x: 0.8, y: 0.1 }
    };
    
    Plotly.newPlot('love-plot', [trace1, trace2], layout);
}
</script>

<style scoped>
.psm-container {
    padding: 0;
}
.wizard-step {
    max-width: 800px;
    margin: 0 auto;
}
.step-desc {
    color: #606266;
    margin-bottom: 20px;
}
</style>
