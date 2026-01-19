import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * UI Store
 * 管理全局 UI 状态，如学术模式开关
 */
export const useUiStore = defineStore('ui', () => {
  // 学术发表模式 (学术三线表、Plotly 学术样式开关)
  const isAcademicMode = ref(false)

  function toggleAcademicMode() {
    isAcademicMode.value = !isAcademicMode.value
  }

  function setAcademicMode(value) {
    isAcademicMode.value = !!value
  }

  return {
    isAcademicMode,
    toggleAcademicMode,
    setAcademicMode
  }
})
