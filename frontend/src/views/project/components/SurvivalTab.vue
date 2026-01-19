
<template>
  <div class="survival-container">
    <el-row :gutter="20">
        <!-- Config Panel -->
        <el-col :span="6">
            <el-card class="box-card">
                <template #header>
                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <span>参数配置</span>
                        <el-button 
                            type="primary" 
                            link 
                            :icon="MagicStick" 
                            @click="suggestRoles"
                            :loading="isSuggesting"
                        >
                            AI 智能推荐
                        </el-button>
                    </div>
                </template>
                <el-form label-position="top">
                    <!-- Guidance Alert -->
                    <el-alert
                        title="生存分析指南"
                        type="info"
                        show-icon
                        :closable="false"
                        style="margin-bottom: 20px"
                    >
                        <template #default>
                            <div style="font-size: 13px; color: #606266; line-height: 1.6;">
                                <li><b>时间变量</b>: 随访时间（如：月、天）。</li>
                                <li><b>事件变量</b>: 终点结局（通常 1=死亡/发病，0=删失/存活）。</li>
                                <li><b>Log-rank P</b>: 评估各组生存曲线是否有显著差异。<b>P < 0.05</b> 代表差异有统计学意义。</li>
                            </div>
                        </template>
                    </el-alert>
                    <el-form-item label="时间变量 (Time)">
                        <el-select v-model="config.time" placeholder="选择时间变量" filterable style="width: 100%">
                             <el-option v-for="opt in numericOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-form-item label="事件变量 (Event)">
                        <el-select v-model="config.event" placeholder="选择事件变量 (0/1)" filterable style="width: 100%">
                             <el-option v-for="opt in numericOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-form-item label="分组变量 (Group By)">
                         <el-select v-model="config.group" placeholder="可选 (Optional)" clearable filterable style="width: 100%">
                             <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-button type="primary" style="width: 100%" @click="generatePlot" :loading="loading">绘制曲线 (Draw KM Plot)</el-button>
                </el-form>
            </el-card>
        </el-col>

        <!-- Plot Panel -->
        <el-col :span="18">
            <el-card class="box-card" v-loading="loading">
                 <template #header>
                     <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span>生存分析 (Kaplan-Meier)</span>
                            <el-tag v-if="pValue" type="info">
                                Log-Rank P: {{ pValue }}
                            </el-tag>
                            <el-button 
                                v-if="pValue"
                                type="primary" 
                                size="small" 
                                @click="runAIInterpretation" 
                                :loading="isInterpreting"
                                :icon="MagicStick"
                                class="ai-km-btn"
                            >
                                AI 深度解读
                            </el-button>
                            <el-switch
                                v-if="rawPlotData.length > 0"
                                v-model="isGlobalPublicationReady"
                                inline-prompt
                                active-text="学术绘图"
                                inactive-text="普通预览"
                                style="--el-switch-on-color: #67C23A; margin-left: 10px;"
                            />
                        </div>
                    </div>
                </template>
                
                <InterpretationPanel 
                    v-if="kmInterpretation"
                    :interpretation="kmInterpretation"
                />
                
                <InsightChart
                    v-if="rawPlotData.length > 0"
                    chartId="km-plot"
                    title="Kaplan-Meier 生存估计 (Survival Estimates)"
                    :data="kmPlotData"
                    :layout="kmLayout"
                    height="500px"
                    :publicationReady="isGlobalPublicationReady"
                />
                <el-empty v-else description="暂无图表数据，请配置参数后点击绘制" />
                
            </el-card>
        </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import { MagicStick } from '@element-plus/icons-vue'
import InterpretationPanel from './InterpretationPanel.vue'
import InsightChart from './InsightChart.vue'
import { useVariableOptions } from '../../../composables/useVariableOptions'

/**
 * SurvivalTab.vue
 * 生存分析 (Kaplan-Meier) 标签页。
 * 
 * 职责：
 * 1. 提供 KM 生存曲线的参数配置（时间、事件、分组）。
 * 2. 绘制具有学术发表质量的阶梯状生存曲线图。
 * 3. 显示 Log-rank 检验结果，并提供智能化的统计解读。
 * 4. 支持复制符合论文要求的方法学描述。
 */

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const isGlobalPublicationReady = ref(false)
const loading = ref(false) // 加载状态
const isInterpreting = ref(false)
const pValue = ref(null)    // Log-rank 检验的 P 值
const kmInterpretation = ref(null) // 智能解读对象
const rawPlotData = ref([])
const isSuggesting = ref(false)

const config = reactive({
    time: null,
    event: null,
    group: null
})

// 使用公共 Composable 提取变量选项
const { 
    allOptions: variableOptions, 
    numericOptions 
} = useVariableOptions(computed(() => props.metadata))

const kmMethodology = ref('')

/**
 * 向后端请求 KM 分析数据。
 */
const generatePlot = async () => {
    if (!config.time || !config.event) {
        ElMessage.warning("请选择时间变量和事件变量")
        return
    }

    loading.value = true
    pValue.value = null
    kmInterpretation.value = null
    kmMethodology.value = ''
    
    try {
        const { data } = await api.post('/statistics/km', {
            dataset_id: props.datasetId,
            ...config
        })
        
        pValue.value = data.km_data.p_value
        kmInterpretation.value = data.km_data.interpretation
        kmMethodology.value = data.km_data.methodology
        rawPlotData.value = data.km_data.plot_data
        
    } catch (error) {
        ElMessage.error(error.response?.data?.message || "绘图失败")
    } finally {
        loading.value = false
    }
}

const runAIInterpretation = async () => {
    if (rawPlotData.value.length === 0) return
    
    isInterpreting.value = true
    try {
        const { data } = await api.post('/statistics/ai-interpret-km', {
            plot_data: rawPlotData.value,
            p_value: pValue.value
        })
        
        kmInterpretation.value = {
            text: data.analysis,
            is_ai: true,
            level: 'info'
        }
        ElMessage.success("AI 深度解析完成")
    } catch (e) {
        console.error("AI KM Interpretation failed", e)
        ElMessage.error(e.response?.data?.message || "AI 解析失败")
    } finally {
        isInterpreting.value = false
    }
}

const suggestRoles = async () => {
    isSuggesting.value = true
    try {
        const { data } = await api.post('/statistics/ai-suggest-roles', {
            dataset_id: props.datasetId,
            analysis_type: 'km'
        })
        
        config.time = data.time || config.time
        config.event = data.event || config.event
        config.group = data.group || config.group
        
        ElMessage({
            message: `AI 已为您推荐生存分析的最佳变量角色。\n理由: ${data.reason || '基于随访数据特征推荐'}`,
            type: 'success',
            duration: 5000
        })
    } catch (e) {
        console.error("AI Role suggestion failed", e)
        ElMessage.error(e.response?.data?.message || "AI 推荐失败")
    } finally {
        isSuggesting.value = false
    }
}

const copyMethodology = () => {
    if (!kmMethodology.value) {
        ElMessage.info('暂无方法学内容')
        return
    }
    navigator.clipboard.writeText(kmMethodology.value).then(() => {
        ElMessage.success('方法学段落已复制')
    }).catch(err => {
        ElMessage.error('复制失败')
    })
}

const kmPlotData = computed(() => {
    return rawPlotData.value.map(g => ({
        x: g.times,
        y: g.probs,
        mode: 'lines',
        name: g.name,
        line: { shape: 'hv', width: 3 },
        type: 'scatter'
    }))
})

const kmLayout = computed(() => ({
    xaxis: { title: '时间 (Time)' },
    yaxis: { title: '生存概率 (Survival Probability)', range: [0, 1.05] },
    showlegend: true
}))


// 导出和渲染逻辑现在由 InsightChart 托管
</script>

<style scoped>
.survival-container {
    padding: 20px;
}
.ai-km-btn {
    background: linear-gradient(45deg, #6366f1, #a855f7);
    border: none;
    transition: all 0.3s ease;
}
.ai-km-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
}
</style>
