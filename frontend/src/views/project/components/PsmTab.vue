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
                <h3>选择匹配因素 (Covariates) <GlossaryTooltip term="or" v-if="false" /></h3>
                <p class="step-desc">请选择那些即影响分组、又影响结果的混杂因素。匹配后，两组在这些变量上将达到均衡。</p>
                
                <el-form label-position="top" v-loading="isRecommending">
                    <el-form-item>
                        <template #label>
                             <span>纳入匹配的协变量 (Covariates)</span>
                             <GlossaryTooltip term="vif" style="margin-left: 8px">什么是协变量？</GlossaryTooltip>
                        </template>
                        <el-select v-model="config.covariates" multiple placeholder="Select Covariates" filterable size="large" style="width: 100%;">
                             <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                        <div v-if="recommendedVars.length > 0" class="recommend-hint">
                            <el-icon><MagicStick /></el-icon>
                            <span>系统已根据组间显著差异自动预选了 <b>{{ recommendedVars.length }}</b> 个变量。</span>
                        </div>
                    </el-form-item>
                    
                     <el-form-item>
                        <el-checkbox v-model="config.save" border>匹配成功后，自动保存为新数据集</el-checkbox>
                        <GlossaryTooltip term="caliper" style="margin-left: 10px">关于匹配设置</GlossaryTooltip>
                    </el-form-item>
                </el-form>
                
                <el-alert
                    title="智能建议"
                    type="success"
                    show-icon
                    :closable="false"
                    v-if="recommendedVars.length > 0"
                >
                    <div style="font-size: 13px; color: #606266; line-height: 1.6;">
                        <li>系统已识别出处理组间存在显著差异的变量，建议将其纳入匹配以消除偏差。</li>
                        <li><b>当前已选中</b>: {{ config.covariates.join(', ') }}</li>
                    </div>
                </el-alert>

                <div v-if="healthReport.length > 0" class="health-report-area">
                    <h4>数据健康预检 (Pre-flight Check)</h4>
                    <div class="health-cards">
                        <div v-for="item in healthReport" :key="item.variable" :class="['health-card', item.status]">
                            <div class="health-header">
                                <span class="var-name">{{ item.variable }}</span>
                                <el-tag :type="item.status === 'healthy' ? 'success' : 'warning'" size="small">
                                    {{ item.status === 'healthy' ? 'Healthy' : 'Warning' }}
                                </el-tag>
                            </div>
                            <div class="health-details">
                                <span>缺失率: {{ (item.missing_rate * 100).toFixed(1) }}%</span>
                            </div>
                            <div v-if="item.status !== 'healthy'" class="health-msg">
                                <el-icon><Warning /></el-icon> {{ item.message }}
                            </div>
                        </div>
                    </div>
                </div>
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
                                <GlossaryTooltip term="smd">匹配前 SMD</GlossaryTooltip>
                            </template>
                            <template #default="scope">{{ scope.row.smd_pre.toFixed(3) }}</template>    
                        </el-table-column>
                        <el-table-column prop="smd_post" label="匹配后 SMD">
                            <template #header>
                                <GlossaryTooltip term="smd">匹配后 SMD</GlossaryTooltip>
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
import GlossaryTooltip from './GlossaryTooltip.vue'
import { QuestionFilled, MagicStick } from '@element-plus/icons-vue'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const emit = defineEmits(['dataset-created'])

const loading = ref(false)
const results = ref(null)
const activeStep = ref(0)
const recommendedVars = ref([])
const isRecommending = ref(false)
const healthReport = ref([])

const config = reactive({
    treatment: null,
    covariates: [],
    save: false
})

// ... props and emits ...

// Watch treatment to recommend covariates
watch(() => config.treatment, async (newVal) => {
    if (newVal) {
        config.covariates = [] // Reset
        await fetchRecommendations(newVal)
    }
})

// Watch covariates to check health
watch(() => config.covariates, (newVal) => {
    if (newVal && newVal.length > 0) {
        checkHealth(newVal)
    } else {
        healthReport.value = []
    }
}, { deep: true })

const checkHealth = async (variables) => {
    try {
        const { data } = await api.post('/statistics/check-health', {
            dataset_id: props.datasetId,
            variables
        })
        healthReport.value = data.report
    } catch (err) {
        console.error("Health check failed", err)
    }
}

const fetchRecommendations = async (treatment) => {
    isRecommending.value = true
    try {
        const { data } = await api.post('/statistics/recommend-covariates', {
            dataset_id: props.datasetId,
            treatment
        })
        recommendedVars.value = data.recommendations
        // Auto-apply highly significant ones? Or just let user click.
        // Let's auto-apply for "No-Manual" experience.
        config.covariates = data.recommendations.map(r => r.variable)
        if (config.covariates.length > 0) {
            ElMessage({
                message: `系统已自动为您预选了 ${config.covariates.length} 个组间差异显著的协变量。`,
                type: 'success',
                duration: 3000
            })
            // Manually trigger health check if watch doesn't catch it fast enough
            checkHealth(config.covariates)
        }
    } catch (err) {
        console.error("Recommendation failed", err)
    } finally {
        isRecommending.value = false
    }
}

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
.recommend-hint {
    margin-top: 8px;
    font-size: 13px;
    color: #67c23a;
    display: flex;
    align-items: center;
    gap: 6px;
    background: #f0f9eb;
    padding: 6px 12px;
    border-radius: 4px;
}
.health-report-area {
    margin-top: 25px;
    border-top: 1px solid #ebeef5;
    padding-top: 15px;
}
.health-report-area h4 {
    margin-bottom: 12px;
    font-size: 15px;
    color: #303133;
}
.health-cards {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}
.health-card {
    width: calc(50% - 6px);
    border: 1px solid #e4e7ed;
    border-radius: 6px;
    padding: 10px;
    background: #fafafa;
}
.health-card.warning {
    border-color: #fce4d6;
    background: #fff9f5;
}
.health-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.var-name {
    font-weight: bold;
    font-size: 13px;
}
.health-details {
    font-size: 12px;
    color: #606266;
}
.health-msg {
    margin-top: 8px;
    font-size: 11px;
    color: #e6a23c;
    display: flex;
    align-items: center;
    gap: 4px;
}
</style>
