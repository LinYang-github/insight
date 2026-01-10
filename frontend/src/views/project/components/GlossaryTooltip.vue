<template>
  <el-tooltip effect="dark" placement="top">
    <template #content>
      <div class="glossary-content">
        <div class="term-title">{{ term }}</div>
        <div class="term-desc">{{ explanation }}</div>
        <div v-if="clinicalContext" class="clinical-context">
          <strong>临床意义:</strong> {{ clinicalContext }}
        </div>
      </div>
    </template>
    <span class="glossary-trigger">
      <slot>{{ term }}</slot>
      <el-icon class="help-icon"><QuestionFilled /></el-icon>
    </span>
  </el-tooltip>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  term: {
    type: String,
    required: true
  }
})

const dictionary = {
  'p_value': {
    explanation: '假设检验中的概率值。',
    clinical: 'P < 0.05 通常认为组间差异具有统计学意义，即不太可能是由于随机误差导致的。'
  },
  'smd': {
    explanation: 'Standardized Mean Difference (标准差化的均数差)。',
    clinical: '用于衡量两组间的平衡程度。PSM 匹配后，SMD < 0.1 代表两组达到了非常好的平衡。'
  },
  'hr': {
    explanation: 'Hazard Ratio (风险比)。',
    clinical: '在生存分析中，HR > 1 代表该因素增加了终点事件发生的风险；HR < 1 为保护性因素。'
  },
  'or': {
    explanation: 'Odds Ratio (优势比)。',
    clinical: '逻辑回归中，OR > 1 代表该因素增加了结局事件发生的可能性。'
  },
  'caliper': {
    explanation: '卡钳值 (匹配容差)。',
    clinical: 'PSM 时设定的最大允许分差。卡钳越小，匹配越精确，但可能导致匹配成功的人数变少。'
  },
  'vif': {
    explanation: 'Variance Inflation Factor (方差膨胀因子)。',
    clinical: '用于检测多重共线性。VIF > 5 或 10 代表变量间存在严重的信息冗余，可能导致模型不稳定。'
  }
}

const explanation = computed(() => dictionary[props.term.toLowerCase()]?.explanation || '暂无详细解释')
const clinicalContext = computed(() => dictionary[props.term.toLowerCase()]?.clinical || '')
</script>

<style scoped>
.glossary-trigger {
  cursor: help;
  border-bottom: 1px dashed #409eff;
  display: inline-flex;
  align-items: center;
}
.help-icon {
  margin-left: 4px;
  font-size: 0.9em;
  color: #909399;
}
.glossary-content {
  max-width: 250px;
  line-height: 1.4;
}
.term-title {
  font-weight: bold;
  font-size: 1.1em;
  border-bottom: 1px solid #666;
  margin-bottom: 8px;
  padding-bottom: 4px;
}
.clinical-context {
  margin-top: 8px;
  font-size: 0.9em;
  color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  padding: 4px;
  border-radius: 4px;
}
</style>
