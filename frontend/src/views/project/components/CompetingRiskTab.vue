<template>
    <div class="competing-risks-container">
        <el-row :gutter="20">
            <!-- 左侧：参数配置 -->
            <el-col :span="6">
                <el-card shadow="never">
                    <template #header>⚡️ 竞争风险模型</template>
                    <el-form label-position="top">
                        <el-form-item label="时间变量 (Time)" required>
                            <el-select v-model="config.time_col" filterable placeholder="选择时间变量">
                                <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        <el-form-item label="事件状态 (Event)" required>
                            <el-select v-model="config.event_col" filterable placeholder="选择事件变量 (0, 1, 2...)">
                                <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                            <div class="help-text">需包含至少2种事件类型 (如: 1=死因A, 2=死因B)。0=Censor。</div>
                        </el-form-item>
                        
                        <el-form-item label="协变量 (Covariates)" required>
                            <el-select v-model="config.covariates" multiple filterable placeholder="选择协变量">
                                <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        
                        <el-form-item label="分组变量 (分组 - 可选)">
                             <el-select v-model="config.group_col" filterable clearable placeholder="用于 CIF 绘图">
                                <el-option v-for="v in catVars" :key="v.name" :label="v.name" :value="v.name" />
                            </el-select>
                        </el-form-item>
                        
                        <el-button type="primary" style="width: 100%" @click="runAnalysis" :loading="loading" :disabled="!isValid">
                            运行分析 (Run Analysis)
                        </el-button>
                    </el-form>
                </el-card>
            </el-col>
            
            <!-- 右侧：结果展示 -->
            <el-col :span="18">
                <div v-if="!hasResults" class="empty-placeholder">
                    <el-empty description="请配置参数并运行分析以查看原因特异性风险比 (CS-HR) 和累积发生率 (CIF)" />
                </div>
                
                <div v-else class="results-area">
                    <el-tabs type="border-card">
                        <!-- 标签页 1：CIF 图表 -->
                        <el-tab-pane label="累积发生率 (CIF 图)">
                             <div class="plot-container">
                                 <div id="cif-plot" style="width:100%; height:500px;"></div>
                             </div>
                             <div class="methodology-box" v-if="cifResults?.methodology">
                                 <strong>方法学:</strong> {{ cifResults.methodology }}
                             </div>
                        </el-tab-pane>
                        
                        <!-- 标签页 2：原因特异性风险模型 -->
                        <el-tab-pane label="原因特异性模型 (CS 模型)">
                            <div v-for="model in modelResults.models" :key="model.event_type" style="margin-bottom: 30px;">
                                <div class="model-header">
                                    <h4 style="margin:0;">事件类型: {{ model.event_type }} (原因特异性 Cox 模型)</h4>
                                </div>
                                <el-table :data="model.summary" stripe border size="small">
                                    <el-table-column prop="variable" label="变量 (Variable)" />
                                    <el-table-column prop="hr" label="风险比 (HR)">
                                        <template #default="scope">{{ scope.row.hr.toFixed(3) }}</template>
                                    </el-table-column>
                                    <el-table-column label="95% CI">
                                        <template #default="scope">
                                            {{ scope.row.ci_lower.toFixed(3) }} - {{ scope.row.ci_upper.toFixed(3) }}
                                        </template>
                                    </el-table-column>
                                    <el-table-column prop="p_value" label="P 值">
                                        <template #default="scope">
                                            <span :style="{fontWeight: scope.row.p_value < 0.05 ? 'bold' : 'normal', color: scope.row.p_value < 0.05 ? 'red' : 'inherit'}">
                                                {{ scope.row.p_value < 0.001 ? '<0.001' : scope.row.p_value.toFixed(3) }}
                                            </span>
                                        </template>
                                    </el-table-column>
                                </el-table>
                            </div>
                            <div class="methodology-box" v-if="modelResults?.methodology">
                                 <strong>方法学 (Methodology):</strong> {{ modelResults.methodology }}
                             </div>
                        </el-tab-pane>

                        <!-- 标签页 3：Fine-Gray 模型 -->
                        <el-tab-pane label="Fine-Gray 模型 (预测)">
                            <div v-if="!modelResults.fine_gray_models || modelResults.fine_gray_models.length === 0">
                                <el-empty description="无法生成 Fine-Gray 模型 (可能因 lifelines 版本或数据问题)" />
                            </div>
                            <div v-else>
                                <div v-for="model in modelResults.fine_gray_models" :key="model.event_type" style="margin-bottom: 30px;">
                                    <div class="model-header">
                                        <h4 style="margin:0;">事件类型: {{ model.event_type }} (子分布风险模型)</h4>
                                    </div>
                                    <div v-if="model.error" style="color: red; padding: 10px;">
                                        Error: {{ model.error }}
                                    </div>
                                    <el-table v-else :data="model.summary" stripe border size="small">
                                        <el-table-column prop="variable" label="变量 (Variable)" />
                                        <el-table-column prop="hr" label="子分布风险比 (SHR)">
                                            <template #default="scope">{{ scope.row.hr.toFixed(3) }}</template>
                                        </el-table-column>
                                        <el-table-column label="95% CI">
                                            <template #default="scope">
                                                {{ scope.row.ci_lower.toFixed(3) }} - {{ scope.row.ci_upper.toFixed(3) }}
                                            </template>
                                        </el-table-column>
                                        <el-table-column prop="p_value" label="P 值">
                                            <template #default="scope">
                                                <span :style="{fontWeight: scope.row.p_value < 0.05 ? 'bold' : 'normal', color: scope.row.p_value < 0.05 ? 'red' : 'inherit'}">
                                                    {{ scope.row.p_value < 0.001 ? '<0.001' : scope.row.p_value.toFixed(3) }}
                                                </span>
                                            </template>
                                        </el-table-column>
                                    </el-table>
                                </div>
                                <div class="help-text" style="background: #fdf6ec; padding: 10px; margin-top:10px; color:#e6a23c">
                                    <strong>结果解读:</strong> SHR 描述了协变量对累积发生率函数（风险）的影响，适用于风险预测。
                                    原因特异性 HR (CS-HR, 见前一个标签页) 描述了在那些始终处于风险中的人群中，协变量对事件发生率的影响，适用于病因学探索。
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

const loading = ref(false) // 加载状态
const hasResults = ref(false) // 是否已有分析结果
const cifResults = ref(null) // CIF 分析结果 (包含方法学与数据)
const modelResults = ref(null) // 回归模型结果 (CS 与 Fine-Gray)

const variables = computed(() => props.metadata?.variables || [])
const numVars = computed(() => variables.value.filter(v => v.type === 'numeric' || v.type === 'integer' || true)) // 宽泛筛选
const catVars = computed(() => variables.value) // 分组通常允许所有类型

const isValid = computed(() => config.time_col && config.event_col && config.covariates.length > 0)

/**
 * 执行全套竞争风险分析。
 * 并行请求回归模型接口与 CIF 可视化接口。
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
        
        ElMessage.success('病因学研究请参考原因特异性模型，发生率研究请参考 CIF。')
        
        nextTick(() => {
            renderCIF(res2.data.cif_data)
        })
        
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '分析失败')
    } finally {
        loading.value = false
    }
}

/**
 * 渲染 CIF 曲线图。
 * @param {Array} cifData - 后端返回的曲线数据点数组。
 */
const renderCIF = (cifData) => {
    // cifData: [{group: 'A', event_type: 1, cif_data: [{x,y}...]}, ...]
    // 绘制曲线
    // X: 时间, Y: CIF 概率
    
    // 按事件类型还是按组别进行颜色映射？
    // 通常：颜色 = 组别，线型 = 事件类型？
    // 或者：颜色 = 事件类型，线型 = 组别？
    // 这里采用：如果有多个组别则颜色对应组别，否则颜色对应事件类型。
    
    const traces = []
    
    // 简单调色板
    const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    // 组别键
    const groups = [...new Set(cifData.map(d => d.group))]
    
    cifData.forEach(item => {
        const x = item.cif_data.map(p => p.x)
        const y = item.cif_data.map(p => p.y)
        
        // 确定样式
        // 如果有多个组别：按组别着色
        // 如果有多个事件：按事件类型设置虚线样式？
        
        let color = '#333'
        if (groups.length > 1) {
            const gIdx = groups.indexOf(item.group)
            color = colors[gIdx % colors.length]
        } else {
             const eIdx = item.event_type - 1
             color = colors[eIdx % colors.length]
        }
        
        let dash = 'solid'
        // 如果存在多个事件，为不同事件设置不同的虚线样式
        // item.event_type 理想情况下为 1, 2...
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
        title: '累积发生率函数 (Aalen-Johansen)',
        xaxis: { title: '时间 (Time)' },
        yaxis: { title: '累积发生概率', range: [0, 1] },
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
