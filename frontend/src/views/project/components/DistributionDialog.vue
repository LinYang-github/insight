<template>
  <el-dialog
    v-model="visible"
    :title="`变量分布: ${variable}`"
    width="600px"
    destroy-on-close
    append-to-body
  >
    <div v-loading="loading" class="distribution-body">
      <div v-if="distData" id="distribution-plot" style="width: 100%; height: 400px;"></div>
      <div v-if="distData" class="dist-stats">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="样本量 (N)">{{ distData.stats.n }}</el-descriptions-item>
          <el-descriptions-item v-if="distData.type === 'numeric'" label="均值 (Mean)">
            {{ distData.stats.mean.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="distData.type === 'numeric'" label="标准差 (SD)">
            {{ distData.stats.std.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item v-if="distData.type === 'categorical'" label="唯一值">
            {{ distData.stats.unique }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
/**
 * DistributionDialog.vue
 * 变量分布查看弹窗组件。
 * 
 * 职责：
 * 1. 异步获取特定变量的统计分布数据。
 * 2. 针对数值型变量绘制直方图 (Histogram) 并叠加正态分布拟合曲线。
 * 3. 针对分类型变量绘制环形图 (Donut Chart) 展示比例。
 */
import { ref, watch, nextTick } from 'vue'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
  datasetId: Number,
  variable: String,
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const loading = ref(false)  // 加载状态
const distData = ref(null) // 变量分布统计数据

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val && props.variable) {
    fetchDistribution()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

/**
 * 向后端请求变量分布与汇总统计指标。
 */
const fetchDistribution = async () => {
  loading.value = true
  distData.value = null
  try {
    const { data } = await api.post('/statistics/distribution', {
      dataset_id: props.datasetId,
      variable: props.variable
    })
    distData.value = data.distribution
    nextTick(() => {
        renderPlot()
    })
  } catch (err) {
    console.error("Failed to fetch distribution", err)
  } finally {
    loading.value = false
  }
}

/**
 * 渲染分布图表。
 */
const renderPlot = () => {
  if (!distData.value) return
  
  const d = distData.value
  const traces = []

  if (d.type === 'numeric') {
    // Histogram
    const binEdges = d.bins.edges
    const counts = d.bins.counts
    
    // Convert edges to centers for Plotly bar or just use edges
    traces.push({
      x: binEdges.slice(0, -1),
      y: counts,
      type: 'bar',
      name: '频率 (Frequency)',
      marker: { color: '#3B71CA', opacity: 0.7 }
    })

    // Normal Curve
    if (d.curve.x.length > 0) {
        // Scale curve to match histogram height roughly
        // max_y_norm * total_count * bin_width
        const binWidth = binEdges[1] - binEdges[0]
        const total = d.stats.n
        const scaledY = d.curve.y.map(y => y * total * binWidth)
        
        traces.push({
            x: d.curve.x,
            y: scaledY,
            mode: 'lines',
            name: '正态拟合 (Normal Fit)',
            line: { color: '#D32F2F', width: 2 }
        })
    }
  } else {
    // Categorical Pie or Bar
    const labels = Object.keys(d.counts)
    const values = Object.values(d.counts)
    traces.push({
      labels: labels,
      values: values,
      type: 'pie',
      hole: 0.4,
      marker: { colors: ['#3B71CA', '#E6A23C', '#67C23A', '#909399', '#F56C6C'] }
    })
  }

  const layout = {
    margin: { t: 30, b: 40, l: 50, r: 20 },
    showlegend: d.type === 'numeric',
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)'
  }

  Plotly.newPlot('distribution-plot', traces, layout)
}
</script>

<style scoped>
.distribution-body {
  min-height: 450px;
}
.dist-stats {
  margin-top: 15px;
}
</style>
