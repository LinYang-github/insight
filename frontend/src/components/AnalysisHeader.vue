<template>
  <div class="analysis-header">
    <div class="header-left">
      <slot name="title">
        <span class="default-title">{{ title }}</span>
      </slot>
      <slot name="subtitle"></slot>
    </div>
    
    <div class="header-right">
      <!-- Custom Actions (e.g., AI Buttons) -->
      <slot name="actions"></slot>

      <!-- Global Academic Mode Toggle -->
      <div class="academic-toggle">
        <el-divider direction="vertical" v-if="$slots.actions" />
        <el-switch
          v-model="uiStore.isAcademicMode"
          inline-prompt
          active-text="学术模式"
          inactive-text="预览模式"
          style="--el-switch-on-color: #3b71ca; --el-switch-off-color: #909399;"
        />
        <el-tooltip content="开启学术模式：图表切换为 SCI 发表样式，表格切换为标准三线表。" placement="top">
          <el-icon class="help-icon"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>

      <!-- Export Actions -->
      <slot name="export"></slot>
    </div>
  </div>
</template>

<script setup>
import { useUiStore } from '../stores/ui'
import { QuestionFilled } from '@element-plus/icons-vue'

defineProps({
  title: { type: String, default: '' }
})

const uiStore = useUiStore()
</script>

<style scoped>
.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 4px 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.default-title {
  font-weight: bold;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.academic-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
}

.help-icon {
  font-size: 14px;
  color: #909399;
  cursor: help;
}

:deep(.el-switch__inner) {
  font-size: 11px;
}
</style>
