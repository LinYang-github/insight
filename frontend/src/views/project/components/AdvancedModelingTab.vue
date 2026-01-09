<template>
  <div class="advanced-modeling-container">
    <el-tabs v-model="activeTab" class="sub-tabs">
        <!-- Tab 1: RCS -->
        <el-tab-pane label="📈 限制性立方样条 (RCS)" name="rcs">
            <el-row :gutter="20">
                <el-col :span="6">
                    <el-card shadow="never">
                         <el-form label-position="top">
                             <el-form-item label="模型类型 (Model Type)">
                                 <el-select v-model="rcsParams.model_type">
                                     <el-option label="Cox Proportional Hazards" value="cox" />
                                     <el-option label="Logistic Regression" value="logistic" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="结局变量 (Outcome, Y)" required>
                                 <el-select v-model="rcsParams.target" filterable placeholder="Select Outcome">
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="事件状态 (Event, 1/0)" v-if="rcsParams.model_type === 'cox'" required>
                                 <el-select v-model="rcsParams.event_col" filterable placeholder="Select Event">
                                     <el-option v-for="v in binaryVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="暴露变量 (Exposure, X)" required>
                                 <el-select v-model="rcsParams.exposure" filterable placeholder="Continuous Var">
                                     <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="协变量 (Covariates)">
                                 <el-select v-model="rcsParams.covariates" multiple filterable collapse-tags>
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" :disabled="v.name === rcsParams.target || v.name === rcsParams.exposure" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="节点数 (Knots)">
                                 <el-slider v-model="rcsParams.knots" :min="3" :max="7" show-input />
                             </el-form-item>
                             
                             <el-button type="primary" @click="runRCS" :loading="rcsLoading" style="width: 100%">绘制 RCS 曲线</el-button>
                         </el-form>
                    </el-card>
                </el-col>
                
                <el-col :span="18">
                    <div id="rcs-plot" style="width: 100%; height: 600px; background: #fff; border-radius: 4px;"></div>
                    <div v-if="!rcsData" class="placeholder-text">请配置参数并运行以查看结果</div>
                </el-col>
            </el-row>
        </el-tab-pane>
        
        <!-- Tab 2: Subgroup -->
        <el-tab-pane label="🌲 亚组分析 (Subgroup)" name="subgroup">
             <el-row :gutter="20">
                <el-col :span="6">
                    <el-card shadow="never">
                         <el-form label-position="top">
                             <el-form-item label="模型类型">
                                 <el-select v-model="subgroupParams.model_type">
                                     <el-option label="Cox Proportional Hazards" value="cox" />
                                     <el-option label="Logistic Regression" value="logistic" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="结局变量 (Y)" required>
                                 <el-select v-model="subgroupParams.target" filterable>
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="事件 (Event)" v-if="subgroupParams.model_type === 'cox'" required>
                                 <el-select v-model="subgroupParams.event_col" filterable>
                                     <el-option v-for="v in binaryVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="主要暴露 (Main Exposure)" required>
                                 <el-select v-model="subgroupParams.exposure" filterable>
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="亚组变量 (Stratification)" required>
                                 <el-select v-model="subgroupParams.subgroups" multiple filterable collapse-tags placeholder="选择分类变量">
                                     <el-option v-for="v in catVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="其他协变量 (Adjusted)">
                                 <el-select v-model="subgroupParams.covariates" multiple filterable collapse-tags>
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-button type="primary" @click="runSubgroup" :loading="subgroupLoading" style="width: 100%">生成森林图 (Forest Plot)</el-button>
                         </el-form>
                    </el-card>
                </el-col>
                <el-col :span="18">
                     <div id="forest-plot" style="width: 100%; height: 700px; background: #fff; border-radius: 4px;"></div>
                </el-col>
             </el-row>
        </el-tab-pane>
        
        <!-- Tab 3: Competing Risks -->
        <el-tab-pane label="⚠️ 竞争风险 (Competing Risks)" name="cif">
             <el-row :gutter="20">
                <el-col :span="6">
                    <el-card shadow="never">
                         <div class="tip-box" style="margin-bottom: 15px; background: #fdf6ec; padding: 10px; border-radius: 4px; font-size: 12px; color: #e6a23c;">
                            <el-icon><InfoFilled /></el-icon>
                            CIF 比 1-KM 更能准确估计竞争事件发生率。
                            <br/>
                            event=1 为主要事件，event=2+ 为竞争事件。
                         </div>
                         <el-form label-position="top">
                             <el-form-item label="时间变量 (Time)" required>
                                 <el-select v-model="cifParams.time_col" filterable placeholder="Select Time">
                                     <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="事件变量 (Event)" required>
                                 <el-select v-model="cifParams.event_col" filterable placeholder="0=Censor, 1, 2...">
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="分组变量 (Group)">
                                 <el-select v-model="cifParams.group_col" filterable clearable placeholder="可选">
                                     <el-option v-for="v in catVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-button type="primary" @click="runCIF" :loading="cifLoading" style="width: 100%">绘制 CIF 曲线</el-button>
                         </el-form>
                    </el-card>
                </el-col>
                <el-col :span="18">
                     <div id="cif-plot" style="width: 100%; height: 600px; background: #fff; border-radius: 4px;"></div>
                </el-col>
             </el-row>
        </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import Plotly from 'plotly.js-dist-min'
import api from '../../../api/client'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const activeTab = ref('rcs') // 'rcs', 'subgroup', 'cif'

// --- 1. RCS State & Logic ---
const rcsLoading = ref(false)
const rcsData = ref(null)
const rcsParams = ref({
    model_type: 'cox',
    target: '',
    event_col: '',
    exposure: '',
    covariates: [],
    knots: 4
})

const runRCS = async () => {
    rcsLoading.value = true
    try {
        const payload = {
            dataset_id: props.datasetId,
            ...rcsParams.value
        }
        const { data } = await api.post('/advanced/rcs', payload)
        rcsData.value = data
        renderRCS(data)
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'RCS 运行失败')
    } finally {
        rcsLoading.value = false
    }
}

const renderRCS = (res) => {
    const x = res.plot_data.map(d => d.x)
    const y = res.plot_data.map(d => d.y)
    const lower = res.plot_data.map(d => d.lower || d.y) 
    const upper = res.plot_data.map(d => d.upper || d.y)
    
    const traces = [
        {
            x: x, y: upper, type: 'scatter', mode: 'lines', line: { width: 0 }, showlegend: false, hoverinfo: 'skip'
        },
        {
            x: x, y: lower, type: 'scatter', mode: 'lines', line: { width: 0 }, fill: 'tonexty', fillcolor: 'rgba(52, 115, 231, 0.2)', showlegend: false, hoverinfo: 'skip'
        },
        {
            x: x, y: y, type: 'scatter', mode: 'lines', line: { color: '#3b71ca', width: 3 }, name: rcsParams.value.model_type === 'cox' ? 'Hazard Ratio' : 'Odds Ratio'
        },
        {
            x: [Math.min(...x), Math.max(...x)], y: [1, 1], type: 'scatter', mode: 'lines', line: { color: 'gray', dash: 'dash', width: 1 }, name: 'Reference (1.0)', hoverinfo: 'skip'
        }
    ]
    
    const layout = {
        title: `Restricted Cubic Spline (Knots=${rcsParams.value.knots})`,
        xaxis: { title: rcsParams.value.exposure },
        yaxis: { title: rcsParams.value.model_type === 'cox' ? 'Hazard Ratio (95% CI)' : 'Odds Ratio (95% CI)' },
        showlegend: true
    }
    Plotly.newPlot('rcs-plot', traces, layout)
}

// --- 2. Subgroup State & Logic ---
const subgroupLoading = ref(false)
const subgroupParams = ref({
    model_type: 'cox',
    target: '',
    event_col: '',
    exposure: '',
    subgroups: [],
    covariates: []
})

const runSubgroup = async () => {
    subgroupLoading.value = true
    try {
        const payload = {
            dataset_id: props.datasetId,
            ...subgroupParams.value
        }
        const { data } = await api.post('/advanced/subgroup', payload)
        renderForest(data.forest_data)
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '亚组分析失败')
    } finally {
        subgroupLoading.value = false
    }
}

const renderForest = (groups) => {
    let y_labels = []
    
    const traceData = {
        y: [], x: [],
        error_x: { type: 'data', symmetric: false, array: [], arrayminus: [] },
        text: [], marker: { color: [] }
    }
    const annotations = []
    let current_y = 0
    
    groups.forEach(group => {
        current_y += 1
        annotations.push({
            x: 0, y: current_y, xref: 'paper', text: `<b>${group.variable}</b>`, showarrow: false, xanchor: 'left'
        })
        if (group.p_interaction !== null) {
             annotations.push({
                x: 1, y: current_y, xref: 'paper', text: `P-interaction: ${formatP(group.p_interaction)}`, showarrow: false, xanchor: 'right', font: {size: 11, color: 'gray'}
            })
        }
        group.subgroups.forEach(sub => {
            current_y += 1
            if (sub.est) {
                traceData.y.push(current_y)
                traceData.x.push(sub.est)
                traceData.error_x.array.push(sub.upper - sub.est)
                traceData.error_x.arrayminus.push(sub.est - sub.lower)
                
                annotations.push({
                    x: 0, y: current_y, xref: 'paper', text: `   ${sub.level} (N=${sub.n})`, showarrow: false, xanchor: 'left'
                })
                const hrTxt = `${sub.est.toFixed(2)} (${sub.lower.toFixed(2)}-${sub.upper.toFixed(2)}) P=${formatP(sub.p)}`
                annotations.push({
                     x: 0.8, y: current_y, xref: 'paper', text: hrTxt, showarrow: false, xanchor: 'left'
                })
            }
        })
        current_y += 0.5
    })
    
    const trace = {
        x: traceData.x, y: traceData.y, mode: 'markers', type: 'scatter',
        error_x: traceData.error_x, marker: { size: 8, color: '#3b71ca' }, hoverinfo: 'x'
    }
    const layout = {
        title: 'Subgroup Analysis Forest Plot',
        xaxis: { title: 'Hazard Ratio / Odds Ratio (log scale)', type: 'log', zeroline: false },
        yaxis: { showticklabels: false, range: [current_y + 1, 0] },
        shapes: [{ type: 'line', x0: 1, x1: 1, y0: 0, y1: current_y + 1, line: {dash: 'dot', color: 'gray'} }],
        annotations: annotations,
        height: Math.max(600, current_y * 40),
        margin: { l: 200, r: 200 }
    }
    Plotly.newPlot('forest-plot', [trace], layout)
}

// --- 3. CIF Logic ---
const cifLoading = ref(false)
const cifParams = ref({
    time_col: '',
    event_col: '',
    group_col: ''
})

const runCIF = async () => {
    cifLoading.value = true
    try {
        const payload = {
            dataset_id: props.datasetId,
            ...cifParams.value
        }
        const { data } = await api.post('/advanced/cif', payload)
        renderCIF(data)
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'CIF 分析失败')
    } finally {
        cifLoading.value = false
    }
}

const renderCIF = (results) => {
    const traces = []
    results.forEach(res => {
        const x = res.cif_data.map(d => d.x)
        const y = res.cif_data.map(d => d.y)
        traces.push({
            x: x, y: y, mode: 'lines', type: 'scatter',
            name: `${res.group} - Event ${res.event_type}`,
            line: { shape: 'hv' }
        })
    })
    const layout = {
        title: 'Cumulative Incidence Function (CIF)',
        xaxis: { title: cifParams.value.time_col },
        yaxis: { title: 'Probability', range: [0, 1] },
        showlegend: true
    }
    Plotly.newPlot('cif-plot', traces, layout)
}

// Shared
const allVars = computed(() => props.metadata?.variables || [])
const numVars = computed(() => allVars.value.filter(v => ['continuous','float','int'].includes(v.type)))
const binaryVars = computed(() => allVars.value) 
const catVars = computed(() => allVars.value.filter(v => ['object','category','string'].includes(v.type)))

const formatP = (p) => {
    if (p < 0.001) return '<0.001'
    return p.toFixed(3)
}
</script>

<style scoped>
.placeholder-text {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: #909399;
    font-size: 16px;
    background: #f5f7fa;
}
</style>
