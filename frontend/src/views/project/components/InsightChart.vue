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
            <el-dropdown-item command="png">高清图片 (PNG, 300dpi)</el-dropdown-item>
            <el-dropdown-item command="svg">矢量图 (SVG)</el-dropdown-item>
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
    type: Array, // Plotly 数据数组
    required: true
  },
  layout: {
    type: Object, // Plotly 布局对象
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

    // 合并默认布局与传入布局
    const defaultLayout = {
      font: { family: 'Helvetica Neue, Arial, sans-serif' },
      margin: { t: 40, r: 20, b: 40, l: 60 },
      colorway: ['#3B71CA', '#E6A23C', '#2E7D32', '#D32F2F', '#909399'], // IDS 标准配色方案
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
        scale: format === 'png' ? 3 : 1 // PNG 模式下使用 3 倍缩放以保证清晰度
    })
    ElMessage.success('图片导出成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('图片导出失败')
  }
}

// 响应数据变化
watch(() => [props.data, props.layout], () => {
    // 使用 Plotly.react 进行高效局部更新
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
