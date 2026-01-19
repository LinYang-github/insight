<template>
  <span :class="['stat-value', type, { 'is-significant': isSignificant, 'is-insignificant': isInsignificant }]">
    <template v-if="type === 'p-value'">
      {{ formatPValue(value) }}
    </template>
    <template v-else-if="type === 'range'">
      <span class="range-val">{{ formatNumber(value, digits) }}</span> 
      <span class="range-bracket">({{ formatNumber(lower, digits) }} - {{ formatNumber(upper, digits) }})</span>
    </template>
    <template v-else>
      {{ formatNumber(value, digits) }}
    </template>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { formatPValue, formatNumber } from '../utils/formatters'

const props = defineProps({
  value: { type: [Number, String], required: true },
  lower: { type: [Number, String], default: null },
  upper: { type: [Number, String], default: null },
  type: { type: String, default: 'number' }, // 'p-value', 'range' (CI), 'number'
  digits: { type: Number, default: 2 } // For normal numbers
})

const isSignificant = computed(() => {
  if (props.type === 'p-value') {
    const val = parseFloat(props.value)
    return !isNaN(val) && val < 0.05
  }
  return false
})

const isInsignificant = computed(() => {
    // For Confidence Intervals: if it crosses 1 (e.g., 0.8-1.2), it's insignificant
    if (props.type === 'range' && props.lower != null && props.upper != null) {
        const l = parseFloat(props.lower)
        const u = parseFloat(props.upper)
        if (!isNaN(l) && !isNaN(u)) {
            return (l <= 1 && u >= 1)
        }
    }
    return false
})
</script>

<style scoped>
.stat-value {
  font-family: var(--font-mono);
}

.stat-value.p-value.is-significant {
    color: var(--color-significance);
    font-weight: bold;
}

.stat-value.range.is-insignificant {
    color: #909399; /* Gray out insignificant CIs */
}

.range-bracket {
    margin-left: 4px;
    font-size: 0.9em;
    color: var(--color-text-secondary);
}

.stat-value.range.is-insignificant .range-bracket {
    color: inherit;
}
</style>
