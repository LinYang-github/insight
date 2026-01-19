<template>
  <el-table
    v-bind="$attrs"
    :class="['publication-table', { 'academic-style': uiStore.isAcademicMode }]"
    :border="!uiStore.isAcademicMode"
    :stripe="!uiStore.isAcademicMode"
    style="width: 100%"
  >
    <slot />
  </el-table>
</template>

<script setup>
import { useUiStore } from '../stores/ui'
const uiStore = useUiStore()
</script>

<style>
/* 学术样式：标准三线表 (Three-Line Table) */
.publication-table.academic-style {
    border-top: 2px solid #000 !important;
    border-bottom: 2px solid #000 !important;
    font-family: var(--font-mono);
    --el-table-header-bg-color: #fff;
    --el-table-border-color: transparent;
}

.publication-table.academic-style .el-table__header-wrapper th {
    border-bottom: 1.5px solid #000 !important;
    background-color: #fff !important;
    color: #000;
    font-weight: 700;
}

.publication-table.academic-style .el-table__row td {
    border-bottom: none !important;
    background-color: #fff !important;
}

/* 移除所有垂直线 */
.publication-table.academic-style.el-table--border .el-table__cell,
.publication-table.academic-style .el-table__inner-fixed .el-table__cell {
    border-right: none !important;
}

/* 仅在特定行（如分组行）保留轻微分割线 - 可扩展 */
.publication-table.academic-style .is-group-row td {
    border-bottom: 1px solid #eee !important;
}
</style>
