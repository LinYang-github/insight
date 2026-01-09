
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
                    <el-form-item label="时间变量 (Time)">
                        <el-select v-model="config.time" placeholder="Select Time" filterable style="width: 100%">
                             <el-option v-for="opt in numericOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-form-item label="事件变量 (Event)">
                        <el-select v-model="config.event" placeholder="Select Event (0/1)" filterable style="width: 100%">
                             <el-option v-for="opt in numericOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-form-item label="分组变量 (Group By)">
                         <el-select v-model="config.group" placeholder="Optional" clearable filterable style="width: 100%">
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
                            <span>Survival Analysis (Kaplan-Meier)</span>
                            <el-tag v-if="pValue" :type="pValue === 'N/A' ? 'info' : (parseFloat(pValue) < 0.05 ? 'danger' : 'success')">
                                Log-Rank P: {{ pValue }}
                            </el-tag>
                        </div>
                        <el-dropdown trigger="click" @command="downloadPlot">
                            <el-button type="primary" size="small">
                                导出图片 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                            </el-button>
                            <template #dropdown>
                                <el-dropdown-menu>
                                    <el-dropdown-item command="png">High-Res PNG (300dpi)</el-dropdown-item>
                                    <el-dropdown-item command="svg">Vector SVG</el-dropdown-item>
                                </el-dropdown-menu>
                            </template>
                        </el-dropdown>
                    </div>
                </template>
                
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

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const loading = ref(false)
const pValue = ref(null)

const config = reactive({
    time: null,
    event: null,
    group: null
})

const variableOptions = computed(() => {
    if (!props.metadata) return []
    // Assuming metadata is dict {col: type} or derived from it.
    // If metadata structure is { variables: [{name, type}, ...] } from previous context
    if (props.metadata.variables) {
         return props.metadata.variables.map(v => ({ label: v.name, value: v.name, type: v.type }))
    }
    // Fallback if metadata is simple dict
    return Object.keys(props.metadata).map(k => ({ label: k, value: k }))
})

const numericOptions = computed(() => variableOptions.value) // Simplified for MVP

const generatePlot = async () => {
    if (!config.time || !config.event) {
        ElMessage.warning("请选择时间变量和事件变量")
        return
    }

    loading.value = true
    pValue.value = null
    
    try {
        const { data } = await api.post('/statistics/km', {
            dataset_id: props.datasetId,
            ...config
        })
        
        pValue.value = data.km_data.p_value
        renderPlot(data.km_data.plot_data)
        
    } catch (error) {
        ElMessage.error(error.response?.data?.message || "绘图失败")
    } finally {
        loading.value = false
    }
}

const renderPlot = (plotData) => {
    const traces = []
    
    plotData.forEach(g => {
        // Main Line
        traces.push({
            x: g.times,
            y: g.probs,
            mode: 'lines',
            name: g.name,
            line: { shape: 'hv' }, // Step shape for KM
            type: 'scatter'
        })
        
        // Censored markers? (Not passed from backend yet, MVP just lines)
        
        // CI Area (Optional, maybe cluttering? Let's skip for simple MVP or add as transparent fill)
    })
    
    const layout = {
        title: 'Kaplan-Meier Survival Estimates',
        xaxis: { title: 'Time' },
        yaxis: { title: 'Survival Probability', range: [0, 1.05] },
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
