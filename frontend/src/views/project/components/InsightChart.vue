<template>
  <div class="insight-chart-container">
    <div class="chart-header" v-if="title">
      <div class="title-group">
        <el-icon v-if="publicationReady" style="color: #67C23A; font-size: 14px;"><CircleCheckFilled /></el-icon>
        <span>{{ title }}</span>
      </div>
      <div class="actions">
        <el-switch
            v-model="internalPubReady"
            inline-prompt
            active-text="学术模式"
            inactive-text="普通模式"
            style="margin-right: 15px; --el-switch-on-color: #67C23A"
        />
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
import { onMounted, watch, onBeforeUnmount, nextTick, ref } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { ArrowDown, CircleCheckFilled } from '@element-plus/icons-vue'
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
    default: () => ({ 
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d']
    })
  },
  height: {
    type: String,
    default: '400px'
  },
  publicationReady: {
    type: Boolean,
    default: false
  }
})

const internalPubReady = ref(props.publicationReady)
watch(() => props.publicationReady, (newVal) => {
    internalPubReady.value = newVal
})

let chartInstance = null

const getMergedLayout = () => {
    // 通用基础样式
    const baseLayout = {
        font: { 
            family: internalPubReady.value ? '"Times New Roman", Times, serif' : 'system-ui, -apple-system, sans-serif',
            size: internalPubReady.value ? 14 : 12,
            color: '#212121'
        },
        margin: { t: 60, r: 40, b: 60, l: 70 },
        template: 'plotly_white',
        colorway: ['#3B71CA', '#D32F2F', '#2E7D32', '#E6A23C', '#9C27B0'], // IDS 标准配色
        hovermode: 'closest',
        plot_bgcolor: 'rgba(0,0,0,0)',
        paper_bgcolor: 'rgba(0,0,0,0)',
    }

    // 学术发表模式特定样式 (Academic Theme)
    if (props.publicationReady) {
        Object.assign(baseLayout, {
            xaxis: {
                showline: true,
                linewidth: 2,
                linecolor: 'black',
                mirror: true,
                gridcolor: 'rgba(0,0,0,0.05)',
                ticks: 'outside',
                tickwidth: 2,
                title: { font: { size: 16, color: 'black' } }
            },
            yaxis: {
                showline: true,
                linewidth: 2,
                linecolor: 'black',
                mirror: true,
                gridcolor: 'rgba(0,0,0,0.05)',
                ticks: 'outside',
                tickwidth: 2,
                title: { font: { size: 16, color: 'black' } }
            },
            legend: {
                borderwidth: 1,
                bordercolor: 'black',
                bgcolor: 'white',
                font: { size: 12 }
            }
        })
    } else {
        // 现代交互模式样式
        Object.assign(baseLayout, {
            xaxis: { gridcolor: '#f0f0f0' },
            yaxis: { gridcolor: '#f0f0f0' },
            legend: { font: { size: 12 } }
        })
    }

    // 递归深度合并布局 (除了嵌套对象如 xaxis/yaxis 可能需要特殊处理，简单覆盖即可)
    return { ...baseLayout, ...props.layout }
}

const renderChart = () => {
  const el = document.getElementById(props.chartId)
  if (!el) return

  Plotly.newPlot(props.chartId, props.data, getMergedLayout(), props.config)
    .then((gd) => {
        chartInstance = gd
    })
}

const handleExport = async (format) => {
  try {
    const el = document.getElementById(props.chartId)
    if (!el) return
    
    // 导出时暂时强制使用高质量背景
    const exportConfig = {
        format: format,
        width: 1200,
        height: 800,
        filename: props.title ? props.title.replace(/\s+/g, '_').toLowerCase() : 'insight_chart',
        scale: format === 'png' ? 4 : 1 // 提高到 4 倍以获得印刷级品质
    }
    
    await Plotly.downloadImage(el, exportConfig)
    ElMessage.success('高清图片导出成功，符合学术发表要求')
  } catch (error) {
    console.error(error)
    ElMessage.error('图片导出失败')
  }
}

// 响应数据变化
watch(() => [props.data, props.layout], () => {
    const el = document.getElementById(props.chartId)
    if (el) {
        Plotly.react(props.chartId, props.data, getMergedLayout(), props.config)
    }
}, { deep: true })

watch(internalPubReady, (newVal) => {
    const el = document.getElementById(props.chartId)
    if (el) {
        Plotly.react(props.chartId, props.data, getMergedLayout(), props.config)
    }
})

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
    margin-bottom: 15px;
    font-weight: 600;
    color: #303133;
    padding: 2px 5px;
    border-left: 4px solid #3B71CA;
}
.title-group {
    display: flex;
    align-items: center;
    gap: 8px;
}
.actions {
    display: flex;
    align-items: center;
}
.chart-content {
    width: 100%;
    background: white;
    border-radius: 4px;
}
</style>
