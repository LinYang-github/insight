<template>
    <div class="model-comparison-container">
        <el-row :gutter="20">
            <!-- Left: Config Panel -->
            <el-col :span="8">
                <el-card shadow="never" class="config-card">
                    <template #header>
                        <div class="card-header">
                            <span>🛠️ 模型配置器 (Model Builder)</span>
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
                            对比多个模型在<b>完全相同样本 (Same N)</b> 上的表现。
                            <br/>
                            用于证明联合指标优于单指标 (AUC 提升)。
                        </div>
                    </el-alert>

                    <el-form label-position="top">
                        <el-form-item label="模型类型 (Model Type)">
                            <el-radio-group v-model="modelType">
                                <el-radio-button value="logistic">Logistic Regression</el-radio-button>
                                <el-radio-button value="cox">Cox Regression</el-radio-button>
                            </el-radio-group>
                        </el-form-item>

                        <el-form-item :label="modelType === 'cox' ? '时间变量 (Time Variable)' : '结局变量 (Target Outcome)'" required>
                            <el-select v-model="target" filterable placeholder="Select Variable">
                                <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>

                        <el-form-item v-if="modelType === 'cox'" label="事件状态 (Event Status 0/1)" required>
                            <el-select v-model="eventCol" filterable placeholder="Select Event (1=Occurred)">
                                <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>

                        <div class="model-list">
                            <label class="el-form-item__label">模型组合 (Model Configs)</label>
                            
                            <div v-for="(model, index) in modelConfigs" :key="index" class="model-row">
                                <div class="model-header">
                                    <span class="model-index">Model {{ index + 1 }}</span>
                                    <el-button type="danger" link size="small" @click="removeModel(index)" v-if="modelConfigs.length > 2">
                                        Remove
                                    </el-button>
                                </div>
                                
                                <el-input v-model="model.name" placeholder="模型名称 (e.g. Model A)" style="margin-bottom: 5px" />
                                
                                <el-select v-model="model.features" multiple filterable placeholder="选择特征 (Features)" collapse-tags>
                                    <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" :disabled="v.name === target" />
                                </el-select>
                            </div>
                        </div>

                        <el-button type="default" style="width: 100%; margin-top: 10px; margin-bottom: 20px" @click="addModel">
                            + 添加对比模型
                        </el-button>

                        <el-button type="primary" size="large" style="width: 100%" @click="runComparison" :loading="loading" :disabled="!isValid">
                            🚀 开始对比 (Run Comparison)
                        </el-button>
                    </el-form>
                </el-card>
            </el-col>

            <!-- Right: Visualization -->
            <el-col :span="16">
                <div class="viz-area">
                    <div id="comparison-plot" style="width: 100%; height: 500px; background: #fff;"></div>
                    <div v-if="!results" class="placeholder-overlay">
                        配置模型以查看 ROC 对比
                    </div>
                </div>

                <!-- Result Table -->
                <el-card shadow="never" style="margin-top: 20px" v-if="results">
                    <template #header>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>统计对比表 (Statistics)</span>
                            <el-button v-if="methodology" size="small" type="primary" plain @click="copyText">Copy Methods</el-button>
                        </div>
                    </template>
                    <el-table :data="tableData" stripe border size="small">
                        <el-table-column prop="name" label="模型名称" width="150" />
                        <el-table-column prop="auc" label="C-index / AUC (95% CI)" width="180">
                            <template #default="scope">
                                {{ scope.row.auc }} <span style="color: gray">{{ scope.row.auc_ci }}</span>
                            </template>
                        </el-table-column>
                        
                        <el-table-column label="P值 (模型提升)" width="130">
                            <template #header>
                                P for Improvement
                                <el-tooltip content="似然比检验 (LRT) P值。用于评估新加入的变量是否带来统计学显著的性能提升 (P<0.05)。而不只是看AUC数值增加。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                <span v-if="scope.row.lrt_p !== undefined">
                                     <span :style="{fontWeight: scope.row.lrt_p < 0.05 ? 'bold' : 'normal', color: scope.row.lrt_p < 0.05 ? 'red' : 'black'}">
                                        {{ scope.row.lrt_p < 0.001 ? '< 0.001' : scope.row.lrt_p.toFixed(3) }}
                                     </span>
                                </span>
                                <span v-else style="color: #ccc">-</span>
                            </template>
                        </el-table-column>
                        
                        <el-table-column label="AIC (变化)" width="110">
                            <template #header>
                                AIC (Delta)
                                <el-tooltip content="赤池信息准则。数值越低越好。绿色数字(-x.x)代表模型拟合/复杂度平衡更佳。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                {{ scope.row.aic }}
                                <div v-if="scope.row.delta_aic" :style="{color: scope.row.delta_aic < -2 ? 'green' : (scope.row.delta_aic > 2 ? 'red' : 'gray'), fontSize: '11px', fontWeight: 'bold'}">
                                     ({{ scope.row.delta_aic > 0 ? '+' : '' }}{{ scope.row.delta_aic.toFixed(1) }})
                                </div>
                            </template>
                        </el-table-column>

                        <el-table-column label="BIC (变化)" width="110">
                            <template #header>
                                BIC (Delta)
                                <el-tooltip content="贝叶斯信息准则。数值越低越好。比AIC惩罚更重，更倾向于简单模型。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <template #default="scope">
                                {{ scope.row.bic }}
                                <div v-if="scope.row.delta_bic" :style="{color: scope.row.delta_bic < -2 ? 'green' : (scope.row.delta_bic > 2 ? 'red' : 'gray'), fontSize: '11px', fontWeight: 'bold'}">
                                     ({{ scope.row.delta_bic > 0 ? '+' : '' }}{{ scope.row.delta_bic.toFixed(1) }})
                                </div>
                            </template>
                        </el-table-column>

                        <el-table-column label="NRI" align="center">
                            <template #header>
                                NRI
                                <el-tooltip content="净重分类改善指数。>0 表示新模型能更准确地将患者分入正确风险组。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <el-table-column label="Estimate (95% CI)" width="150">
                                <template #default="scope">
                                    <span v-if="scope.row.nri_display" :style="{color: scope.row.nri > 0 ? 'green' : 'red', fontWeight: 'bold'}">
                                        {{ scope.row.nri_display }}
                                    </span>
                                    <span v-else>
                                        <el-tooltip v-if="scope.row.nri_error" :content="'计算失败: ' + scope.row.nri_error" placement="top">
                                            <span style="color: #E6A23C; cursor: help; border-bottom: 1px dashed #E6A23C">计算失败</span>
                                        </el-tooltip>
                                        <span v-else style="color: #ccc">-</span>
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column label="P value" width="80">
                                <template #default="scope">
                                    <span v-if="scope.row.nri_p !== undefined">{{ scope.row.nri_p < 0.001 ? '<.001' : scope.row.nri_p.toFixed(3) }}</span>
                                    <span v-else style="color: #ccc">-</span>
                                </template>
                            </el-table-column>
                        </el-table-column>

                        <el-table-column label="IDI" align="center">
                            <template #header>
                                IDI
                                <el-tooltip content="综合判别改善指数。>0 表示新模型预测概率的整体区分度提升。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                            </template>
                            <el-table-column label="Estimate (95% CI)" width="150">
                                <template #default="scope">
                                    <span v-if="scope.row.idi_display" :style="{color: scope.row.idi > 0 ? 'green' : 'red', fontWeight: 'bold'}">
                                        {{ scope.row.idi_display }}
                                    </span>
                                    <span v-else style="color: #ccc">-</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="P value" width="80">
                                <template #default="scope">
                                    <span v-if="scope.row.idi_p !== undefined">{{ scope.row.idi_p < 0.001 ? '<.001' : scope.row.idi_p.toFixed(3) }}</span>
                                    <span v-else style="color: #ccc">-</span>
                                </template>
                            </el-table-column>
                        </el-table-column>

                        <el-table-column prop="n" label="N" width="70" />
                        <el-table-column prop="features" label="包含特征">
                             <template #default="scope">
                                 <el-tag v-for="f in scope.row.features" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
                             </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import Plotly from 'plotly.js-dist-min'
import api from '../../../api/client'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

// Variables
const allVars = computed(() => props.metadata?.variables || [])

// State
const modelType = ref('logistic')
const target = ref('')
const eventCol = ref('')
const modelConfigs = ref([
    { name: 'Model 1 (Base)', features: [] },
    { name: 'Model 2 (Test)', features: [] }
])
const loading = ref(false)
const results = ref(null)

// Actions
const addModel = () => {
    if (modelConfigs.value.length >= 5) {
        ElMessage.warning('最多支持 5 个模型对比')
        return
    }
    modelConfigs.value.push({ name: `Model ${modelConfigs.value.length + 1}`, features: [] })
}

const removeModel = (idx) => {
    modelConfigs.value.splice(idx, 1)
}

const isValid = computed(() => {
    const basic = target.value && modelConfigs.value.every(m => m.name && m.features.length > 0)
    if (modelType.value === 'cox') {
        return basic && eventCol.value
    }
    return basic
})

// Methodology
const methodology = ref('')

const copyText = () => {
    if(!methodology.value) return
    navigator.clipboard.writeText(methodology.value).then(() => {
        ElMessage.success('Copied methodology')
    })
}

const runComparison = async () => {
    loading.value = true
    methodology.value = ''
    try {
        const payload = {
            dataset_id: props.datasetId,
            target: target.value,
            event_col: modelType.value === 'cox' ? eventCol.value : null,
            models: modelConfigs.value,
            model_type: modelType.value
        }
        
        const { data } = await api.post('/advanced/compare-models', payload)
        results.value = data.comparison_data
        methodology.value = data.methodology
        
        renderPlot(data.comparison_data)
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '对比分析失败')
    } finally {
        loading.value = false
    }
}

const tableData = computed(() => {
    if (!results.value) return []
    return results.value.map(r => ({
        name: r.name,
        auc: r.metrics?.auc ? r.metrics.auc.toFixed(3) : '-',
        auc_ci: r.metrics?.auc_ci ? `(${r.metrics.auc_ci})` : '', 
        n: r.n,
        features: r.features,
        // New Metrics
        aic: r.metrics?.aic ? r.metrics.aic.toFixed(1) : '-',
        bic: r.metrics?.bic ? r.metrics.bic.toFixed(1) : '-',
        delta_aic: r.metrics?.delta_aic,
        delta_bic: r.metrics?.delta_bic,
        nri: r.metrics?.nri,
        nri_display: (r.metrics?.nri !== undefined && r.metrics?.nri !== null) 
            ? `${r.metrics.nri.toFixed(3)} (${r.metrics.nri_ci || '?'})` 
            : null,
        nri_p: r.metrics?.nri_p,
        nri_error: r.metrics?.nri_error,
        
        idi: r.metrics?.idi,
        idi_display: (r.metrics?.idi !== undefined && r.metrics?.idi !== null) 
            ? `${r.metrics.idi.toFixed(3)} (${r.metrics.idi_ci || '?'})` 
            : null,
        idi_p: r.metrics?.idi_p,
        
        lrt_p: r.metrics?.lrt_p
    }))
})

// Visualization
const renderPlot = (resList) => {
    const traces = []
    
    // Sort by AUC desc for clean legend
    const sortedRes = [...resList].sort((a, b) => (b.metrics?.auc || 0) - (a.metrics?.auc || 0))
    
    sortedRes.forEach((res, i) => {
        if (!res.roc_data || res.roc_data.length === 0) return
        
        const aucStr = res.metrics?.auc ? `(AUC=${res.metrics.auc.toFixed(3)})` : ''
        
        traces.push({
            x: res.roc_data.map(d => d.x || d.fpr), // simple run might return x/y or fpr/tpr depending on previous impl
            y: res.roc_data.map(d => d.y || d.tpr),
            mode: 'lines',
            name: `${res.name} ${aucStr}`,
            line: { width: 3 }
        })
    })
    
    // Diagonal
    traces.push({
        x: [0, 1], y: [0, 1], 
        mode: 'lines', 
        line: { dash: 'dash', color: 'gray', width: 1 }, 
        name: 'Reference', 
        hoverinfo: 'skip'
    })
    
    const layout = {
        title: 'ROC Curve Comparison',
        xaxis: { title: '1 - Specificity (FPR)', range: [0, 1] },
        yaxis: { title: 'Sensitivity (TPR)', range: [0, 1] },
        legend: { x: 0.6, y: 0.1 },
        margin: { l: 50, r: 20, t: 50, b: 50 },
        height: 500
    }
    
    // Check key mapping (ModelingService.run_model returns metrics[auc] and plots[roc_curve: [{fpr, tpr}]])
    // Need to verify backend response structure for roc_data.
    // In comparison service: `roc_data = model_res['plots']['roc_curve']`
    // roc_curve list of {fpr, tpr}.
    
    // Update trace mapping above to use fpr/tpr
    Plotly.newPlot('comparison-plot', traces, layout)
}
</script>

<style scoped>
.model-row {
    background: #f5f7fa;
    padding: 10px;
    border-radius: 4px;
    margin-bottom: 10px;
    border: 1px solid #e4e7ed;
}
.model-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
}
.model-index {
    font-size: 12px;
    font-weight: bold;
    color: #909399;
}
.viz-area {
    position: relative;
    border: 1px solid #e4e7ed;
    border-radius: 4px;
}
.placeholder-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    background: rgba(255,255,255,0.8);
    color: #909399;
}
.ci-text {
    font-size: 12px;
    color: #909399;
    margin-left: 4px;
}
</style>
