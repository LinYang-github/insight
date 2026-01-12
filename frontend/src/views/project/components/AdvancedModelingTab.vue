<template>
  <div class="advanced-modeling-container">
    <el-tabs v-model="activeTab" class="sub-tabs">
        <!-- Tab 1: RCS -->
        <el-tab-pane label="📈 限制性立方样条 (RCS)" name="rcs">
            <el-row :gutter="20">
                <el-col :span="6">
                    <el-card shadow="never">
                        <el-alert
                             title="什么是 RCS?"
                             type="info"
                             :closable="false"
                             show-icon
                             style="margin-bottom: 20px"
                         >
                             <div>
                                 <b>限制性立方样条 (RCS)</b> 用于探索<b>非线性关系</b>（如 J 型曲线）。
                                 <br/>
                                 <li><b>Knots (节点)</b>: 决定曲线灵活性。一般推荐 3 或 4。</li>
                             </div>
                         </el-alert>
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
                                 <el-select v-model="rcsParams.covariates" multiple filterable>
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
                    <el-card shadow="never">
                        <template #header>
                             <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                                <span>RCS Plot</span>
                                <el-button v-if="rcsMethodology" size="small" type="primary" plain @click="copyText(rcsMethodology)">Copy Methods</el-button>
                             </div>
                        </template>
                        <div v-if="processRCSInterpretation()" style="margin-bottom: 10px;">
                            <el-alert :title="processRCSInterpretation()" type="info" :closable="false" show-icon />
                        </div>
                        <div id="rcs-plot" style="width: 100%; height: 600px; background: #fff;"></div>
                        <div v-if="!rcsData" class="placeholder-text" style="height: 100px;">请配置参数并运行以查看结果</div>
                    </el-card>
                </el-col>
            </el-row>
        </el-tab-pane>
        
        <!-- Tab 2: Subgroup -->
        <el-tab-pane label="🌲 亚组分析 (Subgroup)" name="subgroup">
             <el-row :gutter="20">
                <el-col :span="6">
                    <el-card shadow="never">
                        <el-alert
                             title="交互作用检验"
                             type="success"
                             :closable="false"
                             show-icon
                             style="margin-bottom: 20px"
                         >
                             <div>
                                 <b>P-interaction &lt; 0.05</b> 意味着治疗效果在不同亚组间存在显著差异（效应修饰）。
                                 <br/>
                                 例如：新药在男性中有效 (HR&lt;1)，但在女性中无效 (HR=1)。
                             </div>
                         </el-alert>
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
                                 <el-select v-model="subgroupParams.subgroups" multiple filterable placeholder="选择分类变量">
                                     <el-option v-for="v in catVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="其他协变量 (Adjusted)">
                                 <el-select v-model="subgroupParams.covariates" multiple filterable>
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-button type="primary" @click="runSubgroup" :loading="subgroupLoading" style="width: 100%">生成森林图 (Forest Plot)</el-button>
                         </el-form>
                    </el-card>
                </el-col>
                <el-col :span="18">
                    <el-card shadow="never">
                        <template #header>
                            <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                                <span>Forest Plot</span>
                                <el-button v-if="subMethodology" size="small" type="primary" plain @click="copyText(subMethodology)">Copy Methods</el-button>
                            </div>
                        </template>
                        <div id="forest-plot" style="width: 100%; height: 700px; background: #fff;"></div>
                    </el-card>
                </el-col>
             </el-row>
        </el-tab-pane>
        
        <!-- Tab 3: Competing Risks -->
        <el-tab-pane label="⚠️ 竞争风险 (Competing Risks)" name="cif">
             <el-row :gutter="20">
                <el-col :span="6">
                    <el-card shadow="never">
                         <el-alert
                             title="为什么不用 Kaplan-Meier?"
                             type="warning"
                             :closable="false"
                             show-icon
                             style="margin-bottom: 20px"
                         >
                            <div>
                                当存在<b>竞争事件</b>（如死于其他原因）时，KM 会高估主要事件的风险。
                                <br/>
                                此时应使用 <b>CIF (累积发生率)</b>。
                                <br/>
                                <i>注: Event 1=主要事件, 2=竞争事件, 0=删失。</i>
                            </div>
                         </el-alert>
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
                    <el-card shadow="never">
                        <template #header>
                            <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                                <span>CIF Plot</span>
                                <el-button v-if="cifMethodology" size="small" type="primary" plain @click="copyText(cifMethodology)">Copy Methods</el-button>
                            </div>
                        </template>
                        <div id="cif-plot" style="width: 100%; height: 600px; background: #fff;"></div>
                    </el-card>
                </el-col>
             </el-row>
        </el-tab-pane>

        <!-- Tab 4: Nomogram -->
        <el-tab-pane label="🏥 列线图 (Nomogram)" name="nomogram">
             <el-row :gutter="20">
                <el-col :span="6">
                    <el-card shadow="never">
                         <el-alert
                             title="临床应用"
                             type="success"
                             :closable="false"
                             show-icon
                             style="margin-bottom: 20px"
                         >
                             <div>
                                 <b>列线图 (Nomogram)</b> 将复杂的回归模型可视化为简单的评分系统。
                             </div>
                         </el-alert>
                         <el-form label-position="top">
                             <el-form-item label="模型类型">
                                 <el-select v-model="nomoParams.model_type">
                                     <el-option label="Cox Proportional Hazards" value="cox" />
                                     <el-option label="Logistic Regression" value="logistic" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="结局变量 (Y)" required>
                                 <el-select v-model="nomoParams.target" filterable>
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="事件 (Event)" v-if="nomoParams.model_type === 'cox'" required>
                                 <el-select v-model="nomoParams.event_col" filterable>
                                     <el-option v-for="v in binaryVars" :key="v.name" :label="v.name" :value="v.name" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-form-item label="预测因子 (Predictors)" required>
                                 <el-select v-model="nomoParams.predictors" multiple filterable>
                                     <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" :disabled="v.name === nomoParams.target" />
                                 </el-select>
                             </el-form-item>
                             
                             <el-button type="primary" @click="runNomogram" :loading="nomoLoading" style="width: 100%">生成列线图</el-button>
                         </el-form>
                    </el-card>
                </el-col>
                <el-col :span="18">
                     <!-- Web Calculator -->
                     <el-card shadow="hover" v-if="nomoData" style="margin-bottom: 20px;">
                        <template #header>
                             <div class="card-header">
                                 <span>🌐 Web Risk Calculator</span>
                             </div>
                        </template>
                        <el-form :inline="true">
                            <el-form-item v-for="v in nomoData.variables" :key="v.name" :label="v.name">
                                <el-input-number v-model="calcValues[v.name]" :min="v.min" :max="v.max" size="small" />
                            </el-form-item>
                        </el-form>
                        <div style="background: #f0f9eb; padding: 10px; border-radius: 4px; text-align: center;">
                            <span style="font-size: 16px; color: #67c23a; font-weight: bold;">
                                预测风险 (Predicted Probability): {{ (calculatedRisk * 100).toFixed(2) }}%
                            </span>
                        </div>
                     </el-card>
                     
                     <div id="nomogram-plot" style="width: 100%; height: 600px; background: #fff; border-radius: 4px;"></div>
                     <div style="margin-top: 10px; text-align: right;" v-if="nomoMethodology">
                         <el-button size="small" type="primary" plain @click="copyText(nomoMethodology)">Copy Methods</el-button>
                     </div>
                </el-col>
             </el-row>
        </el-tab-pane>

        <!-- Tab 5: Model Comparison -->
        <el-tab-pane label="📊 模型对比 (Comparison)" name="comparison">
            <model-comparison-tab :dataset-id="datasetId" :metadata="metadata" />
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
import ModelComparisonTab from './ModelComparisonTab.vue'

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
        rcsMethodology.value = data.methodology
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
        title: `Restricted Cubic Spline (Knots=${rcsParams.value.knots}) with 95% CI`,
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
        subMethodology.value = data.methodology
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
        cifMethodology.value = data.methodology
        renderCIF(data.cif_data)
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

// --- 4. Nomogram Logic ---
const nomoLoading = ref(false)
const nomoData = ref(null)
const nomoParams = ref({
    model_type: 'cox',
    target: '',
    event_col: '',
    predictors: []
})
const calcValues = ref({})

// Methodologies
const rcsMethodology = ref('')
const subMethodology = ref('')
const cifMethodology = ref('')
const nomoMethodology = ref('')

const copyText = (text) => {
    navigator.clipboard.writeText(text).then(() => {
        ElMessage.success('Copied methodology')
    })
}

const processRCSInterpretation = () => {
    return rcsData.value?.interpretation
}

const runNomogram = async () => {
    nomoLoading.value = true
    try {
        const payload = {
            dataset_id: props.datasetId,
            ...nomoParams.value
        }
        const { data } = await api.post('/advanced/nomogram', payload)

        nomoData.value = data
        nomoMethodology.value = data.methodology
        
        // Init calculator
        const initVals = {}
        data.variables.forEach(v => {
            initVals[v.name] = v.min // Default to min
        })
        calcValues.value = initVals
        
        renderNomogram(data)
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'Nomogram 生成失败')
    } finally {
        nomoLoading.value = false
    }
}

const calculatedRisk = computed(() => {
    if (!nomoData.value) return 0
    let totalPoints = 0
    
    // Calculate Total Points
    // Need scaling info?
    // Backend returned 'points_mapping' for ticks.
    // We need the formula: Points = (Val - Min) * Coef * Scaling + Min_C?
    // Let's infer from the mapping linearly.
    // simpler: The backend logic was:
    // Pts = (Val * Coef - Min_C) * scaling
    // But we don't have scaling factor directly exposed easily unless we parse mapping.
    // Let's use linear interpolation from 'points_mapping'.
    
    nomoData.value.variables.forEach(v => {
        const val = calcValues.value[v.name] || v.min
        // Find mapping
        // It's linear. Just take 2 points.
        const p1 = v.points_mapping[0]
        const p2 = v.points_mapping[v.points_mapping.length - 1]
        
        if (Math.abs(p2.val - p1.val) < 1e-9) {
             totalPoints += 0
        } else {
             const slope = (p2.pts - p1.pts) / (p2.val - p1.val)
             const pts = p1.pts + slope * (val - p1.val)
             totalPoints += pts
        }
    })
    
    // Map Total Points to Risk
    // 'risk_table' in nomoData
    // find nearest or interp
    const risks = nomoData.value.risk_table
    if (!risks || risks.length === 0) return 0
    
    // risks is sorted by points (0 to max)
    // simple linear search or interp
    // find i where risks[i].points <= totalPoints < risks[i+1].points
    
    if (totalPoints <= risks[0].points) return risks[0].risk
    if (totalPoints >= risks[risks.length-1].points) return risks[risks.length-1].risk
    
    for (let i = 0; i < risks.length - 1; i++) {
        if (totalPoints >= risks[i].points && totalPoints <= risks[i+1].points) {
            const r1 = risks[i]
            const r2 = risks[i+1]
            const ratio = (totalPoints - r1.points) / (r2.points - r1.points)
            return r1.risk + ratio * (r2.risk - r1.risk)
        }
    }
    return 0
})

const renderNomogram = (res) => {
    // Draw using Shapes
    const shapes = []
    const annotations = []
    
    let current_y = 1
    const Y_STEP = 0.15
    
    // 1. Variable Scales
    res.variables.forEach(v => {
        // Line
        shapes.push({
            type: 'line',
            x0: 0, x1: 100, // Normalized 0-100 points
            y0: current_y, y1: current_y,
            line: { color: 'black', width: 2 }
        })
        
        // Label
        annotations.push({
            x: -5, y: current_y, xref: 'x', yref: 'y',
            text: `<b>${v.name}</b>`, showarrow: false, xanchor: 'right'
        })
        
        // Ticks
        v.points_mapping.forEach(m => {
             shapes.push({
                type: 'line', x0: m.pts, x1: m.pts, y0: current_y, y1: current_y + 0.02,
                line: { color: 'black', width: 1 }
             })
             annotations.push({
                 x: m.pts, y: current_y + 0.05, xref: 'x', yref: 'y',
                 text: m.val.toFixed(1), showarrow: false, font: {size: 10}
             })
        })
        
        current_y -= Y_STEP
    })
    
    // 2. Total Points Scale
    current_y -= Y_STEP
    shapes.push({
        type: 'line', x0: 0, x1: 100, y0: current_y, y1: current_y,
        line: { color: 'black', width: 2 }
    })
    annotations.push({
        x: -5, y: current_y, xref: 'x', yref: 'y',
        text: `<b>Total Points</b>`, showarrow: false, xanchor: 'right'
    })
    // Ticks usually 0 to ??? Backend normalized to 100 max variable points? 
    // Wait, total max points > 100 probably.
    // The backend `points_mapping` already normalized each var to 0-100 scale relative to max effect?
    // YES. `total_max_points` in backend is the sum of max points.
    // We need to know the Total Points Range to draw the detailed scale.
    // Backend `risk_table` has points range 0 to total_max.
    // We should map this 0-total_max to 0-100 visual width? Or just show 0-total_max.
    // Let's use the `risk_table` range.
    const max_total_pts = res.risk_table[res.risk_table.length-1].points
    
    // Draw ticks for Total Points (e.g. every 20 or 50)
    const step = max_total_pts / 10
    for(let p=0; p<=max_total_pts; p+=step) {
        // Where is p on the x-axis?
        // We need to align the visual columns.
        // Actually, the Nomogram aligns everything standardly.
        // If var1 0-100 pts takes 100 pixel width.
        // Then Total points 0-SumMax takes SumMax pixel width.
        // So we should scale everything to the same physical unit.
        // Let's simply map "Points" directly to X-axis value.
        // So X-axis is "Points".
        shapes.push({
            type: 'line', x0: p, x1: p, y0: current_y, y1: current_y + 0.02,
            line: { color: 'black', width: 1 }
        })
        annotations.push({
             x: p, y: current_y + 0.05, xref: 'x', yref: 'y',
             text: p.toFixed(0), showarrow: false, font: {size: 10}
        })
    }
    
    // 3. Risk Scale
    current_y -= Y_STEP
    shapes.push({
        type: 'line', x0: 0, x1: max_total_pts, y0: current_y, y1: current_y,
        line: { color: 'black', width: 2 }
    })
    annotations.push({
        x: -5, y: current_y, xref: 'x', yref: 'y',
        text: `<b>Linear Predictor</b>`, showarrow: false, xanchor: 'right' // or Risk
    })
    
    // Risk Ticks mapping
    // We iterate risk levels (0.1, 0.2 ... 0.9) and find corresponding points
    const risk_levels = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
    current_y -= Y_STEP
    
    shapes.push({
        type: 'line', x0: 0, x1: max_total_pts, y0: current_y, y1: current_y,
        line: { color: 'black', width: 2 }
    })
    annotations.push({
        x: -5, y: current_y, xref: 'x', yref: 'y',
        text: `<b>Risk Probability</b>`, showarrow: false, xanchor: 'right'
    })
    
    risk_levels.forEach(r => {
        // Reverse map Risk -> Points using risk_table
        // risk_table is monotonic
        const match = res.risk_table.find(item => item.risk >= r)
        if (match) {
            const x_pos = match.points
             shapes.push({
                type: 'line', x0: x_pos, x1: x_pos, y0: current_y, y1: current_y + 0.02,
                line: { color: 'black', width: 1 }
             })
             annotations.push({
                 x: x_pos, y: current_y + 0.05, xref: 'x', yref: 'y',
                 text: r.toString(), showarrow: false, font: {size: 10}
             })
        }
    })
    
    const layout = {
        title: 'Nomogram',
        xaxis: { visible: false, range: [-20, max_total_pts * 1.1] }, // Add padding
        yaxis: { visible: false, range: [current_y - 0.2, 1.2] },
        shapes: shapes,
        annotations: annotations,
        height: 600,
        margin: { l: 150, r: 50, t: 50, b: 50 }
    }
    
    Plotly.newPlot('nomogram-plot', [], layout)
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
