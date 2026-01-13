
<template>
  <div class="survival-container">
    <el-row :gutter="20">
        <!-- Config Panel -->
        <el-col :span="6">
            <el-card class="box-card">
                <template #header>
                    <div class="card-header">
                        <span>参数配置</span>
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
                        </div>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <el-button v-if="kmMethodology" type="primary" size="small" @click="copyMethodology" plain>复制方法学 (Methods)</el-button>
                            <el-dropdown trigger="click" @command="downloadPlot">
                                <el-button type="primary" size="small">
                                    导出图片 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                                </el-button>
                                <template #dropdown>
                                    <el-dropdown-menu>
                                        <el-dropdown-item command="png">高清 PNG (300dpi)</el-dropdown-item>
                                        <el-dropdown-item command="svg">矢量 SVG (Vector)</el-dropdown-item>
                                    </el-dropdown-menu>
                                </template>
                            </el-dropdown>
                        </div>
                    </div>
                </template>
                
                <InterpretationPanel 
                    v-if="kmInterpretation"
                    :interpretation="kmInterpretation"
                />
                
                <div id="km-plot" style="width: 100%; height: 500px;"></div>
                
            </el-card>
        </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'
import { ArrowDown } from '@element-plus/icons-vue'
import InterpretationPanel from './InterpretationPanel.vue'

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

const loading = ref(false) // 加载状态
const pValue = ref(null)    // Log-rank 检验的 P 值
const kmInterpretation = ref(null) // 智能解读对象

const config = reactive({
    time: null,
    event: null,
    group: null
})

const variableOptions = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables.map(v => ({ 
        label: v.name, 
        value: v.name, 
        type: v.type 
    }))
})

const numericOptions = computed(() => {
    return variableOptions.value.filter(v => v.type === 'continuous')
})

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
        
        renderPlot(data.km_data.plot_data)
        
    } catch (error) {
        ElMessage.error(error.response?.data?.message || "绘图失败")
    } finally {
        loading.value = false
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

/**
 * 将后端返回的 KM 数据绘制成图表。
 * 
 * @param {Array} plotData - 后端返回的分组数据 [{name: 'GroupA', times: [], probs: []}, ...]
 * @description
 * KM 曲线是阶梯状 (Step Function)，因此 line.shape 必须设为 'hv' (Horizontal-Vertical)。
 * Log-rank 检验用于比较两个或多个组的生存曲线是否存在显著差异。
 */
const renderPlot = (plotData) => {
    const traces = []
    
    plotData.forEach(g => {
        // 主曲线
        traces.push({
            x: g.times,
            y: g.probs,
            mode: 'lines',
            name: g.name,
            line: { shape: 'hv' }, // 关键配置：阶梯线
            type: 'scatter'
        })
        
        // Censored markers? (Not passed from backend yet, MVP just lines)
        
        // CI Area (Optional, maybe cluttering? Let's skip for simple MVP or add as transparent fill)
    })
    
    const layout = {
        title: 'Kaplan-Meier 生存估计 (Survival Estimates)',
        xaxis: { title: '时间 (Time)' },
        yaxis: { title: '生存概率 (Survival Probability)', range: [0, 1.05] },
        showlegend: true
    }
    
    Plotly.newPlot('km-plot', traces, layout, {responsive: true})
}


const downloadPlot = async (format = 'png') => {
    try {
        const el = document.getElementById('km-plot')
        if (!el) return
        
        await Plotly.downloadImage(el, {
            format: format,
            width: 1200,
            height: 800,
            filename: 'kaplan_meier_plot',
            scale: format === 'png' ? 3 : 1
        })
    } catch (error) {
        ElMessage.error('图片导出失败')
    }
}
</script>

<style scoped>
.survival-container {
    padding: 20px;
}
</style>
