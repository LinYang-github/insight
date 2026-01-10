<template>
  <div class="interpretation-panel" v-if="interpretation" :class="interpretation.level">
    <div class="panel-header">
      <el-icon class="icon"><MagicStick /></el-icon>
      <span class="title">智能分析结论 (Smart Insight)</span>
    </div>
    <div class="panel-content">
      <!-- Main Conclusion rendered from template -->
      <p class="summary-text" v-html="renderedText"></p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  interpretation: {
    type: Object,
    default: null 
    // Structure: { text_template: "Var {var}...", params: {var: "Age"}, level: "danger" }
  }
})

const renderedText = computed(() => {
    if (!props.interpretation) return ''
    const tmpl = props.interpretation.text_template
    const params = props.interpretation.params || {}
    
    // Simple interpolation
    return tmpl.replace(/{(\w+)}/g, (match, key) => {
        const val = params[key]
        if (val === undefined) return match
        
        // Apply specific styling based on keys?
        // e.g. HR/OR/P -> Bold or Color
        // Or simpler: Backend can provide markdown or HTML? 
        // User requirement said "Frontend only renders".
        // Let's wrap value in span for potential styling.
        // But 'direction' changes color based on logic? 
        // The logic was moved to backend (level: danger/success), 
        // so we can style the whole block or specific keywords.
        // Let's keep it simple: Bold the parameters.
        return `<strong>${val}</strong>`
    })
})
</script>

<style scoped>
.interpretation-panel {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 15px;
  margin-top: 20px;
  background-color: #f4f4f5;
}

.interpretation-panel.danger {
    background-color: #fef0f0;
    border-color: #fde2e2;
}
.interpretation-panel.success {
    background-color: #f0f9eb;
    border-color: #e1f3d8;
}
.interpretation-panel.info {
    background-color: #f4f4f5;
    border-color: #e9e9eb;
}

.panel-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  font-weight: bold;
}

.interpretation-panel.danger .panel-header { color: #f56c6c; }
.interpretation-panel.success .panel-header { color: #67c23a; }
.interpretation-panel.info .panel-header { color: #909399; }

.icon {
  font-size: 18px;
  margin-right: 8px;
}

.title {
  font-size: 14px;
}

.summary-text {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  margin: 0;
}
</style>
