<template>
    <div class="competing-risks-container">
        <el-row :gutter="20">
            <!-- 左侧：参数配置 (Config Panel) -->
            <el-col :span="6">
                <el-card shadow="hover" class="config-card">
                    <template #header>
                        <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                            <span>⚡️ 竞争风险模型</span>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <el-button 
                                    type="primary" 
                                    link 
                                    :icon="MagicStick" 
                                    @click="suggestRoles"
                                    :loading="isSuggestingRoles"
                                >
                                    AI 推荐
                                </el-button>
                                <el-tooltip content="竞争风险模型适用于存在多个互斥终点事件的情况，如死于心血管疾病与死于其他疾病。" placement="top">
                                    <el-icon><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </div>
                        </div>
                    </template>
                    <el-form label-position="top">
                        <el-form-item label="时间变量 (Time)" required>
                            <el-select v-model="config.time_col" filterable placeholder="选择生存时间变量">
                                <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        <el-form-item label="事件状态 (Event)" required>
                            <el-select v-model="config.event_col" filterable placeholder="选择事件变量 (0, 1, 2...)">
                                <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                            <div class="help-text">需包含至少2种事件类型 (如: 1=死因A, 2=死因B)。0=删失 (Censor)。</div>
                        </el-form-item>
                        
                        <el-form-item label="协变量 (Covariates)" required>
                            <el-select v-model="config.covariates" multiple filterable collapse-tags placeholder="选择混杂因素/预测变量">
                                <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        
                        <el-form-item label="分组变量 (Group - 可选)">
                             <el-select v-model="config.group_col" filterable clearable placeholder="用于 CIF 绘图的分组比较">
                                <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                             </el-select>
                             <div class="help-text">不选则展示全人群的累积发生率曲线。</div>
                        </el-form-item>
                        
                        <el-button type="primary" style="width: 100%; margin-top: 10px;" @click="runAnalysis" :loading="loading" :disabled="!isValid">
                            运行竞争风险分析
                        </el-button>
                    </el-form>
                </el-card>
            </el-col>
            
            <!-- 右侧：结果展示 (Result Panel) -->
            <el-col :span="18">
                <div v-if="!hasResults" class="empty-placeholder">
                    <el-empty description="请在左侧配置参数并点击运行分析按钮。">
                        <template #extra>
                            <div style="font-size: 13px; color: #909399; max-width: 400px; text-align: center;">
                                本模块提供原因特异性 Cox 模型 (Cause-Specific Cox) 与 Fine-Gray 子分布风险模型。
                            </div>
                        </template>
                    </el-empty>
                </div>
                
                <div v-else class="results-area">
                    <div style="margin-bottom: 15px; text-align: right;">
                        <el-button 
                            type="primary" 
                            size="small" 
                            @click="runAIInterpretation" 
                            :loading="isInterpreting" 
                            :icon="MagicStick"
                            class="ai-advanced-btn"
                        >
                            AI 深度解读 (Fine-Gray/CIF)
                        </el-button>
                    </div>

                    <InterpretationPanel 
                        v-if="aiInterpretation"
                        :interpretation="{ text: aiInterpretation, is_ai: true, level: 'info' }"
                        style="margin-bottom: 20px;"
                    />

                    <el-tabs type="border-card" class="result-tabs">
                        <!-- 标签页 1：CIF 图表 -->
                        <el-tab-pane label="累积发生率 (CIF 曲线)">
                             <div class="plot-container">
                                 <div id="cif-plot" style="width:100%; height:520px;"></div>
                             </div>
                             <div class="interpretation-panel" v-if="cifResults?.methodology">
                                 <div class="panel-title"><el-icon><InfoFilled /></el-icon> 方法学提示</div>
                                 <p>{{ cifResults.methodology }}</p>
                             </div>
                        </el-tab-pane>
                        
                        <!-- 标签页 2：原因特异性风险模型 -->
                        <el-tab-pane label="原因特异性模型 (CS-Cox)">
                            <div class="alert-info" style="margin-bottom: 20px;">
                                <el-alert title="CS-Cox 适用于由于生物学病因学研究，其将竞争事件视为删失。" type="info" :closable="false" show-icon />
                            </div>
                            
                            <div v-for="model in modelResults.models" :key="model.event_type" class="model-section">
                                <div class="model-header-alt">
                                    <span>🎯 结局事件: <b>{{ model.event_type }}</b></span>
                                    <el-tag size="small" type="primary">Cause-Specific Cox</el-tag>
                                </div>
                                <div v-if="model.error" class="error-msg">误差: {{ model.error }}</div>
                                <el-table v-else :data="model.summary" class="publication-table" size="small">
                                    <el-table-column prop="variable" label="变量 (Variable)" min-width="150" />
                                    <el-table-column prop="hr" label="风险比 (HR)" width="100">
                                        <template #default="scope">{{ scope.row.hr.toFixed(3) }}</template>
                                    </el-table-column>
                                    <el-table-column label="95% CI" width="180" align="center">
                                        <template #default="scope">
                                            ({{ scope.row.ci_lower.toFixed(3) }}, {{ scope.row.ci_upper.toFixed(3) }})
                                        </template>
                                    </el-table-column>
                                    <el-table-column prop="p_value" label="P 值" width="100">
                                        <template #default="scope">
                                            <span :class="{'sig-p': scope.row.p_value < 0.05}">
                                                {{ scope.row.p_value < 0.001 ? '<0.001' : scope.row.p_value.toFixed(3) }}
                                            </span>
                                        </template>
                                    </el-table-column>
                                    <el-table-column prop="z" label="Z 值" width="90">
                                        <template #default="scope">{{ scope.row.z ? scope.row.z.toFixed(2) : '-' }}</template>
                                    </el-table-column>
                                </el-table>
                                <div class="model-footer" v-if="model.aic">AIC: {{ model.aic.toFixed(2) }}</div>
                            </div>
                            
                            <div class="interpretation-panel" v-if="modelResults?.methodology">
                                 <div class="panel-title"><el-icon><InfoFilled /></el-icon> 方法学提示</div>
                                 <p>{{ modelResults.methodology }}</p>
                             </div>
                        </el-tab-pane>

                        <!-- 标签页 3：Fine-Gray 模型 -->
                        <el-tab-pane label="Fine-Gray 模型 (SHR)">
                            <div class="alert-warning" style="margin-bottom: 20px;">
                                <el-alert title="Fine-Gray 模型计算子分布风险比 (SHR)，直接反映对累积发生率的影响，常用于风险预测。" type="warning" :closable="false" show-icon />
                            </div>
                            
                            <div v-if="!modelResults.fine_gray_models || modelResults.fine_gray_models.length === 0">
                                <el-empty description="无法生成 Fine-Gray 模型结果。" />
                            </div>
                            <div v-else>
                                <div v-for="model in modelResults.fine_gray_models" :key="model.event_type" class="model-section">
                                    <div class="model-header-alt">
                                        <span>🎯 结局事件: <b>{{ model.event_type }}</b></span>
                                        <el-tag size="small" type="warning">Fine-Gray (SHR)</el-tag>
                                    </div>
                                    <div v-if="model.error" class="error-msg">误差: {{ model.error }}</div>
                                    <el-table v-else :data="model.summary" class="publication-table" size="small">
                                        <el-table-column prop="variable" label="变量 (Variable)" min-width="150" />
                                        <el-table-column prop="hr" label="SHR" width="100">
                                            <template #default="scope">{{ scope.row.hr.toFixed(3) }}</template>
                                        </el-table-column>
                                        <el-table-column label="95% CI" width="180" align="center">
                                            <template #default="scope">
                                                ({{ scope.row.ci_lower.toFixed(3) }}, {{ scope.row.ci_upper.toFixed(3) }})
                                            </template>
                                        </el-table-column>
                                        <el-table-column prop="p_value" label="P 值" width="100">
                                            <template #default="scope">
                                                <span :class="{'sig-p': scope.row.p_value < 0.05}">
                                                    {{ scope.row.p_value < 0.001 ? '<0.001' : scope.row.p_value.toFixed(3) }}
                                                </span>
                                            </template>
                                        </el-table-column>
                                    </el-table>
                                </div>
                            </div>
                        </el-tab-pane>
                    </el-tabs>
                </div>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
/**
 * CompetingRiskTab.vue
 * 竞争风险模型分析标签页。
 * 
 * 职责：
 * 1. 运行原因特异性 Cox 模型 (Cause-Specific Cox)。
 * 2. 运行 Fine-Gray 子分布风险模型 (Subdistribution Hazard)。
 * 3. 绘制多组别、多事件的累积发生率 (CIF) 曲线。
 */
import { ref, reactive, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, QuestionFilled, MagicStick } from '@element-plus/icons-vue'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'
import InterpretationPanel from './InterpretationPanel.vue'

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
const isSuggestingRoles = ref(false)
const isInterpreting = ref(false)
const aiInterpretation = ref(null)

const variables = computed(() => props.metadata?.variables || [])
const numVars = computed(() => variables.value.filter(v => v.type === 'numeric' || v.type === 'integer'))
const catVars = computed(() => variables.value)

const isValid = computed(() => config.time_col && config.event_col && config.covariates.length > 0)

/**
 * 执行全套竞争风险分析。
 */
const runAnalysis = async () => {
    loading.value = true
    try {
        // 1. 运行回归模型
        const p1 = api.post('/advanced/competing-risks', {
            dataset_id: props.datasetId,
            time_col: config.time_col,
            event_col: config.event_col,
            covariates: config.covariates
        })
        
        // 2. 运行 CIF 可视化 (独立接口)
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
        
        ElMessage.success('分析完成。病因学研究请参考 CS-Cox，风险预测请参考 Fine-Gray。')
        
        nextTick(() => {
            renderCIF(res2.data.cif_data)
        })
        
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '分析失败')
    } finally {
        loading.value = false
    }
}

const runAIInterpretation = async () => {
    if (!modelResults.value) return
    isInterpreting.value = true
    try {
        const { data } = await api.post('/advanced/ai-interpret-cif', {
            plot_data: cifResults.value.cif_data,
            time_col: config.time_col,
            event_col: config.event_col,
            // Also pass model summaries for a more comprehensive analysis
            models: modelResults.value.fine_gray_models || modelResults.value.models
        })
        aiInterpretation.value = data.analysis
        ElMessage.success("AI 竞争风险解读完成")
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'AI 解读失败')
    } finally {
        isInterpreting.value = false
    }
}

const suggestRoles = async () => {
    isSuggestingRoles.value = true
    try {
        const { data } = await api.post('/statistics/ai-suggest-roles', {
            dataset_id: props.datasetId,
            analysis_type: 'km' // Reusing KM logic for CIF since inputs are similar (Time/Event/Group)
        })
        
        config.time_col = data.time || config.time_col
        config.event_col = data.event || config.event_col
        config.group_col = data.group || config.group_col
        
        ElMessage({
            message: `AI 已为您推荐竞争风险分析的最佳变量角色。\n理由: ${data.reason || '基于随访数据特征推荐'}`,
            type: 'success',
            duration: 5000
        })
    } catch (e) {
        console.error("AI Role suggestion failed", e)
        ElMessage.error(e.response?.data?.message || "AI 推荐失败")
    } finally {
        isSuggestingRoles.value = false
    }
}

/**
 * 渲染 CIF 曲线图。
 */
const renderCIF = (cifData) => {
    const traces = []
    const colors = ['#3B71CA', '#E6A23C', '#2E7D32', '#D32F2F', '#9467bd']
    const groups = [...new Set(cifData.map(d => d.group))]
    
    cifData.forEach(item => {
        const x = item.cif_data.map(p => p.x)
        const y = item.cif_data.map(p => p.y)
        
        let color = '#333'
        if (groups.length > 1) {
            const gIdx = groups.indexOf(item.group)
            color = colors[gIdx % colors.length]
        } else {
             const eIdx = (item.event_type - 1)
             color = colors[eIdx % colors.length]
        }
        
        let dash = 'solid'
        if (item.event_type === 2) dash = 'dash'
        if (item.event_type === 3) dash = 'dot'
        
        traces.push({
            x: x,
            y: y,
            mode: 'lines',
            name: groups.length > 1 ? `${item.group} (事件 ${item.event_type})` : `事件 ${item.event_type}`,
            line: { 
                color: color, 
                dash: dash, 
                width: 2.5,
                shape: 'hv' // Step function for CIF
            }
        })
    })
    
    const layout = {
        title: {
            text: '累积发生率函数 (Cumulative Incidence Function)',
            font: { size: 18, color: '#303133' }
        },
        xaxis: { 
            title: config.time_col || '时间 (Time)',
            gridcolor: '#f0f0f0'
        },
        yaxis: { 
            title: '累积发生率', 
            range: [0, Math.min(1, Math.max(...cifData.flatMap(d => d.cif_data.map(p => p.y))) * 1.2 || 1)],
            gridcolor: '#f0f0f0'
        },
        legend: { 
            x: 0.05, 
            y: 0.95,
            bgcolor: 'rgba(255,255,255,0.7)',
            bordercolor: '#f0f0f0',
            borderwidth: 1
        },
        margin: { l: 60, r: 40, t: 80, b: 60 },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        hovermode: 'closest'
    }
    
    Plotly.newPlot('cif-plot', traces, layout, { responsive: true })
}
</script>

<style scoped>
.competing-risks-container {
    height: 100%;
}
.empty-placeholder {
    height: 600px;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #fff;
    border-radius: 8px;
    border: 1px dashed #dcdfe6;
}
.help-text {
    font-size: 12px;
    color: #909399;
    line-height: 1.4;
    margin-top: 6px;
}
.interpretation-panel {
    margin-top: 24px;
    padding: 16px;
    background: #ecf5ff;
    border-radius: 8px;
    border-left: 4px solid #3B71CA;
}
.panel-title {
    font-weight: bold;
    color: #3B71CA;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.interpretation-panel p {
    margin: 0;
    font-size: 13px;
    color: #606266;
    line-height: 1.6;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: bold;
}
.model-section {
    margin-bottom: 40px;
}
.model-header-alt {
    padding: 8px 12px;
    background: #f8f9fb;
    border-bottom: 2px solid #ebeef5;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.publication-table {
    border-top: 2px solid #303133;
    border-bottom: 2px solid #303133;
}
:deep(.el-table__header) {
    border-bottom: 1px solid #303133;
}
.sig-p {
    font-weight: bold;
    color: #D32F2F;
}
.ai-advanced-btn {
    background: linear-gradient(45deg, #6366f1, #a855f7);
    border: none;
    transition: all 0.3s ease;
}
.ai-advanced-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
}
.model-footer {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
    text-align: right;
}
.error-msg {
    color: #F56C6C;
    padding: 10px;
    background: #fef0f0;
    border-radius: 4px;
}
</style>
