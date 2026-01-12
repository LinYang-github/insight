<template>
    <div class="iptw-container">
        <el-row :gutter="20">
            <!-- Left: Configuration -->
            <el-col :span="6">
                <el-card shadow="never" class="config-card">
                    <template #header>
                        <span>⚖️ 逆概率加权 (IPTW)</span>
                    </template>
                    
                    <el-form label-position="top">
                        <el-form-item label="处理变量 (Treatment)" required>
                            <el-select v-model="treatment" filterable placeholder="选择二分类变量 (0/1)">
                                <el-option v-for="v in binaryVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        
                        <el-form-item label="协变量 (Covariates)" required>
                            <el-select v-model="covariates" multiple filterable placeholder="选择混杂因素">
                                <el-option 
                                    v-for="v in availableCovariates" 
                                    :key="v.name" 
                                    :label="v.name" 
                                    :value="v.name"
                                />
                            </el-select>
                        </el-form-item>
                        
                        <el-divider />
                        
                        <el-form-item label="权重类型 (Weight Type)">
                            <el-radio-group v-model="weightType">
                                <el-radio-button value="ATE">ATE (总体)</el-radio-button>
                                <el-radio-button value="ATT">ATT (处理组)</el-radio-button>
                            </el-radio-group>
                            <div class="help-text" style="font-size: 11px; margin-top: 5px; color: gray;">
                                {{ weightType === 'ATE' ? '评估全人群接受干预的效果' : '评估实际处理组接受干预的效果' }}
                            </div>
                        </el-form-item>
                        
                        <el-form-item>
                             <el-checkbox v-model="stabilized">稳定权重 (Stabilized)</el-checkbox>
                             <el-tooltip content="乘以处理变量的边际概率，减少极端权重的影响，保持样本量稳定。" placement="top">
                                 <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                             </el-tooltip>
                        </el-form-item>
                        
                        <el-form-item>
                             <el-checkbox v-model="truncate">截断极端权重 (1% / 99%)</el-checkbox>
                        </el-form-item>
                        
                        <el-form-item>
                             <el-checkbox v-model="saveResult">保存加权数据集</el-checkbox>
                        </el-form-item>
                        
                        <el-button 
                            type="primary" 
                            style="width: 100%; margin-top: 20px" 
                            @click="runIPTW" 
                            :loading="loading"
                            :disabled="!isValid"
                        >
                            执行加权分析
                        </el-button>
                    </el-form>
                </el-card>
            </el-col>
            
            <!-- Right: Results -->
            <el-col :span="18">
                <div v-if="!results" class="empty-placeholder">
                    <el-empty description="配置参数并运行以查看平衡性诊断" />
                </div>
                
                <div v-else class="results-area">
                    <!-- 1. Stats Summary -->
                    <div class="stats-summary">
                        <div class="stat-box">
                            <div class="label">处理组 (N)</div>
                            <div class="value">{{ results.n_treated }}</div>
                            <div class="sub">ESS: {{ results.ess_treated.toFixed(1) }}</div>
                        </div>
                        <div class="stat-box">
                            <div class="label">对照组 (N)</div>
                            <div class="value">{{ results.n_control }}</div>
                            <div class="sub">ESS: {{ results.ess_control.toFixed(1) }}</div>
                        </div>
                        <div class="stat-box" v-if="results.new_dataset_id">
                            <div class="label">新数据集 ID</div>
                            <div class="value" style="color: #2E7D32">{{ results.new_dataset_id }}</div>
                            <div class="sub">已保存</div>
                        </div>
                    </div>
                    
                    <!-- 2. Visualization (Love Plot & Weights) -->
                    <el-row :gutter="20" style="margin-top: 20px">
                        <el-col :span="14">
                            <el-card shadow="never">
                                <template #header>Love Plot (Standardized Mean Differences)</template>
                                <div id="love-plot" style="width: 100%; height: 400px;"></div>
                            </el-card>
                        </el-col>
                        <el-col :span="10">
                            <el-card shadow="never">
                                <template #header>Weight Distribution</template>
                                <div id="weight-plot" style="width: 100%; height: 400px;"></div>
                            </el-card>
                        </el-col>
                    </el-row>
                    
                    <!-- 3. SMD Table -->
                    <el-card shadow="never" style="margin-top: 20px">
                        <template #header>
                             <div style="display: flex; justify-content: space-between;">
                                 <span>平衡性详情 (SMD Table)</span>
                                 <el-button size="small" @click="copyTable">复制表格</el-button>
                             </div>
                        </template>
                        <el-table :data="results.balance" height="300" stripe size="small">
                            <el-table-column prop="variable" label="Variable" />
                            <el-table-column label="Pre-Weighting SMD">
                                <template #default="scope">
                                    <span :style="{color: scope.row.smd_pre > 0.1 ? '#D32F2F' : 'black'}">
                                        {{ scope.row.smd_pre.toFixed(3) }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column label="Post-Weighting SMD">
                                <template #default="scope">
                                    <span :style="{color: scope.row.smd_post > 0.1 ? '#D32F2F' : '#2E7D32', fontWeight: 'bold'}">
                                        {{ scope.row.smd_post.toFixed(3) }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column label="Reduction (%)">
                                <template #default="scope">
                                    {{ calculateReduction(scope.row.smd_pre, scope.row.smd_post) }}%
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-card>
                </div>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import api from '../../../api/client' // Corrected path
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const treatment = ref('')
const covariates = ref([])
const weightType = ref('ATE')
const stabilized = ref(true)
const truncate = ref(true)
const saveResult = ref(false)
const loading = ref(false)
const results = ref(null)

const binaryVars = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    // Simple logic: nunique=2 or likely categorical. 
    // Ideally metadata should have 'type' or 'nunique'.
    // Assuming user knows.
    return props.metadata.variables
})

const availableCovariates = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables.filter(v => v.name !== treatment.value)
})

const isValid = computed(() => {
    return treatment.value && covariates.value.length > 0
})

const calculateReduction = (pre, post) => {
    if (pre === 0) return 0
    const red = ((pre - post) / pre) * 100
    return red.toFixed(1)
}

const runIPTW = async () => {
    loading.value = true
    try {
        const payload = {
            dataset_id: props.datasetId,
            treatment: treatment.value,
            covariates: covariates.value,
            weight_type: weightType.value,
            stabilized: stabilized.value,
            truncate: truncate.value,
            save: saveResult.value
        }
        
        const { data } = await api.post('/statistics/iptw', payload)
        results.value = data
        ElMessage.success('IPTW 分析完成')
        
        nextTick(() => {
            renderLovePlot()
            renderWeightPlot()
        })
        
    } catch (error) {
        ElMessage.error(error.response?.data?.message || '分析失败')
    } finally {
        loading.value = false
    }
}

const renderLovePlot = () => {
    const el = document.getElementById('love-plot')
    if (!el || !results.value) return
    
    const vars = results.value.balance.map(r => r.variable)
    const smd_pre = results.value.balance.map(r => r.smd_pre)
    const smd_post = results.value.balance.map(r => r.smd_post)
    
    // Reverse for nice top-down plotting in horizontal bar
    // Actually scatter is better for Love Plot
    
    const trace1 = {
        x: smd_pre,
        y: vars,
        mode: 'markers',
        type: 'scatter',
        name: 'Unweighted',
        marker: { color: 'red', size: 8, symbol: 'circle-open' }
    }
    
    const trace2 = {
        x: smd_post,
        y: vars,
        mode: 'markers',
        type: 'scatter',
        name: 'Weighted',
        marker: { color: 'green', size: 10, symbol: 'circle' }
    }
    
    const layout = {
        title: 'Covariate Balance (Love Plot)',
        xaxis: { title: 'Absolute Standardized Mean Difference', range: [0, Math.max(0.5, ...smd_pre) + 0.1] },
        yaxis: { automargin: true },
        shapes: [
            {
                type: 'line',
                x0: 0.1, x1: 0.1,
                y0: 0, y1: 1, yref: 'paper',
                line: { color: 'gray', dash: 'dash', width: 1 }
            }
        ],
        margin: { l: 150, r: 20, t: 40, b: 40 }
    }
    
    Plotly.newPlot(el, [trace1, trace2], layout)
}

const renderWeightPlot = () => {
    const el = document.getElementById('weight-plot')
    if (!el || !results.value) return
    
    const weights = results.value.weights
    
    const trace = {
        x: weights,
        type: 'histogram',
        marker: { color: '#3B71CA' },
        opacity: 0.7
    }
    
    const layout = {
        title: 'Weight Distribution',
        xaxis: { title: 'Weight' },
        yaxis: { title: 'Frequency' },
        margin: { l: 40, r: 20, t: 40, b: 40 }
    }
    
    Plotly.newPlot(el, [trace], layout)
}

const copyTable = () => {
    // TSV copy logic similar to other tabs
    const headers = ['Variable', 'Pre-SMD', 'Post-SMD', 'Reduction%']
    const rows = results.value.balance.map(r => [
        r.variable,
        r.smd_pre.toFixed(4),
        r.smd_post.toFixed(4),
        calculateReduction(r.smd_pre, r.smd_post)
    ])
    
    const tsv = [headers.join('\t'), ...rows.map(r => r.join('\t'))].join('\n')
    navigator.clipboard.writeText(tsv).then(() => ElMessage.success('已复制表格'))
}
</script>

<style scoped>
.iptw-container {
    height: 100%;
}
.config-card {
    height: 100%;
    overflow-y: auto;
}
.empty-placeholder {
    height: 400px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.stats-summary {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
}
.stat-box {
    background: white;
    padding: 15px 25px;
    border-radius: 8px;
    border: 1px solid #ebeef5;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.stat-box .label {
    font-size: 12px;
    color: #909399;
}
.stat-box .value {
    font-size: 24px;
    font-weight: bold;
    color: #303133;
}
.stat-box .sub {
    font-size: 11px;
    color: #909399;
    margin-top: 4px;
}
</style>
