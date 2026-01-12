<template>
    <div class="competing-risks-container">
        <el-row :gutter="20">
            <!-- Left: Config -->
            <el-col :span="6">
                <el-card shadow="never">
                    <template #header>⚡️ 竞争风险模型</template>
                    <el-form label-position="top">
                        <el-form-item label="时间变量 (Time)" required>
                            <el-select v-model="config.time_col" filterable placeholder="Select Time">
                                <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        <el-form-item label="事件状态 (Event)" required>
                            <el-select v-model="config.event_col" filterable placeholder="Select Event (0,1,2...)">
                                <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                            <div class="help-text">需包含至少2种事件类型 (如: 1=死因A, 2=死因B)。0=Censor。</div>
                        </el-form-item>
                        
                        <el-form-item label="协变量 (Covariates)" required>
                            <el-select v-model="config.covariates" multiple filterable placeholder="Select Covariates">
                                <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        
                        <el-form-item label="分组变量 (Group - Optional)">
                             <el-select v-model="config.group_col" filterable clearable placeholder="For CIF Plotting">
                                <el-option v-for="v in catVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        
                        <el-button type="primary" style="width: 100%" @click="runAnalysis" :loading="loading" :disabled="!isValid">
                            运行分析 (Run Analysis)
                        </el-button>
                    </el-form>
                </el-card>
            </el-col>
            
            <!-- Right: Results -->
            <el-col :span="18">
                <div v-if="!hasResults" class="empty-placeholder">
                    <el-empty description="配置并运行以查看 Cause-Specific Hazard Ratios & CIF" />
                </div>
                
                <div v-else class="results-area">
                    <el-tabs type="border-card">
                        <!-- Tab 1: CIF Plot -->
                        <el-tab-pane label="累积发生率 (CIF Plot)">
                             <div class="plot-container">
                                 <div id="cif-plot" style="width:100%; height:500px;"></div>
                             </div>
                             <div class="methodology-box" v-if="cifResults?.methodology">
                                 <strong>Methodology:</strong> {{ cifResults.methodology }}
                             </div>
                        </el-tab-pane>
                        
                        <!-- Tab 2: Cause-Specific Models -->
                        <el-tab-pane label="病因特异性模型 (CS-Models)">
                            <div v-for="model in modelResults.models" :key="model.event_type" style="margin-bottom: 30px;">
                                <div class="model-header">
                                    <h4 style="margin:0;">Event Type: {{ model.event_type }} (Cause-Specific Cox)</h4>
                                </div>
                                <el-table :data="model.summary" stripe border size="small">
                                    <el-table-column prop="variable" label="Variable" />
                                    <el-table-column prop="hr" label="HR (Hazard Ratio)">
                                        <template #default="scope">{{ scope.row.hr.toFixed(3) }}</template>
                                    </el-table-column>
                                    <el-table-column label="95% CI">
                                        <template #default="scope">
                                            {{ scope.row.ci_lower.toFixed(3) }} - {{ scope.row.ci_upper.toFixed(3) }}
                                        </template>
                                    </el-table-column>
                                    <el-table-column prop="p_value" label="P Value">
                                        <template #default="scope">
                                            <span :style="{fontWeight: scope.row.p_value < 0.05 ? 'bold' : 'normal', color: scope.row.p_value < 0.05 ? 'red' : 'inherit'}">
                                                {{ scope.row.p_value < 0.001 ? '<0.001' : scope.row.p_value.toFixed(3) }}
                                            </span>
                                        </template>
                                    </el-table-column>
                                </el-table>
                            </div>
                            <div class="methodology-box" v-if="modelResults?.methodology">
                                 <strong>Methodology:</strong> {{ modelResults.methodology }}
                             </div>
                        </el-tab-pane>
                    </el-tabs>
                </div>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const config = reactive({
    time_col: '',
    event_col: '',
    covariates: [],
    group_col: ''
})

const loading = ref(false)
const hasResults = ref(false)
const cifResults = ref(null)
const modelResults = ref(null)

const variables = computed(() => props.metadata?.variables || [])
const numVars = computed(() => variables.value.filter(v => v.type === 'numeric' || v.type === 'integer' || true)) // Broaden
const catVars = computed(() => variables.value) // Allow all for grouping usually

const isValid = computed(() => config.time_col && config.event_col && config.covariates.length > 0)

const runAnalysis = async () => {
    loading.value = true
    try {
        // 1. Run Models
        const p1 = api.post('/advanced/competing-risks', {
            dataset_id: props.datasetId,
            time_col: config.time_col,
            event_col: config.event_col,
            covariates: config.covariates
        })
        
        // 2. Run CIF Viz (Separate endpoint)
        const p2 = api.post('/advanced/cif', {
            dataset_id: props.datasetId,
            time_col: config.time_col,
            event_col: config.event_col,
            group_col: config.group_col || null
        })
        
        const [res1, res2] = await Promise.all([p1, p2])
        modelResults.value = res1.data
        cifResults.value = res2.data
        hasResults.value = true
        
        ElMessage.success('Use Cause-Specific Models for Etiology, CIF for Incidence.')
        
        nextTick(() => {
            renderCIF(res2.data.cif_data)
        })
        
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'Analysis Failed')
    } finally {
        loading.value = false
    }
}

const renderCIF = (cifData) => {
    // cifData: [{group: 'A', event_type: 1, cif_data: [{x,y}...]}, ...]
    // We plot lines.
    // X: Time, Y: CIF Probability
    
    // Color mapping per event type? Or per group?
    // Usually: Color = Group, LineStyle = EventType? 
    // Or Color = EventType, LineStyle = Group?
    // Let's do: Color = Group (if exists), else Color = EventType.
    
    const traces = []
    
    // Simple palette
    const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    // Group keys
    const groups = [...new Set(cifData.map(d => d.group))]
    
    cifData.forEach(item => {
        const x = item.cif_data.map(p => p.x)
        const y = item.cif_data.map(p => p.y)
        
        // Determine styling
        // If multiple groups: Color by Group.
        // If multiple events: Dash style by Event?
        
        let color = '#333'
        if (groups.length > 1) {
            const gIdx = groups.indexOf(item.group)
            color = colors[gIdx % colors.length]
        } else {
             const eIdx = item.event_type - 1
             color = colors[eIdx % colors.length]
        }
        
        let dash = 'solid'
        // Different dash for different events if multiple events
        // item.event_type ideally 1, 2...
        if (item.event_type === 2) dash = 'dash'
        if (item.event_type === 3) dash = 'dot'
        
        traces.push({
            x: x,
            y: y,
            mode: 'lines',
            name: `${item.group} (Evt ${item.event_type})`,
            line: { color: color, dash: dash, width: 2 }
        })
    })
    
    const layout = {
        title: 'Cumulative Incidence Functions (Aalen-Johansen)',
        xaxis: { title: 'Time' },
        yaxis: { title: 'Cumulative Incidence Probability', range: [0, 1] },
        legend: { x: 1, y: 1 },
        margin: {l:50, r:50, t:50, b:50}
    }
    
    Plotly.newPlot('cif-plot', traces, layout)
}
</script>

<style scoped>
.competing-risks-container {
    height: 100%;
}
.empty-placeholder {
    height: 400px;
    display: flex;
    justify-content: center;
    align-items: center;
}
.help-text {
    font-size: 11px;
    color: #909399;
    line-height: 1.2;
    margin-top: 5px;
}
.methodology-box {
    margin-top: 20px;
    padding: 10px;
    background: #f4f4f5;
    border-radius: 4px;
    font-size: 12px;
    color: #606266;
    line-height: 1.5;
}
.model-header {
    background: #ecf5ff;
    padding: 10px;
    border-left: 4px solid #409EFF;
    margin-bottom: 10px;
}
</style>
