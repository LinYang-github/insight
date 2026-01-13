<template>
  <div class="eda-container">
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="5" animated />
    </div>
    
    <div v-else-if="!stats || stats.length === 0">
      <el-empty description="暂无数据预览或 EDA 信息" />
    </div>
    
    <div v-else>
      <el-tabs v-model="activeTab">
        <!-- Basic Statistics -->
        <el-tab-pane label="描述性统计" name="stats">
            <el-table :data="stats" style="width: 100%" height="500" stripe border>
                <el-table-column prop="name" label="变量名" fixed width="150" />
                <el-table-column prop="type" label="类型" width="100" />
                <el-table-column prop="count" label="计数" width="100" />
                <el-table-column prop="missing" label="缺失值" width="100" />
                
                <!-- Numeric columns -->
                <el-table-column label="数值统计">
                    <el-table-column prop="mean" label="均值" width="100">
                        <template #default="scope">{{ formatNum(scope.row.mean) }}</template>
                    </el-table-column>
                    <el-table-column prop="std" label="标准差" width="100">
                         <template #default="scope">{{ formatNum(scope.row.std) }}</template>
                    </el-table-column>
                    <el-table-column prop="min" label="Min" width="80">
                         <template #default="scope">{{ formatNum(scope.row.min) }}</template>
                    </el-table-column>
                    <el-table-column prop="q25" label="25%" width="80">
                         <template #default="scope">{{ formatNum(scope.row.q25) }}</template>
                    </el-table-column>
                    <el-table-column prop="q50" label="中位数 (Median)" width="80">
                         <template #default="scope">{{ formatNum(scope.row.q50) }}</template>
                    </el-table-column>
                    <el-table-column prop="q75" label="75%" width="80">
                         <template #default="scope">{{ formatNum(scope.row.q75) }}</template>
                    </el-table-column>
                    <el-table-column prop="max" label="Max" width="80">
                         <template #default="scope">{{ formatNum(scope.row.max) }}</template>
                    </el-table-column>
                </el-table-column>

                 <!-- Categorical columns -->
                <el-table-column label="分类统计">
                    <el-table-column prop="unique_count" label="唯一值" width="80" />
                    <el-table-column label="Top Values" min-width="200">
                        <template #default="scope">
                            <span v-if="scope.row.top_values">
                                {{ scope.row.top_values.join(', ') }}
                            </span>
                        </template>
                    </el-table-column>
                </el-table-column>
            </el-table>
        </el-tab-pane>
        
        <!-- Visualization -->
        <el-tab-pane label="数据可视化" name="viz">
             <el-row :gutter="20">
                <!-- Correlation Heatmap -->
                <el-col :span="12">
                    <el-card shadow="hover">
                        <template #header>
                            <span>相关性热力图 (Pearson)</span>
                        </template>
                        <div id="corr-plot" style="width: 100%; height: 400px;"></div>
                    </el-card>
                </el-col>
                
                <!-- Distribution Plot -->
                 <el-col :span="12">
                    <el-card shadow="hover">
                        <template #header>
                            <div class="dist-header">
                                <span>单变量分布</span>
                                <el-select v-model="selectedDistVar" placeholder="选择变量" size="small" @change="fetchDistribution">
                                    <el-option v-for="item in stats" :key="item.name" :label="item.name" :value="item.name" />
                                </el-select>
                            </div>
                        </template>
                         <div id="dist-plot" style="width: 100%; height: 400px;"></div>
                    </el-card>
                </el-col>
             </el-row>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
/**
 * EdaTab.vue
 * 探索性数据分析 (Exploratory Data Analysis) 组件。
 * 
 * 职责：
 * 1. 展示各变量的基础统计指标（均值、标准差、缺失率等）。
 * 2. 渲染变量间的相关性热力图，帮助用户识别共线性。
 * 3. 渲染单变量分布图（直方图/条形图），识别异常值或偏偏态分布。
 */
import { ref, onMounted, watch } from 'vue'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'
import { ElMessage } from 'element-plus'

const props = defineProps({
  datasetId: {
    type: Number,
    required: false
  }
})

const loading = ref(false) // 加载状态
const stats = ref([]) // 描述性统计结果
const activeTab = ref('stats') // 当前活跃标签页
const selectedDistVar = ref('') // 当前选中的分布查看变量

const formatNum = (val) => {
    if (val === null || val === undefined) return '-'
    if (typeof val === 'number') return val.toFixed(2)
    return val
}

/**
 * 获取数据集的全局描述性统计汇总数据。
 */
const fetchStats = async () => {
    if (!props.datasetId) return
    loading.value = true
    try {
        const { data } = await api.get(`/eda/stats/${props.datasetId}`)
        stats.value = data.stats
        if (stats.value.length > 0) {
            selectedDistVar.value = stats.value[0].name
        }
    } catch (error) {
        console.error(error)
        ElMessage.error('无法获取统计信息')
    } finally {
        loading.value = false
    }
}

/**
 * 获取并绘制变量间的 Pearson 相关性热力图。
 */
const fetchCorrelation = async () => {
    if (!props.datasetId) return
    try {
        const { data } = await api.get(`/eda/correlation/${props.datasetId}`)
        if (!data.columns || data.columns.length === 0) return
        
        const layout = {
             margin: { t: 20, r: 20, l: 100, b: 100 },
             height: 400
        }
        
        const plotData = [{
            z: data.matrix,
            x: data.columns,
            y: data.columns,
            type: 'heatmap',
            colorscale: 'Viridis'
        }]
        
        Plotly.newPlot('corr-plot', plotData, layout)
    } catch (error) {
        console.error(error)
    }
}

/**
 * 获取选定变量的分布数据点，并渲染为直方图/条形图。
 */
const fetchDistribution = async () => {
    if (!props.datasetId || !selectedDistVar.value) return
    try {
        const { data } = await api.get(`/eda/distribution/${props.datasetId}/${selectedDistVar.value}`)
        
        const layout = {
            margin: { t: 20, r: 20, l: 50, b: 50 },
            height: 400,
            xaxis: { title: selectedDistVar.value },
            yaxis: { title: '频数 (Count)' }
        }
        
        const plotData = [{
            x: data.x,
            y: data.y, // For histograms from backend (bins) -> usually bar chart of bins
            type: 'bar' // Simplified as bar chart of pre-binned data or categories
        }]

        if(data.type === 'numerical') {
            // Backend returns bin centers as x, counts as y. Bar chart is fine approximation.
        }
        
        Plotly.newPlot('dist-plot', plotData, layout)
        
    } catch (error) {
        console.error(error)
    }
}

watch(() => props.datasetId, (newVal) => {
    if (newVal) {
        fetchStats()
    }
}, { immediate: true })

watch(activeTab, (newVal) => {
    if (newVal === 'viz') {
        // Use timeout to ensure DOM is ready for Plotly
        setTimeout(() => {
            fetchCorrelation()
            fetchDistribution()
        }, 100)
    }
})

</script>

<style scoped>
.dist-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
</style>
