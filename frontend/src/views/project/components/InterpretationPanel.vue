<template>
  <div class="interpretation-panel" v-if="interpretation" :class="interpretation.level || 'info'">
    <div class="panel-header">
      <el-icon class="icon"><MagicStick /></el-icon>
      <span class="title">{{ interpretation.is_ai ? 'AI 深度医学解读 (AI Insights)' : '智能分析结论 (Smart Insight)' }}</span>
    </div>
    <div class="panel-content">
      <!-- 1. AI Generated Markdown Content -->
      <div v-if="interpretation.is_ai" class="ai-rich-content" v-html="renderedMarkdown"></div>
      
      <!-- 2. Legacy Template Content -->
      <p v-else class="summary-text" v-html="renderedText"></p>
    </div>
  </div>
</template>

<script setup>
/**
 * InterpretationPanel.vue
 * 智能解读面板组件 - 支持模板引擎与 AI Markdown 渲染。
 */
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  interpretation: {
    type: Object,
    default: null 
    // Structure 1: { text_template: "Var {var}...", params: {var: "Age"}, level: "danger" }
    // Structure 2: { text: "Markdown Content...", is_ai: true, level: "info" }
  }
})

/**
 * 渲染 Markdown 内容 (用于 AI 解读)
 */
const renderedMarkdown = computed(() => {
    if (!props.interpretation || !props.interpretation.text) return ''
    return marked.parse(props.interpretation.text)
})

/**
 * 计算插值后的解读文本 (用于模板解读)
 */
const renderedText = computed(() => {
    if (!props.interpretation || !props.interpretation.text_template) return ''
    const tmpl = props.interpretation.text_template
    const params = props.interpretation.params || {}
    
    return tmpl.replace(/{(\w+)}/g, (match, key) => {
        const val = params[key]
        if (val === undefined) return match
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

/* AI Markdown Styles */
.ai-rich-content {
    font-size: 14px;
    line-height: 1.7;
    color: #1e293b;
}
.ai-rich-content :deep(p) {
    margin: 8px 0;
}
.ai-rich-content :deep(ul), .ai-rich-content :deep(ol) {
    padding-left: 20px;
    margin: 10px 0;
}
.ai-rich-content :deep(li) {
    margin-bottom: 5px;
}
.ai-rich-content :deep(strong) {
    color: #0f172a;
    font-weight: 600;
}
.ai-rich-content :deep(h1), .ai-rich-content :deep(h2), .ai-rich-content :deep(h3) {
    font-size: 15px;
    margin: 16px 0 8px 0;
    color: #334155;
}
</style>
