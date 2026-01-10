<template>
  <el-table
    v-bind="$attrs"
    :class="['publication-table']"
    :border="false"
    :stripe="false"
    style="width: 100%"
  >
    <slot />
  </el-table>
</template>

<script setup>
// Simply wraps el-table but enforces specific classes and props
</script>

<style>
/* Global styles for Publication Table to override Element Plus */
.publication-table {
    border-top: 2px solid #000 !important;
    border-bottom: 2px solid #000 !important;
    font-family: var(--font-mono); /* Numbers aligned */
    --el-table-header-font-color: #000;
    --el-table-border-color: transparent; /* Hide internal borders */
}

/* Header bottom border */
.publication-table th.el-table__cell {
    border-bottom: 1px solid #000 !important;
    background-color: #fff !important; /* No gray background */
    font-weight: bold;
    color: #000;
}

/* Row bottom border */
.publication-table td.el-table__cell {
    border-bottom: none !important; /* Remove row dividing lines by default for clean look */
    /* Or keep them light? Academic usually has few lines. */
    /* Let's keep specific dividing lines if needed, but standard is minimal. */
    /* For Table 1, usually no horizontal lines except header and footer. */
    padding: 8px 0;
}

/* Hover effect can stay or be subtle */
.publication-table .el-table__body tr:hover > td {
    background-color: #f5f7fa !important;
}

/* Remove vertical lines if any */
.publication-table--enable-row-hover .el-table__body tr > td.el-table__cell {
    border-right: none;
}
</style>
