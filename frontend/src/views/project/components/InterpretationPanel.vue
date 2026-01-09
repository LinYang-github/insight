<template>
  <div class="interpretation-panel" v-if="isValid">
    <div class="panel-header">
      <el-icon class="icon"><MagicStick /></el-icon>
      <span class="title">智能分析结论 (Smart Insight)</span>
    </div>
    <div class="panel-content">
      <!-- Main Conclusion -->
      <p class="summary-text" v-html="summaryHtml"></p>
      
      <!-- Methodology Explanation -->
      <div v-if="testName" class="methodology-note">
        <span class="label">分析方法:</span>
        <span class="value">{{ testName }}</span>
        <el-tooltip v-if="selectionReason" :content="selectionReason" placement="top">
            <el-icon class="info-icon"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  pValue: {
    type: [Number, String],
    default: null
  },
  testName: {
    type: String,
    default: ''
  },
  selectionReason: {
    type: String,
    default: ''
  },
  // Optional: difference description (e.g. "Mean A > Mean B")
  direction: String
})

const isValid = computed(() => {
  return props.pValue !== null && props.pValue !== 'N/A'
})

const summaryHtml = computed(() => {
  if (!isValid.value) return ''

  let p = props.pValue
  if (typeof p === 'string') {
    if (p.startsWith('<')) p = 0.0001
    else p = parseFloat(p)
  }

  if (isNaN(p)) return ''

  if (p < 0.05) {
    return `<span class="significant">差异显著 (P < 0.05)。</span>` + 
           (props.direction ? ` ${props.direction}` : '') + 
           ` 统计学分析表明，组间存在显著性关联，该结果不太可能是偶然发生的。`
  } else {
    return `<span class="non-significant">无显著差异 (P > 0.05)。</span>` +
           ` 目前的证据尚不足以证明组间存在差异。`
  }
})
</script>

<style scoped>
.interpretation-panel {
  background-color: #F8FDFF; /* Very light blue background */
  border: 1px solid #C3E9FF;
  border-radius: 8px;
  padding: 15px;
  margin-top: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  color: #3B71CA; /* Science Blue */
}

.icon {
  font-size: 18px;
  margin-right: 8px;
}

.title {
  font-weight: 600;
  font-size: 14px;
}

.summary-text {
  font-size: 14px;
  line-height: 1.6;
  color: #212121;
  margin: 0 0 10px 0;
}

.methodology-note {
  font-size: 12px;
  color: #616161;
  display: flex;
  align-items: center;
}

.label {
  font-weight: 500;
  margin-right: 6px;
}

.info-icon {
  margin-left: 4px;
  cursor: help;
  color: #9E9E9E;
}

:deep(.significant) {
  color: #D32F2F; /* Red for significance */
  font-weight: 600;
}

:deep(.non-significant) {
  color: #616161;
}
</style>
