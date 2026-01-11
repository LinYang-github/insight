<template>
  <div class="nomogram-container">
     <el-row :gutter="20">
         
         <!-- Canvas Area -->
         <el-col :span="16">
             <div class="canvas-wrapper" ref="canvasWrapper">
                 <div class="canvas-toolbar">
                     <span>交互式列线图 (Interactive Nomogram)</span>
                     <el-button size="small" type="primary" link @click="exportImage">下载图片</el-button>
                 </div>
                 
                 <svg ref="svgRef" :width="width" :height="height" class="nomogram-svg">
                     <defs>
                         <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                             <path d="M 0 0 L 10 5 L 0 10 z" fill="#333" />
                         </marker>
                     </defs>
                     
                     <!-- 1. Header: Points Scale -->
                     <g transform="translate(0, 40)">
                         <text x="10" y="0" font-weight="bold" font-size="12">Points</text>
                         <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="black" stroke-width="1.5" />
                         <!-- Ticks 0-100 -->
                         <g v-for="t in pointsTicks" :key="t">
                             <line :x1="scaleX(t)" y1="0" :x2="scaleX(t)" y2="-5" stroke="black" />
                             <text :x="scaleX(t)" y="-10" text-anchor="middle" font-size="10">{{ t }}</text>
                         </g>
                     </g>
                     
                     <!-- 2. Variables -->
                     <g v-for="(axis, idx) in spec.axes" :key="axis.name" :transform="`translate(0, ${80 + idx * 50})`">
                         <text x="10" y="0" font-weight="bold" font-size="12">{{ axis.name }}</text>
                         <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="#ccc" stroke-dasharray="2,2" />
                         
                         <!-- Continuous Axis -->
                         <template v-if="axis.type === 'continuous'">
                             <!-- Main Line representing range -->
                             <line :x1="scaleX(axis.points[axis.min])" y1="0" :x2="scaleX(axis.points[axis.max])" y2="0" stroke="black" stroke-width="1.5" />
                             
                             <!-- Ticks (Min/Max) -->
                             <g v-for="(pt, val) in axis.points" :key="val">
                                 <line :x1="scaleX(pt)" y1="0" :x2="scaleX(pt)" y2="-5" stroke="black" />
                                 <text :x="scaleX(pt)" y="-10" text-anchor="middle" font-size="10">{{ parseFloat(val).toFixed(1) }}</text>
                             </g>
                             
                             <!-- User Value Marker (Red) -->
                             <circle v-if="userPoints[axis.name] !== undefined" :cx="scaleX(userPoints[axis.name])" cy="0" r="4" fill="red" />
                         </template>
                         
                         <!-- Categorical Axis -->
                         <template v-else>
                             <g v-for="level in axis.levels" :key="level.label">
                                 <circle :cx="scaleX(level.points)" cy="0" r="3" fill="black" />
                                 <line :x1="scaleX(level.points)" y1="0" :x2="scaleX(level.points)" y2="-5" stroke="black" />
                                 <text :x="scaleX(level.points)" y="-10" text-anchor="middle" font-size="10">{{ level.label }}</text>
                                 
                                  <!-- User Select Marker -->
                                  <circle v-if="userInputs[axis.name] === level.label" :cx="scaleX(level.points)" cy="0" r="5" fill="red" fill-opacity="0.5" stroke="red" />
                             </g>
                         </template>
                     </g>
                     
                     <!-- 3. Total Points -->
                     <g :transform="`translate(0, ${80 + spec.axes.length * 50 + 40})`">
                         <text x="10" y="0" font-weight="bold" font-size="12">Total Points</text>
                         <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="black" stroke-width="1.5" />
                          <!-- Ticks for Total Points -->
                         <g v-for="t in totalPointsTicks" :key="t">
                             <line :x1="scaleTotal(t)" y1="0" :x2="scaleTotal(t)" y2="-5" stroke="black" />
                             <text :x="scaleTotal(t)" y="-10" text-anchor="middle" font-size="10">{{ t }}</text>
                         </g>
                         
                         <!-- User Total Marker -->
                          <circle :cx="scaleTotal(currentUserTotal)" cy="0" r="5" fill="red" />
                          <!-- Drop Line -->
                          <line :x1="scaleTotal(currentUserTotal)" y1="0" :x2="scaleTotal(currentUserTotal)" :y2="150" stroke="red" stroke-dasharray="4,4" />
                     </g>
                     
                     <!-- 4. Survival Probabilities -->
                     <g v-for="(scale, idx) in spec.survival_scales" :key="scale.time" :transform="`translate(0, ${80 + spec.axes.length * 50 + 80 + idx * 40})`">
                         <text x="10" y="0" font-weight="bold" font-size="12">{{ scale.time }}-Month Surv. Prob.</text>
                         <line :x1="leftMargin" y1="0" :x2="rightMargin" y2="0" stroke="black" stroke-width="1.5" />
                         
                         <g v-for="(tick, i) in scale.ticks" :key="i">
                             <template v-if="i % 2 === 0"> <!-- Reduce density -->
                                <line :x1="scaleTotal(tick.points)" y1="0" :x2="scaleTotal(tick.points)" y2="5" stroke="black" />
                                <text :x="scaleTotal(tick.points)" y="15" text-anchor="middle" font-size="9">{{ tick.survival.toFixed(2) }}</text>
                             </template>
                         </g>
                     </g>
                     
                     <!-- Interactive Red Lines (Vertical from Vars to Top Points) -->
                      <g v-for="(pt, name) in userPoints" :key="name">
                          <!-- Only draw if visible -->
                          <template v-if="spec.axes.find(a=>a.name===name)">
                             <line 
                                :x1="scaleX(pt)" 
                                :y1="getVarY(name)" 
                                :x2="scaleX(pt)" 
                                :y2="40" 
                                stroke="red" 
                                stroke-dasharray="2,2" 
                                opacity="0.4"
                             />
                          </template>
                      </g>
                     
                 </svg>
             </div>
         </el-col>
         
         <!-- Forms Area -->
         <el-col :span="8">
             <el-card shadow="hover" header="预测计算器 (Calculator)">
                 <el-form label-position="top" size="small">
                     <div v-for="axis in spec.axes" :key="axis.name" style="margin-bottom: 5px;">
                         <el-form-item :label="axis.name">
                             <template v-if="axis.type === 'continuous'">
                                 <el-slider v-model="userInputs[axis.name]" :min="axis.min" :max="axis.max" :step="(axis.max-axis.min)/100 || 1" show-input />
                             </template>
                             <template v-else>
                                 <el-select v-model="userInputs[axis.name]" style="width: 100%">
                                     <el-option v-for="l in axis.levels" :key="l.label" :label="l.label" :value="l.label" />
                                 </el-select>
                             </template>
                         </el-form-item>
                     </div>
                 </el-form>
                 
                 <div class="calc-results" style="margin-top: 20px; background: #f0f9eb; padding: 15px; border-radius: 4px;">
                     <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">预测结果:</div>
                     <div style="margin-bottom: 5px;">总分 (Total Points): <b>{{ currentUserTotal.toFixed(1) }}</b></div>
                     <el-divider style="margin: 10px 0" />
                     <div v-for="(prob, t) in currentPredictions" :key="t" style="margin-bottom: 5px; display: flex; justify-content: space-between;">
                         <span>{{ t }}个月生存率:</span>
                         <span style="color: #67C23A; font-weight: bold;">{{ (prob * 100).toFixed(1) }}%</span>
                     </div>
                 </div>
             </el-card>
         </el-col>
     </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue'

const props = defineProps({
    spec: {
        type: Object,
        required: true
    }
})

// Dimensions
const width = 800
const leftMargin = 150
const rightMargin = 750
const usefulWidth = rightMargin - leftMargin

const height = computed(() => {
    // Dynamic height based on number of axes
    return 80 + (props.spec.axes.length * 50) + 250 // Extra space for survival scales
})

// Scaling Utils
const scaleX = (points) => {
    // Map 0-100 Points to [leftMargin, rightMargin]
    return leftMargin + (points / 100) * usefulWidth
}

const scaleTotal = (totalPoints) => {
    // Map 0-maxTotal to [leftMargin, rightMargin]
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
    return 80 + idx * 50
}

// User Inputs
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

// Calculations
const userPoints = computed(() => {
    const pts = {}
    props.spec.axes.forEach(axis => {
        const val = userInputs[axis.name]
        if (val === undefined) return
        
        if (axis.type === 'continuous') {
            // Points = (PointsRange) * (Val - Min)/(Max - Min) ???
            // No, we need to map based on generated points
            // Backend gave us points mapped for min and max.
            // But assume linearity for continuous.
            // If coef > 0: Min=LowPts, Max=HighPts
            // If coef < 0: Min=HighPts, Max=LowPts
            
            // Re-derive linear params from backend points dict
            // values: { 'min': p1, 'max': p2 }
            const pMin = axis.points[String(axis.min)]
            const pMax = axis.points[String(axis.max)]
            
            const ratio = (val - axis.min) / (axis.max - axis.min)
            pts[axis.name] = pMin + ratio * (pMax - pMin)
            
        } else {
            // Categorical
            const level = axis.levels.find(l => l.label === val)
            if (level) pts[axis.name] = level.points
            else pts[axis.name] = 0
        }
    })
    return pts
})

const currentUserTotal = computed(() => {
    return Object.values(userPoints.value).reduce((a, b) => a + b, 0)
})

const currentPredictions = computed(() => {
    const total = currentUserTotal.value
    const ppu = props.spec.formula_params.points_per_unit
    const offset = props.spec.formula_params.constant_offset
    
    // LP = (Total / Scale) + Offset
    const lp = (total / ppu) + offset
    
    const preds = {}
    // S(t) = S0(t) ^ exp(LP)
    if (props.spec.base_survivals) {
        for (const [t, s0] of Object.entries(props.spec.base_survivals)) {
            const prob = Math.pow(s0, Math.exp(lp))
            preds[t] = prob
        }
    }
    return preds
})

const exportImage = () => {
    // Simple SVG export logic (future work: canvas conversion)
    // For now, prompt user to screenshot? Or use canvas serialization.
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
