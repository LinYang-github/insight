<template>
  <div class="insight-chart-container">
    <div class="chart-header" v-if="title">
      <span>{{ title }}</span>
      <el-dropdown trigger="click" @command="handleExport">
        <el-button type="primary" link size="small">
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
    <div :id="chartId" class="chart-content" :style="{ height: height }"></div>
  </div>
</template>

<script setup>
/**
 * InsightChart.vue
 * 
 * 通用 Plotly 图表封装组件。
 * 
 * 功能：
 * 1. 自动响应式调整大小 (Responsive)。
 * 2. 统一的图片导出逻辑 (High-Res PNG / SVG)。
 * 3. 简化 Plotly 调用接口。
 */
import { onMounted, watch, onBeforeUnmount, nextTick } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  chartId: {
    type: String,
    required: true
  },
  title: {
    type: String,
    default: ''
  },
  data: {
    type: Array, // Plotly data array
    required: true
  },
  layout: {
    type: Object, // Plotly layout object
    default: () => ({})
  },
  config: {
    type: Object,
    default: () => ({ responsive: true })
  },
  height: {
    type: String,
    default: '400px'
  }
})

let chartInstance = null

const renderChart = () => {
  const el = document.getElementById(props.chartId)
  if (!el) return

  // Merge default layout with props layout
  const defaultLayout = {
    font: { family: 'Helvetica Neue, Arial, sans-serif' },
    margin: { t: 40, r: 20, b: 40, l: 60 },
    colorway: ['#3B71CA', '#E6A23C', '#2E7D32', '#D32F2F', '#909399'], // IDS Palette
    ...props.layout
  }

  Plotly.newPlot(props.chartId, props.data, defaultLayout, props.config)
    .then((gd) => {
        chartInstance = gd
    })
}

const handleExport = async (format) => {
  try {
    const el = document.getElementById(props.chartId)
    if (!el) return
    
    await Plotly.downloadImage(el, {
        format: format,
        width: 1200,
        height: 800,
        filename: props.title || 'insight_chart',
        scale: format === 'png' ? 3 : 1 // High Res for PNG
    })
    ElMessage.success('图片导出成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('图片导出失败')
  }
}

// React to data changes
watch(() => [props.data, props.layout], () => {
    // Use Plotly.react for efficient updates
    const el = document.getElementById(props.chartId)
    if (el) {
         const defaultLayout = {
            font: { family: 'Helvetica Neue, Arial, sans-serif' },
            margin: { t: 40, r: 20, b: 40, l: 60 },
            colorway: ['#3B71CA', '#E6A23C', '#2E7D32', '#D32F2F', '#909399'],
            ...props.layout
        }
        Plotly.react(props.chartId, props.data, defaultLayout, props.config)
    }
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    renderChart()
  })
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize)
})

const handleResize = () => {
    const el = document.getElementById(props.chartId)
    if (el) {
        Plotly.Plots.resize(el)
    }
}
</script>

<style scoped>
.insight-chart-container {
    width: 100%;
}
.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    font-weight: bold;
    color: #606266;
}
.chart-content {
    width: 100%;
}
</style>
