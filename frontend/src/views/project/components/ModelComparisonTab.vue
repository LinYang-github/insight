<template>
    <div class="model-comparison-container">
        <el-row :gutter="20">
            <!-- 左侧：模型配置面板 -->
            <el-col :span="8">
                <el-card shadow="never" class="config-card">
                    <template #header>
                        <div class="card-header">
                            <span>🛠️ 模型对比配置 (Model Builder)</span>
                        </div>
                    </template>
                    
                    <el-alert
                        title="增量价值分析 (Incremental Value)"
                        type="info"
                        :closable="false"
                        show-icon
                        style="margin-bottom: 20px"
                    >
                        <div>
                            比较多个模型在<b>完全相同样本 (Same N)</b> 上的表现。
                            <br/>
                            用于评估新加入变量是否显著提升了模型的预测效能（AUC/NRI/IDI）。
                        </div>
                    </el-alert>

                    <el-form label-position="top">
                        <el-form-item label="模型类型 (Model Type)">
                            <el-radio-group v-model="modelType">
                                <el-radio-button value="logistic">Logistic 回归</el-radio-button>
                                <el-radio-button value="cox">Cox 生存回归</el-radio-button>
                            </el-radio-group>
                        </el-form-item>

                        <el-form-item :label="modelType === 'cox' ? '随访时间 (Time Variable)' : '结局变量 (Target Outcome)'" required>
                            <el-select v-model="target" filterable placeholder="选择变量">
                                <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>

                        <el-form-item v-if="modelType === 'cox'" label="事件状态 (Event Status)" required>
                            <el-select v-model="eventCol" filterable placeholder="选择事件列 (1=发生)">
                                <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>

                        <div class="model-list">
                            <label class="el-form-item__label">模型组合 (Model Configs)</label>
                            
                            <div v-for="(model, index) in modelConfigs" :key="index" class="model-row">
                                <div class="model-header">
                                    <span class="model-index">模型 {{ index + 1 }}</span>
                                    <el-button type="danger" link size="small" @click="removeModel(index)" v-if="modelConfigs.length > 2">
                                        删除
                                    </el-button>
                                </div>
                                
                                <el-input v-model="model.name" placeholder="模型名称 (如: 基础模型)" style="margin-bottom: 5px" />
                                
                                <el-select v-model="model.features" multiple filterable placeholder="选择纳入变量 (Features)">
                                    <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" :disabled="v.name === target" />
                                </el-select>
                            </div>
                        </div>

                        <el-button type="default" style="width: 100%; margin-top: 10px; margin-bottom: 20px" @click="addModel">
                            + 添加模型
                        </el-button>

                        <el-button type="primary" size="large" style="width: 100%" @click="runComparison" :loading="loading" :disabled="!isValid">
                            🚀 开始对比分析 (Run)
                        </el-button>
                    </el-form>
                </el-card>
            </el-col>

            <!-- 右侧：可视化结果 -->
            <el-col :span="16">
                <div class="viz-area">
                    <div id="comparison-plot" style="width: 100%; height: 500px; background: #fff;"></div>
                    <div v-if="!results" class="placeholder-overlay">
                        配置完成并点击运行以查看 ROC 曲线对比
                    </div>
                </div>

                <!-- 结果统计表 -->
                <el-card shadow="never" style="margin-top: 20px" v-if="results">
                    <template #header>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>统计对比结果 (Statistics)</span>
                            <el-button v-if="methodology" size="small" type="primary" plain @click="copyText">复制研究方法</el-button>
                        </div>
                        
                        <!-- 时间点选择器 (Cox专用) -->
                        <div v-if="modelType === 'cox' && availableTimePoints.length > 0" style="margin-top: 10px; display: flex; align-items: center; justify-content: flex-end;">
                             <span style="font-size: 12px; margin-right: 15px; color: gray">预测截止时间点:</span>
                             <el-radio-group v-model="selectedTimePoint" size="small">
                                 <el-radio-button v-for="t in availableTimePoints" :key="t" :label="t" :value="t">
                                     {{ t }} ({{ timeUnit }})
                                 </el-radio-button>
                             </el-radio-group>
                        </div>
                    </template>

                    <el-table :data="tableData" stripe border size="small">
                        <el-table-column prop="name" label="模型名称" width="130" fixed="left" />
                        
                        <el-table-column label="C-index / AUC (95% CI)" width="180">
                            <template #default="scope">
                                <span style="font-weight: bold">{{ scope.row.auc }}</span> 
                                <span style="color: gray; font-size: 11px; margin-left: 4px">{{ scope.row.auc_ci }}</span>
                            </template>
                        </el-table-column>
                        
                        <el-table-column label="P 值 (模型提升)" width="120">
                            <template #header>
                                模型提升 P 值
                                <el-tooltip content="基于似然比检验 (LRT)。评估相比基础模型，新模型是否带来了统计学显著的性能提升。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                <span v-if="scope.row.p_lrt !== undefined && scope.row.p_lrt !== '-'">
                                     <span :style="{fontWeight: scope.row.p_lrt < 0.05 ? 'bold' : 'normal', color: scope.row.p_lrt < 0.05 ? 'red' : 'black'}">
                                        {{ scope.row.p_lrt < 0.001 ? '< 0.001' : scope.row.p_lrt.toFixed(3) }}
                                     </span>
                                </span>
                                <span v-else style="color: #ccc">-</span>
                            </template>
                        </el-table-column>
                        
                        <el-table-column label="AIC (变化量)" width="110">
                            <template #header>
                                AIC (变化)
                                <el-tooltip content="赤池信息准则。数值越低模型越优。负值代表相比前一模型拟合度提升。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                {{ scope.row.aic }}
                                <div v-if="scope.row.delta_aic !== undefined" :style="{color: scope.row.delta_aic < -2 ? 'green' : (scope.row.delta_aic > 2 ? 'red' : 'gray'), fontSize: '11px'}">
                                     ({{ scope.row.delta_aic > 0 ? '+' : '' }}{{ scope.row.delta_aic.toFixed(1) }})
                                </div>
                            </template>
                        </el-table-column>

                        <el-table-column label="NRI (Estimate/P)" align="center" width="160">
                            <template #header>
                                NRI (改善指数)
                                <el-tooltip content="净重分类改善指数。>0 表示新模型能更准确地划分风险组。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                <div v-if="scope.row.nri !== '-'" :style="{color: parseFloat(scope.row.nri) > 0 ? 'green' : 'red', fontWeight: 'bold'}">
                                    {{ scope.row.nri }}
                                </div>
                                <div v-if="scope.row.nri_p" style="font-size: 11px; color: gray">
                                    P={{ scope.row.nri_p }}
                                </div>
                                <span v-else-if="scope.row.nri === '-'">-</span>
                            </template>
                        </el-table-column>

                        <el-table-column label="IDI (Estimate/P)" align="center" width="160">
                            <template #header>
                                IDI (判别改进)
                                <el-tooltip content="综合判别改善指数。反映整体预测概率的改善程度。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                <div v-if="scope.row.idi !== '-'" :style="{color: parseFloat(scope.row.idi) > 0 ? 'green' : 'red', fontWeight: 'bold'}">
                                    {{ scope.row.idi }}
                                </div>
                                <div v-if="scope.row.idi_p" style="font-size: 11px; color: gray">
                                    P={{ scope.row.idi_p }}
                                </div>
                                <span v-else-if="scope.row.idi === '-'">-</span>
                            </template>
                        </el-table-column>

                        <el-table-column prop="n" label="样本量" width="80" />
                        <el-table-column label="納入变量" min-width="150">
                             <template #default="scope">
                                 <el-tag v-for="f in scope.row.features" :key="f" size="small" style="margin-right: 4px; margin-bottom: 2px">{{ f }}</el-tag>
                             </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import AdvancedModelingService from '@/services/advanced_modeling_service'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

// State
const modelType = ref('cox') // logistic, cox
const target = ref('')
const eventCol = ref('')
const loading = ref(false)
const results = ref(null)
const selectedTimePoint = ref(null)

// Computed
const allVars = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables
})

const modelConfigs = ref([
    { name: 'Model A (Base)', features: [] },
    { name: 'Model B (New)', features: [] }
])

const availableTimePoints = computed(() => {
    if (!results.value || results.value.length === 0) return []
    // Get from first model's metrics
    const metrics = results.value[0].metrics
    if (metrics && metrics.available_time_points) {
        return metrics.available_time_points
    }
    return []
})

const timeUnit = computed(() => {
    if (!results.value || results.value.length === 0) return 'months'
    return results.value[0].metrics.time_unit || 'months'
})

// Auto-select first time point when available
const updateSelectedTimePoint = () => {
    if (availableTimePoints.value.length > 0) {
        // Default to the middle or last point? Usually median or user pref.
        // Let's select the first one for now, or maintain if exists
        if (!selectedTimePoint.value || !availableTimePoints.value.includes(selectedTimePoint.value)) {
            selectedTimePoint.value = availableTimePoints.value[0]
        }
    }
}

watch(results, () => {
    updateSelectedTimePoint()
    nextTick(() => {
        renderPlot()
    })
})

watch(selectedTimePoint, () => {
    renderPlot()
})

const isValid = computed(() => {
    if (!target.value) return false
    if (modelType.value === 'cox' && !eventCol.value) return false
    if (modelConfigs.value.length < 2) return false
    // Check at least one feature
    return modelConfigs.value.every(m => m.features.length > 0)
})

// Actions
const addModel = () => {
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    const idx = modelConfigs.value.length
    modelConfigs.value.push({
        name: `Model ${letters[idx % 26]}`,
        features: []
    })
}

const removeModel = (index) => {
    modelConfigs.value.splice(index, 1)
}

const runComparison = async () => {
    loading.value = true
    try {
        const payload = {
            dataset_id: props.datasetId,
            model_type: modelType.value,
            target: target.value,
            event_col: modelType.value === 'cox' ? eventCol.value : undefined,
            models: modelConfigs.value
        }
        
        const res = await AdvancedModelingService.compareModels(payload)
        if (res.error) throw new Error(res.error)
        
        results.value = res.comparison_data
        ElMessage.success('Comparison Complete!')
        
    } catch (e) {
        ElMessage.error(e.message || 'Comparison failed')
        console.error(e)
    } finally {
        loading.value = false
    }
}

const methodology = computed(() => {
    if (!results.value) return ''
    if (modelType.value === 'logistic') return "采用 Logistic 回归模型进行对比，通过 DeLong 检验评估 AUC 差异，并计算 NRI 和 IDI 指标评估增量价值。"
    return "采用 Cox 生存模型进行对比，评估随访时间点上的时间依赖性 AUC、NRI 和 IDI，并通过似然比检验 (LRT) 评估模型整体提升。"
})

const timeUnitDisplayName = computed(() => {
    const unit = timeUnit.value
    if (unit === 'months') return '月'
    if (unit === 'days') return '天'
    if (unit === 'years') return '年'
    return unit
})

const copyText = () => {
    navigator.clipboard.writeText(methodology.value)
    ElMessage.success('Methodology copied')
}

// Table Data (Computed for Display)
const tableData = computed(() => {
    if (!results.value || !Array.isArray(results.value)) return []
    
    return results.value.map(r => {
        const m = r.metrics || {}
        const base = {
            name: r.name || 'Unknown Model',
            aic: m.aic !== undefined ? m.aic.toFixed(1) : '-',
            bic: m.bic !== undefined ? m.bic.toFixed(1) : '-',
            p_lrt: m.p_lrt !== undefined ? m.p_lrt : '-',
            delta_aic: m.delta_aic !== undefined ? m.delta_aic : undefined,
            delta_bic: m.delta_bic !== undefined ? m.delta_bic : undefined,
            n: m.n || '-',
            features: r.features || []
        }
        
        if (modelType.value === 'cox') {
            const t = selectedTimePoint.value
            if (t && m.time_dependent && m.time_dependent[t]) {
                const tm = m.time_dependent[t]
                return {
                    ...base,
                    auc: tm.auc !== undefined ? tm.auc.toFixed(3) : '-',
                    auc_ci: tm.auc_ci || '-',
                    nri: tm.nri !== undefined ? tm.nri.toFixed(3) : '-',
                    nri_p: tm.nri_p !== undefined ? (tm.nri_p < 0.001 ? '<0.001' : tm.nri_p.toFixed(3)) : '-',
                    idi: tm.idi !== undefined ? tm.idi.toFixed(3) : '-',
                    idi_p: tm.idi_p !== undefined ? (tm.idi_p < 0.001 ? '<0.001' : tm.idi_p.toFixed(3)) : '-'
                }
            } else {
                 return { ...base, auc: '-', auc_ci: '-', nri: '-', nri_p: '-', idi: '-', idi_p: '-' }
            }
        } else {
            // Logistic
            return {
                ...base,
                auc: m.auc !== undefined ? m.auc.toFixed(3) : '-',
                auc_ci: m.auc_ci || '-',
                nri: m.nri !== undefined ? m.nri.toFixed(3) : '-',
                nri_p: m.nri_p !== undefined ? (m.nri_p < 0.001 ? '<0.001' : m.nri_p.toFixed(3)) : '-',
                idi: m.idi !== undefined ? m.idi.toFixed(3) : '-',
                idi_p: m.idi_p !== undefined ? (m.idi_p < 0.001 ? '<0.001' : m.idi_p.toFixed(3)) : '-'
            }
        }
    })
})

// Plotting
const renderPlot = () => {
    const el = document.getElementById('comparison-plot')
    if (!el || !results.value) return
    
    const traces = []
    
    results.value.forEach(r => {
        let rocData = null
        if (modelType.value === 'logistic') {
            rocData = r.roc_data
        } else {
            // Cox Time Dependent ROC
            const t = selectedTimePoint.value
            if (t && r.metrics.time_dependent && r.metrics.time_dependent[t]) {
                rocData = r.metrics.time_dependent[t].roc_data
            }
        }
        
        if (rocData) {
            traces.push({
                x: rocData.map(d => d.fpr),
                y: rocData.map(d => d.tpr),
                mode: 'lines',
                name: `${r.name} (AUC=${r.metrics.time_dependent && selectedTimePoint.value ? r.metrics.time_dependent[selectedTimePoint.value].auc.toFixed(3) : r.metrics.auc.toFixed(3)})`
            })
        }
    })
    
    // Diagonal
    traces.push({
        x: [0, 1],
        y: [0, 1],
        mode: 'lines',
        line: { dash: 'dash', color: 'gray' },
        showlegend: false
    })
    
    const title = modelType.value === 'cox' 
        ? `Time-Dependent ROC Comparison (t=${selectedTimePoint.value} ${timeUnit.value})`
        : 'ROC Curve Comparison'

    const layout = {
        title: title,
        xaxis: { title: '1 - Specificity (FPR)', range: [0, 1] },
        yaxis: { title: 'Sensitivity (TPR)', range: [0, 1] },
        legend: { x: 0.6, y: 0.1 },
        margin: { l: 50, r: 20, t: 40, b: 40 }
    }
    
    Plotly.newPlot(el, traces, layout)
}
</script>

<style scoped>
.model-comparison-container {
    height: 100%;
    padding: 20px;
    background: #f5f7fa;
}
.config-card {
    height: 100%;
    overflow-y: auto;
}
.model-row {
    background: #f8f9fa;
    padding: 10px;
    border-radius: 4px;
    margin-bottom: 10px;
    border: 1px solid #ebeef5;
}
.model-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
}
.model-index {
    font-weight: bold;
    font-size: 12px;
    color: #909399;
}
.viz-area {
    background: white;
    padding: 20px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    position: relative;
    min-height: 500px;
}
.placeholder-overlay {
    position: absolute;
    color: #909399;
    margin-left: 4px;
}
</style>
