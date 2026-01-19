<template>
  <div class="nomogram-container">
     <el-row :gutter="20">
         
         <!-- Canvas Area -->
         <el-col :span="16">
             <div class="canvas-wrapper" ref="canvasWrapper">
                 <div class="canvas-toolbar">
                     <span>交互式列线图 (Interactive Nomogram)</span><div><el-button size="small" type="success" link @click="$emit('view-calibration')">查看校准曲线</el-button>
                     <el-button size="small" type="primary" link @click="exportImage">下载图片</el-button></div>
                 </div>
                 
                 <svg ref="svgRef" :width="width" :height="height" class="nomogram-svg">
                     <defs>
                         <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                             <path d="M 0 0 L 10 5 L 0 10 z" fill="#333" />
                         </marker>
                         <linearGradient id="distGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                             <stop offset="0%" style="stop-color:#3B71CA;stop-opacity:0.2" />
                             <stop offset="100%" style="stop-color:#3B71CA;stop-opacity:0.05" />
                         </linearGradient>
                     </defs>
                     
                     <!-- 1. Header: Points Scale -->
                     <g transform="translate(0, 40)">
                         <text x="10" y="0" font-weight="bold" font-size="13" fill="#303133">分值 (Points)</text>
                         <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="#303133" stroke-width="2" />
                         <!-- Ticks 0-100 -->
                         <g v-for="t in pointsTicks" :key="t">
                             <line :x1="scaleX(t)" y1="0" :x2="scaleX(t)" y2="-6" stroke="#303133" stroke-width="1" />
                             <text :x="scaleX(t)" y="-12" text-anchor="middle" font-size="11" fill="#606266">{{ t }}</text>
                         </g>
                     </g>
                     
                     <!-- 2. Variables -->
                     <g v-for="(axis, idx) in spec.axes" :key="axis.name" :transform="`translate(0, ${100 + idx * 60})`">
                         <!-- Label -->
                         <text x="10" y="0" font-weight="600" font-size="13" fill="#303133">{{ axis.name }}</text>
                         
                         <!-- Secondary/Helper Line -->
                         <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="#EBEEF5" stroke-dasharray="2,2" />
                         
                         <!-- Continuous Axis -->
                         <template v-if="axis.type === 'continuous'">
                             <!-- Distribution Area (Density) -->
                             <path 
                               v-if="axis.distribution && axis.distribution.length > 0"
                               :d="generateDensityPath(axis)" 
                               fill="url(#distGradient)" 
                               stroke="#3B71CA" 
                               stroke-width="0.5" 
                               opacity="0.6"
                               transform="translate(0, -2)"
                             />

                             <!-- Main Line -->
                             <line :x1="scaleX(axis.points[String(axis.min)])" y1="0" :x2="scaleX(axis.points[String(axis.max)])" y2="0" stroke="#333" stroke-width="1.5" />
                             
                             <!-- Ticks -->
                             <g v-for="(pt, val) in axis.points" :key="val">
                                 <line :x1="scaleX(pt)" y1="0" :x2="scaleX(pt)" y2="-5" stroke="#333" />
                                 <text :x="scaleX(pt)" y="-10" text-anchor="middle" font-size="10" fill="#606266">{{ parseFloat(val) }}</text>
                             </g>
                             
                             <!-- User Value Marker -->
                             <g v-if="userInputs[axis.name] !== undefined" :transform="`translate(${scaleX(calculateVariablePoints(axis))}, 0)`">
                                 <circle r="4" fill="#D32F2F" />
                                 <path d="M 0 0 L 0 -15" stroke="#D32F2F" stroke-width="1" stroke-dasharray="2,2" />
                             </g>
                         </template>
                         
                         <!-- Categorical Axis -->
                         <template v-else>
                             <!-- Distribution Bars -->
                             <g v-if="axis.distribution">
                                 <rect 
                                   v-for="level in axis.levels" 
                                   :key="'dist-'+level.label"
                                   :x="scaleX(level.points) - 10"
                                   :y="-getDistHeight(axis, level.label)"
                                   width="20"
                                   :height="getDistHeight(axis, level.label)"
                                   fill="#3B71CA"
                                   opacity="0.15"
                                 />
                             </g>

                             <g v-for="level in axis.levels" :key="level.label">
                                 <circle :cx="scaleX(level.points)" cy="0" r="3" fill="#333" />
                                 <line :x1="scaleX(level.points)" y1="0" :x2="scaleX(level.points)" y2="-5" stroke="#333" />
                                 <text :x="scaleX(level.points)" y="-10" text-anchor="middle" font-size="10" fill="#606266">{{ level.label }}</text>
                                 
                                  <!-- User Select Marker -->
                                  <circle v-if="userInputs[axis.name] === level.label" :cx="scaleX(level.points)" cy="0" r="6" fill="none" stroke="#D32F2F" stroke-width="2" />
                             </g>
                         </template>
                     </g>
                     
                     <!-- 3. Total Points -->
                     <g :transform="`translate(0, ${100 + spec.axes.length * 60 + 40})`">
                         <text x="10" y="0" font-weight="bold" font-size="13" fill="#303133">总分 (Total Points)</text>
                         <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="#303133" stroke-width="2" />
                          <!-- Ticks for Total Points -->
                         <g v-for="t in totalPointsTicks" :key="t">
                             <line :x1="scaleTotal(t)" y1="0" :x2="scaleTotal(t)" y2="-6" stroke="#303133" />
                             <text :x="scaleTotal(t)" y="-12" text-anchor="middle" font-size="11" fill="#606266">{{ t }}</text>
                         </g>
                         
                         <!-- User Total Marker -->
                          <path :d="`M ${scaleTotal(currentUserTotal)} -5 L ${scaleTotal(currentUserTotal)} 5`" stroke="#D32F2F" stroke-width="3" />
                          <circle :cx="scaleTotal(currentUserTotal)" cy="-10" r="4" fill="#D32F2F" />
                          
                          <!-- Vertical Drop Line to bottom scale -->
                          <line 
                               :x1="scaleTotal(currentUserTotal)" 
                               y1="5" 
                               :x2="scaleTotal(currentUserTotal)" 
                               :y2="height - 50" 
                               stroke="#D32F2F" 
                               stroke-dasharray="4,4" 
                               opacity="0.3" 
                          />
                     </g>
                                          <!-- 4. Outcome Scales (Survival or Binary) -->
                      
                      <!-- 4. Outcome Scales -->
                      <template v-if="spec.outcome_type === 'survival'">
                        <g v-for="(scale, idx) in spec.survival_scales" :key="scale.time" :transform="`translate(0, ${100 + spec.axes.length * 60 + 100 + idx * 50})`">
                            <text x="10" y="0" font-weight="bold" font-size="12">{{ scale.time }}个月生存率</text>
                            <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="#303133" stroke-width="1.5" />
                            
                            <g v-for="(tick, i) in scale.ticks" :key="i">
                                <template v-if="shouldShowTick(tick.survival, i)">
                                   <line :x1="scaleTotal(tick.points)" y1="0" :x2="scaleTotal(tick.points)" y2="6" stroke="#303133" />
                                   <text :x="scaleTotal(tick.points)" y="18" text-anchor="middle" font-size="10" fill="#606266">{{ tick.survival.toFixed(2) }}</text>
                                </template>
                            </g>
                        </g>
                      </template>
                      
                      <template v-else-if="spec.outcome_type === 'binary' && spec.probability_scale">
                        <g :transform="`translate(0, ${100 + spec.axes.length * 60 + 110})`">
                            <text x="10" y="0" font-weight="bold" font-size="12">{{ spec.probability_scale.label }}</text>
                            <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="#303133" stroke-width="1.5" />
                            
                            <g v-for="(tick, i) in spec.probability_scale.ticks" :key="i">
                                <template v-if="shouldShowTick(tick.probability, i)">
                                   <line :x1="scaleTotal(tick.points)" y1="0" :x2="scaleTotal(tick.points)" y2="6" stroke="#303133" />
                                   <text :x="scaleTotal(tick.points)" y="18" text-anchor="middle" font-size="10" fill="#606266">{{ tick.probability.toFixed(2) }}</text>
                                </template>
                            </g>
                        </g>
                      </template>
                      
                      <!-- Interactive Red Lines (Vertical from Vars to Top Points) -->
                       <g v-for="(pt, name) in userPoints" :key="name">
                           <template v-if="spec.axes.find(a=>a.name===name)">
                              <line 
                                 :x1="scaleX(pt)" 
                                 :y1="getVarY(name)" 
                                 :x2="scaleX(pt)" 
                                 :y2="40" 
                                 stroke="#D32F2F" 
                                 stroke-dasharray="2,2" 
                                 opacity="0.3"
                              />
                           </template>
                       </g>
                     
                 </svg>
             </div>
         </el-col>
                  <!-- Forms Area -->
          <el-col :span="8">
              <el-card shadow="hover">
                  <template #header>
                      <div style="display: flex; align-items: center; justify-content: space-between;">
                          <span style="font-weight: bold;">预测计算器 (Calculator)</span>
                          <el-tooltip content="在下方调整变量值，左侧图中红色标记将同步移动，实时显示预测风险。" placement="top">
                              <el-icon><QuestionFilled /></el-icon>
                          </el-tooltip>
                      </div>
                  </template>
                  
                  <el-form label-position="top" size="small">
                      <div v-for="axis in spec.axes" :key="axis.name" style="margin-bottom: 5px;">
                          <el-form-item :label="axis.name">
                              <template v-if="axis.type === 'continuous'">
                                  <el-slider v-model="userInputs[axis.name]" :min="axis.min" :max="axis.max" :step="(axis.max-axis.min)/200 || 0.1" show-input />
                              </template>
                              <template v-else>
                                  <el-select v-model="userInputs[axis.name]" style="width: 100%">
                                      <el-option v-for="l in axis.levels" :key="l.label" :label="l.label" :value="l.label" />
                                  </el-select>
                              </template>
                          </el-form-item>
                      </div>
                  </el-form>
                  
                  <div class="calc-results" style="margin-top: 20px; background: #f0f9eb; padding: 15px; border-radius: 8px; border-left: 5px solid #67C23A;">
                      <div style="font-size: 15px; font-weight: bold; margin-bottom: 12px; color: #303133;">实时预测结果:</div>
                      <div style="margin-bottom: 8px; font-size: 14px;">总分 (Total Points): <b style="color: #409EFF; font-size: 18px;">{{ currentUserTotal.toFixed(1) }}</b></div>
                      <el-divider style="margin: 12px 0" />
                      
                      <!-- Case A: Survival -->
                      <template v-if="spec.outcome_type === 'survival'">
                          <div v-for="(prob, t) in currentPredictions" :key="t" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                              <span style="font-size: 13px; color: #606266;">{{ t }}个月生存率:</span>
                              <span style="color: #67C23A; font-weight: bold; font-size: 16px;">{{ (prob * 100).toFixed(1) }}%</span>
                          </div>
                      </template>
                      
                      <!-- Case B: Binary -->
                      <template v-if="spec.outcome_type === 'binary'">
                           <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                              <span style="font-size: 13px; color: #606266;">发生风险概率:</span>
                              <span style="color: #F56C6C; font-weight: bold; font-size: 20px;">{{ (currentPredictions.probability * 100).toFixed(1) }}%</span>
                          </div>
                      </template>
                  </div>
                  
                  <div style="margin-top: 15px; font-size: 12px; color: #909399; line-height: 1.4;">
                      * 注：基于回归模型计算。该结果仅供研究参考，不作为唯一临床诊断依据。
                  </div>
              </el-card>
          </el-col>
     </el-row>
  </div>
</template>

<script setup>
/**
 * NomogramVisualizer.vue
 * 列线图可视化核心组件（SVG 渲染版）。
 * 
 * 职责：
 * 1. 接收后端生成的列线图规格 (Spec)，采用 SVG 渲染学术标准的列线图。
 * 2. 支持交互式预测：用户拖动或输入变量值，图中红色指示线同步更新，实时反馈预测概率。
 * * 实现了 Cox 与 Logistic 回归公式在前端的重构，确保图形映射与数学计算的一致性。
 */
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'

const props = defineProps({
    spec: {
        type: Object,
        required: true
    }
})

// 坐标映射比例与边距配置
const width = 800
const leftMargin = 150
const rightMargin = 750
const usefulWidth = rightMargin - leftMargin

const height = computed(() => {
    if (!props.spec || !props.spec.axes) return 600
    const axesH = props.spec.axes.length * 60
    const survH = (props.spec.survival_scales || []).length * 50
    const binaryH = props.spec.probability_scale ? 100 : 0
    return 100 + axesH + 100 + survH + binaryH + 100
})

// 定义坐标变换工具函数
const scaleX = (points) => {
    // 将 0-100 的分值映射到 SVG 的 X 坐标轴 (leftMargin -> rightMargin)
    return leftMargin + (points / 100) * usefulWidth
}

const scaleTotal = (totalPoints) => {
    // 将 0 -> maxTotal 的总分映射到 SVG 坐标轴
    const max = props.spec.total_points.max
    const ratio = totalPoints / max
    return leftMargin + ratio * usefulWidth
}

const pointsTicks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
const totalPointsTicks = computed(() => {
    const max = props.spec.total_points.max
    const ticks = []
    for(let i=0; i<=max; i+=20) ticks.push(i)
    return ticks
})

const getVarY = (name) => {
    const idx = props.spec.axes.findIndex(a => a.name === name)
    return 100 + idx * 60
}

/**
 * 绘图增强：生成连续变量密度路径 (Density Path)
 */
const generateDensityPath = (axis) => {
    if (!axis.distribution || axis.distribution.length < 2) return ""
    
    // distribution contains 11 deciles: [min, d1, d2, ..., max]
    const deciles = axis.distribution
    const points_at_deciles = deciles.map(val => {
        // Find points for this value
        const pMin = axis.points[String(axis.min)] ?? 0
        const pMax = axis.points[String(axis.max)] ?? 0
        const range = axis.max - axis.min
        const pts = range === 0 ? pMin : pMin + ((val - axis.min) / range) * (pMax - pMin)
        return scaleX(pts)
    })
    
    // We create a "mountain" shape. 
    // Since deciles represent equal sample counts, the "height" is constant in density terms, 
    // but we can vary it to show decile spacing (narrower spacing = higher density).
    // Simple heuristic: height = 1 / (spacing)
    const heights = [0]
    for (let i = 1; i < points_at_deciles.length - 1; i++) {
        const spacing = points_at_deciles[i+1] - points_at_deciles[i-1]
        const h = Math.min(20, 200 / (spacing + 1))
        heights.push(h)
    }
    heights.push(0)
    
    // Build SVG path (simplified curve)
    let d = `M ${points_at_deciles[0]} 0`
    for (let i = 1; i < points_at_deciles.length; i++) {
        d += ` L ${points_at_deciles[i]} ${-heights[i]}`
    }
    d += ` L ${points_at_deciles[points_at_deciles.length - 1]} 0 Z`
    return d
}

const getDistHeight = (axis, label) => {
    if (!axis.distribution || !axis.distribution[label]) return 0
    const counts = Object.values(axis.distribution)
    const max = Math.max(...counts)
    return (axis.distribution[label] / max) * 20
}

const calculateVariablePoints = (axis) => {
    const val = userInputs[axis.name]
    if (val === undefined) return 0
    const pMin = axis.points[String(axis.min)] ?? 0
    const pMax = axis.points[String(axis.max)] ?? 0
    const range = axis.max - axis.min
    return range === 0 ? pMin : pMin + ((val - axis.min) / range) * (pMax - pMin)
}

const shouldShowTick = (val, idx) => {
    // 启发式：对于 0.1 到 0.9 之间的值，每逢 0.1 显示
    // 对于 > 0.9 的值，显示 0.95, 0.99 等
    if (val > 0.05 && val < 0.95) return idx % 2 === 0
    return true
}

// 响应式状态：用户选择的变量输入值
const userInputs = reactive({})

// Initialize inputs
onMounted(() => {
    initInputs()
})
watch(() => props.spec, initInputs)

function initInputs() {
    props.spec.axes.forEach(axis => {
        if (axis.type === 'continuous') {
            userInputs[axis.name] = (axis.min + axis.max) / 2
        } else {
            userInputs[axis.name] = axis.levels[0].label
        }
    })
}

// 核心预测计算逻辑
/**
 * 计算当前选中的输入值对应的各变量得分
 */
const userPoints = computed(() => {
    const pts = {}
    if (!props.spec || !props.spec.axes) return pts
    
    props.spec.axes.forEach(axis => {
        const val = userInputs[axis.name]
        if (val === undefined) return
        
        if (axis.type === 'continuous') {
            // 连续变量：基于线性内插计算得分
            // Robust access to points dict (handle string/number key mismatch)
            const pMin = axis.points[String(axis.min)] ?? axis.points[axis.min] ?? 0
            const pMax = axis.points[String(axis.max)] ?? axis.points[axis.max] ?? 0
            
            const range = axis.max - axis.min
            if (range === 0) {
                pts[axis.name] = pMin
            } else {
                const ratio = (val - axis.min) / range
                pts[axis.name] = pMin + ratio * (pMax - pMin)
            }
            
        } else {
            // 分类变量：直接查表获取对应得分
            const level = axis.levels.find(l => l.label === val)
            if (level) pts[axis.name] = level.points
            else pts[axis.name] = 0
        }
    })
    return pts
})

/**
 * 计算所有变量得分之和 (Total Points)
 */
const currentUserTotal = computed(() => {
    return Object.values(userPoints.value).reduce((a, b) => a + b, 0)
})

/**
 * 基于 Cox 模型公式反推生存概率预测值
 */
const currentPredictions = computed(() => {
    const total = currentUserTotal.value
    const ppu = props.spec.formula_params.points_per_unit
    const offset = props.spec.formula_params.constant_offset
    
    // LP = (Total / Scale) + Offset
    const lp = (total / ppu) + offset
    
    if (props.spec.outcome_type === 'binary') {
        const prob = 1 / (1 + Math.exp(-lp))
        return { probability: prob }
    }
    
    const preds = {}
    if (props.spec.base_survivals) {
        for (const [t, s0] of Object.entries(props.spec.base_survivals)) {
            const prob = Math.pow(s0, Math.exp(lp))
            preds[t] = prob
        }
    }
    return preds
})

const exportImage = () => {
    if (!svgRef.value) return
    
    // 1. 获取 SVG 字符串并处理样式
    const svgData = new XMLSerializer().serializeToString(svgRef.value)
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)
    
    // 2. 创建 Canvas 并绘制 (设置高 DPI)
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    const img = new Image()
    
    // 逻辑：为了高质量导出，我们将 canvas 放大 2 倍
    const scale = 2
    canvas.width = width * scale
    canvas.height = height.value * scale
    
    img.onload = () => {
        // 背景填白 (SVG 默认背景透明)
        ctx.fillStyle = 'white'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        
        ctx.scale(scale, scale)
        ctx.drawImage(img, 0, 0)
        
        // 3. 触发下载
        const pngUrl = canvas.toDataURL('image/png')
        const downloadLink = document.createElement('a')
        downloadLink.href = pngUrl
        downloadLink.download = `nomogram_${new Date().getTime()}.png`
        document.body.appendChild(downloadLink)
        downloadLink.click()
        document.body.removeChild(downloadLink)
        
        URL.revokeObjectURL(url)
        ElMessage.success('列线图导出成功 (高清)')
    }
    img.src = url
}

</script>

<style scoped>
.nomogram-svg {
    font-family: Arial, sans-serif;
    user-select: none;
}
.canvas-wrapper {
    overflow-x: auto;
    border: 1px solid #eee;
    padding: 10px;
    background: white;
}
.canvas-toolbar {
    display: flex; 
    justify-content: space-between; 
    margin-bottom: 10px;
}
</style>
