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
                    <el-tabs v-model="activeVizTab" type="border-card" @tab-change="handleTabChange">
                        <el-tab-pane label="ROC 曲线 (区分度)" name="roc">
                            <div id="comparison-plot" style="width: 100%; height: 500px;"></div>
                        </el-tab-pane>
                        <el-tab-pane label="校准曲线 (校准度)" name="calibration">
                            <div id="calibration-plot" style="width: 100%; height: 500px;"></div>
                        </el-tab-pane>
                        <el-tab-pane label="DCA 决策曲线 (获益)" name="dca">
                            <div id="dca-plot" style="width: 100%; height: 500px;"></div>
                        </el-tab-pane>
                    </el-tabs>
                    <div v-if="!results" class="placeholder-overlay" style="top: 60px">
                        配置完成并点击运行以查看模型表现
                    </div>
                </div>

                <!-- 结果统计表 -->
                <el-card shadow="never" style="margin-top: 20px" v-if="results">
                    <template #header>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>统计对比结果 (Statistics)</span>
                            <div>
                                <el-button v-if="results" size="small" type="success" plain @click="copyTableData" style="margin-right: 10px;">
                                    <el-icon style="margin-right: 4px"><DocumentCopy /></el-icon> 复制表格数据
                                </el-button>
                                <el-button v-if="methodology" size="small" type="primary" plain @click="copyText">复制研究方法</el-button>
                            </div>
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
                        
                        <el-table-column label="C-index / AUC (95% CI)" width="190">
                            <template #header>
                                C-index / AUC
                                <el-tooltip content="括号内为 95% 置信区间。下方 P 值检验 H0: AUC=0.5 (即模型是否优于随机猜测)。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                <span style="font-weight: bold">{{ scope.row.auc }}</span> 
                                <span style="color: gray; font-size: 11px; margin-left: 4px">{{ scope.row.auc_ci }}</span>
                                <div v-if="scope.row.auc_p && scope.row.auc_p !== '-'" style="font-size: 11px; color: #909399">
                                    P(vs 0.5) {{ scope.row.auc_p.toString().startsWith('<') ? scope.row.auc_p : '= ' + scope.row.auc_p }}
                                </div>
                            </template>
                        </el-table-column>
                        
                        <el-table-column label="P 值 (模型提升)" width="130">
                            <template #header>
                                P (vs Base)
                                <el-tooltip content="包含两种检验：LRT (似然比检验) 和 Delong Test (ROC 差异检验)。用于评估相比基础模型，新模型是否带来了显著提升。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                <div v-if="scope.row.p_lrt !== undefined && scope.row.p_lrt !== '-'">
                                     <div style="font-size: 11px; color: #606266">LRT:</div>
                                     <span :style="{fontWeight: scope.row.p_lrt < 0.05 ? 'bold' : 'normal', color: scope.row.p_lrt < 0.05 ? 'red' : 'black'}">
                                        {{ scope.row.p_lrt < 0.001 ? '< 0.001' : scope.row.p_lrt.toFixed(3) }}
                                     </span>
                                </div>
                                <div v-if="scope.row.p_delong !== undefined && scope.row.p_delong !== '-'" style="margin-top: 4px; border-top: 1px dashed #eee; padding-top: 2px">
                                     <div style="font-size: 11px; color: #606266">Delong:</div>
                                     <span :style="{fontWeight: scope.row.p_delong < 0.05 ? 'bold' : 'normal', color: scope.row.p_delong < 0.05 ? '#E6A23C' : 'black'}">
                                        {{ scope.row.p_delong < 0.001 ? '< 0.001' : scope.row.p_delong.toFixed(3) }}
                                     </span>
                                </div>
                                <span v-if="(scope.row.p_lrt === undefined || scope.row.p_lrt === '-') && (scope.row.p_delong === undefined || scope.row.p_delong === '-')" style="color: #ccc">-</span>
                            </template>
                        </el-table-column>
                        
                        <el-table-column label="AIC (变化量)" width="110">
                            <template #header>
                                AIC (Change)
                                <el-tooltip content="赤池信息准则。数值越低模型越优。绿色负值代表相比前一模型拟合度提升。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                {{ scope.row.aic }}
                                <div v-if="scope.row.delta_aic !== undefined" :style="{color: scope.row.delta_aic < -2 ? 'green' : (scope.row.delta_aic > 2 ? 'red' : 'gray'), fontSize: '11px', fontWeight: 'bold'}">
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
                                <template v-if="scope.row.nri !== '-'">
                                    <div :style="{color: parseFloat(scope.row.nri) > 0 ? '#2E7D32' : '#D32F2F', fontWeight: 'bold'}">
                                        {{ scope.row.nri }}
                                    </div>
                                    <div style="font-size: 11px; color: #606266; margin-bottom: 2px;">
                                        ({{ scope.row.nri_ci }})
                                    </div>
                                    <div v-if="scope.row.nri_p && scope.row.nri_p !== '-'" style="font-size: 11px; color: #909399">
                                        P={{ scope.row.nri_p }}
                                    </div>
                                </template>
                                <span v-else style="color: #ccc">-</span>
                            </template>
                        </el-table-column>

                        <el-table-column label="IDI (Estimate/P)" align="center" width="160">
                            <template #header>
                                IDI (判别改进)
                                <el-tooltip content="综合判别改善指数。反映整体预测概率的改善程度。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                <template v-if="scope.row.idi !== '-'">
                                    <div :style="{color: parseFloat(scope.row.idi) > 0 ? '#2E7D32' : '#D32F2F', fontWeight: 'bold'}">
                                        {{ scope.row.idi }}
                                    </div>
                                    <div style="font-size: 11px; color: #606266; margin-bottom: 2px;">
                                        ({{ scope.row.idi_ci }})
                                    </div>
                                    <div v-if="scope.row.idi_p && scope.row.idi_p !== '-'" style="font-size: 11px; color: #909399">
                                        P={{ scope.row.idi_p }}
                                    </div>
                                </template>
                                <span v-else style="color: #ccc">-</span>
                            </template>
                        </el-table-column>

                        <!-- Detailed Metrics -->
                        <el-table-column label="Sens (灵敏度)" width="150" align="center">
                            <template #header>Sens (灵敏度)<el-tooltip content="Sensitivity (Recall)" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip></template>
                            <template #default="{row}">{{ row.sensitivity_ci || '-' }}</template>
                        </el-table-column>
                        <el-table-column label="Spec (特异度)" width="150" align="center">
                            <template #header>Spec (特异度)<el-tooltip content="Specificity" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip></template>
                            <template #default="{row}">{{ row.specificity_ci || '-' }}</template>
                        </el-table-column>
                        <el-table-column label="PPV (阳性预测)" width="150" align="center">
                             <template #header>PPV (阳性预测)<el-tooltip content="Positive Predictive Value" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip></template>
                            <template #default="{row}">{{ row.ppv_ci || '-' }}</template>
                        </el-table-column>
                         <el-table-column label="NPV (阴性预测)" width="150" align="center">
                             <template #header>NPV (阴性预测)<el-tooltip content="Negative Predictive Value" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip></template>
                            <template #default="{row}">{{ row.npv_ci || '-' }}</template>
                        </el-table-column>
                        <el-table-column prop="youden" label="Youden" width="90" align="center" />
                        <el-table-column prop="cutoff" label="Cutoff" width="90" align="center" />
                        <el-table-column label="Brier" width="90" align="center">
                            <template #default="{row}">
                                <div v-if="row.brier && row.brier !== '-'">
                                    {{ row.brier }}
                                    <el-tag v-if="parseFloat(row.brier) < 0.25" type="success" size="small" effect="plain" style="margin-left:2px">Gd</el-tag>
                                </div>
                                <span v-else>-</span>
                            </template>
                        </el-table-column>
                        <el-table-column prop="n_events" label="Events" width="80" align="center" />
                        
                        <el-table-column prop="n" label="N" width="70" align="center" />
                        <el-table-column label="Features" min-width="150">
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
/**
 * ModelComparisonTab.vue
 * 多模型对比分析标签页。
 * 
 * 职责：
 * 1. 提供可视化界面，允许用户构建多个不同的模型（Logistic 或 Cox）。
 * 2. 统计学对比：计算并展示 C-index/AUC、LRT P值、AIC/BIC、NRI、IDI 等关键对比指标。
 * 3. 可视化对比：通过 ROC 曲线、校准曲线 (Calibration) 和决策曲线 (DCA) 评估模型优劣。
 * 4. 支持 Cox 随访时间点的动态切换。
 */
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import AdvancedModelingService from '@/services/advanced_modeling_service'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

// 响应式状态
const modelType = ref('cox') // 当前选中的模型类型：logistic 或 cox
const target = ref('') // 结局变量（或 Cox 的时间变量）
const eventCol = ref('') // 事件状态列（Cox 专用）
const loading = ref(false) // 加载状态
const results = ref(null) // 后端返回的所有对比数据
const selectedTimePoint = ref(null) // Cox 模型下当前选中的预测时间点
const activeVizTab = ref('roc') // 当前活跃的可视化标签页 (roc/calibration/dca)

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
/**
 * 更新选中的时间点。
 * 当结果更新或时间点列表变化时，确保有一个合法的选中项。
 */
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

/**
 * 发送模型对比请求。
 * 包含所有模型的变量配置、目标变量及类型。
 */
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
        // Backend returns the list directly
        results.value = res
        ElMessage.success('模型对比完成！')
        
    } catch (e) {
        ElMessage.error(e.message || '模型对比失败')
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
    ElMessage.success('方法学段落已复制')
}

// Helper to get time metrics safely
const getTimeMetrics = (metrics, t) => {
    if (!metrics || !metrics.time_dependent) return null
    // Try multiple key formats
    if (metrics.time_dependent[t]) return metrics.time_dependent[t]
    if (metrics.time_dependent[String(t)]) return metrics.time_dependent[String(t)]
    if (typeof t === 'number') {
        if (metrics.time_dependent[t.toFixed(1)]) return metrics.time_dependent[t.toFixed(1)]
        if (metrics.time_dependent[t.toFixed(0)]) return metrics.time_dependent[t.toFixed(0)]
    }
    return null
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
            p_delong: m.p_delong !== undefined ? m.p_delong : undefined,
            delta_aic: m.delta_aic !== undefined ? m.delta_aic : undefined,
            delta_bic: m.delta_bic !== undefined ? m.delta_bic : undefined,
            n: m.n || '-',
            features: r.features || []
        }
        
        const fmtCI = (val, l, h) => (val !== undefined && val !== null) ? `${Number(val).toFixed(3)} (${Number(l).toFixed(3)} - ${Number(h).toFixed(3)})` : '-'
        const fmtVal = (val, d=3) => (val !== undefined && val !== null) ? Number(val).toFixed(d) : '-'

        if (modelType.value === 'cox') {
            const t = selectedTimePoint.value
            const tm = getTimeMetrics(m, t)
            
            if (tm) {
                return {
                    ...base,
                    p_delong: tm.p_delong !== undefined ? tm.p_delong : undefined,
                    auc: tm.auc !== undefined ? tm.auc.toFixed(3) : '-',
                    auc_ci: tm.auc_ci || '-', // Backend pre-formatted string or use local logic if data avail (backend gives string)
                    auc_p: tm.auc_p !== undefined ? (tm.auc_p < 0.001 ? '<0.001' : tm.auc_p.toFixed(3)) : '-',
                    
                    sensitivity_ci: fmtCI(tm.sensitivity, tm.sensitivity_ci_lower, tm.sensitivity_ci_upper),
                    specificity_ci: fmtCI(tm.specificity, tm.specificity_ci_lower, tm.specificity_ci_upper),
                    ppv_ci: fmtCI(tm.ppv, tm.ppv_ci_lower, tm.ppv_ci_upper),
                    npv_ci: fmtCI(tm.npv, tm.npv_ci_lower, tm.npv_ci_upper),
                    youden: fmtVal(tm.youden_index),
                    cutoff: fmtVal(tm.optimal_threshold),
                    brier: fmtVal(tm.brier_score),
                    n_events: tm.n_events || '-',
                    
                    nri: tm.nri !== undefined ? tm.nri.toFixed(3) : '-',
                    nri_p: tm.nri_p !== undefined ? (tm.nri_p < 0.001 ? '<0.001' : tm.nri_p.toFixed(3)) : '-',
                    nri_ci: tm.nri_ci || '-',
                    idi: tm.idi !== undefined ? tm.idi.toFixed(3) : '-',
                    idi_p: tm.idi_p !== undefined ? (tm.idi_p < 0.001 ? '<0.001' : tm.idi_p.toFixed(3)) : '-',
                    idi_ci: tm.idi_ci || '-'
                }
            } else {
                 return { ...base, auc: '-', auc_ci: '-', nri: '-', idi: '-' }
            }
        } else {
            // Logistic - Assuming backend sends similar structure or update backend later
            // Currently backend for logistic does NOT send detailed binary metrics in 'compare_models' (it's simplified).
            // So these will be '-'
            return {
                ...base,
                auc: m.auc !== undefined ? m.auc.toFixed(3) : '-',
                auc_ci: m.auc_ci || '-',
                auc_p: m.auc_p !== undefined ? (m.auc_p < 0.001 ? '<0.001' : m.auc_p.toFixed(3)) : '-',
                nri: m.nri !== undefined ? m.nri.toFixed(3) : '-',
                nri_p: m.nri_p !== undefined ? (m.nri_p < 0.001 ? '<0.001' : m.nri_p.toFixed(3)) : '-',
                nri_ci: m.nri_ci || '-',
                idi: m.idi !== undefined ? m.idi.toFixed(3) : '-',
                idi_p: m.idi_p !== undefined ? (m.idi_p < 0.001 ? '<0.001' : m.idi_p.toFixed(3)) : '-',
                idi_ci: m.idi_ci || '-'
            }
        }
    })
})
import { DocumentCopy } from '@element-plus/icons-vue'

/**
 * 以 TSV 格式（Tab 分隔）将统计表格数据复制到剪贴板。
 */
const copyTableData = () => {
    if (!results.value || !tableData.value) return
    
    // 表头
    const headers = [
        '模型名称', 
        'AUC/C-index', 'AUC 95% CI', 'AUC P-Value',
        'P Value (LRT)', 
        'AIC', 'Delta AIC', 
        'NRI', 'NRI P-Value', 'NRI 95% CI',
        'IDI', 'IDI P-Value', 'IDI 95% CI',
        'Sensitivity (95% CI)', 'Specificity (95% CI)',
        'PPV (95% CI)', 'NPV (95% CI)',
        'Youden Index', 'Optimal Cutoff', 'Brier Score', 'Events (E)',
        '样本量', '纳入变量'
    ]
    
    // 行数据
    const rows = tableData.value.map(row => [
        row.name,
        row.auc, row.auc_ci, row.auc_p,
        row.p_lrt,
        row.aic, row.delta_aic !== undefined ? row.delta_aic : '-',
        row.nri, row.nri_p, row.nri_ci || '-',
        row.idi, row.idi_p, row.idi_ci || '-',
        row.sensitivity_ci || '-', row.specificity_ci || '-',
        row.ppv_ci || '-', row.npv_ci || '-',
        row.youden || '-', row.cutoff || '-', row.brier || '-', row.n_events || '-',
        row.n,
        row.features.join(' + ')
    ])
    
    // 拼接为字符串
    const tsvContent = [
        headers.join('\t'),
        ...rows.map(r => r.join('\t'))
    ].join('\n')
    
    // 写入剪贴板
    navigator.clipboard.writeText(tsvContent).then(() => {
        ElMessage.success('表格数据已复制，可直接粘贴到 Excel')
    }).catch(err => {
    ElMessage.error('复制失败: ' + err)
    })
}

// Plotting
// Plotting Dispatcher
// Plotting Dispatcher
const handleTabChange = () => {
    nextTick(() => {
        if (activeVizTab.value === 'roc') renderPlot()
        else if (activeVizTab.value === 'calibration') renderCalibration()
        else if (activeVizTab.value === 'dca') renderDCA()
    })
}

/**
 * 1. 绘制 ROC 曲线对比图。
 * 支持 Logistic (普通 ROC) 和 Cox (时间依赖性 ROC)。
 */
const renderPlot = () => {
    const el = document.getElementById('comparison-plot')
    if (!el || !results.value) return
    
    const traces = []
    
    results.value.forEach(r => {
        let rocData = null
        let titleSuffix = ''
        
        // 获取数据源
        if (modelType.value === 'logistic') {
            rocData = r.plots ? r.plots.roc : r.roc_data
            if (r.metrics && r.metrics.auc) {
                 titleSuffix = `(AUC=${r.metrics.auc.toFixed(3)})`
            }
        } else if (modelType.value === 'cox' && selectedTimePoint.value) {
           if (r.metrics) {
               const tm = getTimeMetrics(r.metrics, selectedTimePoint.value)
               if (tm) {
                   rocData = tm.roc_data
                   titleSuffix = tm.auc ? `(AUC=${tm.auc.toFixed(3)})` : '(AUC=-)'
               }
           }
        }

        if (rocData) {
            traces.push({
                x: rocData.map(d => d.fpr),
                y: rocData.map(d => d.tpr),
                mode: 'lines',
                name: `${r.name} ${titleSuffix}`
            })
        }
    })
    
    // 绘制 45 度基准线 (对角线)
    traces.push({
        x: [0, 1], y: [0, 1],
        mode: 'lines',
        line: { dash: 'dash', color: 'gray' },
        showlegend: false
    })
    
    const title = modelType.value === 'cox' 
        ? `时间依赖性 ROC (Time-Dependent ROC, t=${selectedTimePoint.value})`
        : '模型 ROC 曲线对比 (ROC Comparison)'

    const layout = {
        title: title,
        xaxis: { title: '1 - 特异度 (FPR)', range: [0, 1] },
        yaxis: { title: '灵敏度 (TPR)', range: [0, 1] },
        legend: { x: 0.6, y: 0.1 },
        margin: { l: 50, r: 20, t: 40, b: 40 }
    }
    
    Plotly.newPlot(el, traces, layout)
}

/**
 * 2. 绘制校准曲线对比图。
 */
const renderCalibration = () => {
    const el = document.getElementById('calibration-plot')
    if (!el || !results.value) return
    
    const traces = []
    
    results.value.forEach(r => {
        let calibData = null
        if (modelType.value === 'logistic') {
             calibData = (r.plots) ? r.plots.calibration : null
        } else if (modelType.value === 'cox' && selectedTimePoint.value) {
             const tm = getTimeMetrics(r.metrics, selectedTimePoint.value)
             calibData = tm ? tm.calibration : null
        }
        
        if (calibData) {
            traces.push({
                x: calibData.prob_pred,
                y: calibData.prob_true,
                mode: 'lines+markers',
                name: r.name
            })
        }
    })
    
    // 绘制理想校准线 (y=x)
    traces.push({
        x: [0, 1], y: [0, 1],
        mode: 'lines',
        line: { dash: 'dash', color: 'gray' },
        name: 'Ideal',
        showlegend: false
    })
    
    const layout = {
         title: modelType.value === 'cox' ? `校准曲线 (t=${selectedTimePoint.value})` : '校准曲线 (Calibration Curve)',
        xaxis: { title: '预测概率 (Predicted Probability)', range: [0, 1] },
        yaxis: { title: '实际观察比例 (Observed Fraction)', range: [0, 1] },
        margin: { l: 50, r: 20, t: 40, b: 40 },
        height: 450
    }
    Plotly.newPlot(el, traces, layout)
}

/**
 * 3. 绘制决策曲线 (Decision Curve Analysis) 对比图。
 */
const renderDCA = () => {
    const el = document.getElementById('dca-plot')
    if (!el || !results.value) return
    
    const traces = []
    let hasData = false
    
    results.value.forEach(r => {
        let dcaData = null
        if (modelType.value === 'logistic') {
             dcaData = (r.plots) ? r.plots.dca : null
        } else if (modelType.value === 'cox' && selectedTimePoint.value) {
             const tm = getTimeMetrics(r.metrics, selectedTimePoint.value)
             dcaData = tm ? tm.dca : null
        }
        
        if (dcaData) {
            hasData = true
            // 各模型的净获益曲线
            traces.push({
                x: dcaData.thresholds,
                y: dcaData.net_benefit_model,
                mode: 'lines',
                name: r.name
            })
            
            // 绘制全处理 (Treat All) 和不处理 (Treat None) 的基准线（仅需从第一条数据中提取一次）
            if (traces.length === 1) { 
                 traces.unshift({
                    x: dcaData.thresholds,
                    y: dcaData.net_benefit_all,
                    mode: 'lines',
                    line: { dash: 'dot', color: 'gray', width: 1 },
                    name: 'Treat All'
                 })
                 traces.unshift({
                    x: dcaData.thresholds,
                    y: dcaData.net_benefit_none,
                    mode: 'lines',
                    line: { width: 2, color: 'black' },
                    name: 'Treat None'
                 })
            }
        }
    })
    
    const layout = {
        title: '临床决策曲线 (Decision Curve Analysis)',
        xaxis: { title: '阈值概率 (Threshold Probability)', range: [0, 1] },
        yaxis: { title: '净获益 (Net Benefit)', range: [-0.05, 0.4] },
        margin: { l: 50, r: 20, t: 40, b: 40 },
        height: 450
    }
    
    if (hasData) Plotly.newPlot(el, traces, layout)
}

// Watchers
watch([results, selectedTimePoint], () => {
    handleTabChange()
})
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
