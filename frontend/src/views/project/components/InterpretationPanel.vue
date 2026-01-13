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
/**
 * InterpretationPanel.vue
 * 智能解读面板组件。
 * 
 * 职责：
 * 1. 接收后端生成的分析结论模板 (text_template) 与动态参数 (params)。
 * 2. 在前端执行插值逻辑，生成可读性强的自然语言结论。
 * 3. 根据结论的严重程度（level: danger/success/info）展示不同的视觉样式。
 */
import { computed } from 'vue'

const props = defineProps({
  interpretation: {
    type: Object,
    default: null 
    // Structure: { text_template: "Var {var}...", params: {var: "Age"}, level: "danger" }
  }
})

/**
 * 计算插值后的解读文本。
 */
const renderedText = computed(() => {
    if (!props.interpretation) return ''
    const tmpl = props.interpretation.text_template
    const params = props.interpretation.params || {}
    
    // 简单插值逻辑：将模板中的 {key} 替换为对应的参数值
    return tmpl.replace(/{(\w+)}/g, (match, key) => {
        const val = params[key]
        if (val === undefined) return match
        
        // 此处可以将所有动态参数加粗显示
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
