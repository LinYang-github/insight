<template>
  <span :class="['stat-value', type, { 'is-significant': isSignificant, 'is-insignificant': isInsignificant }]">
    <template v-if="type === 'p-value'">
      {{ formattedP }}
    </template>
    <template v-else-if="type === 'range'">
      <span class="range-val">{{ formattedVal }}</span> 
      <psan class="range-bracket">({{ formattedLower }}-{{ formattedUpper }})</psan>
    </template>
    <template v-else>
      {{ formattedVal }}
    </template>
  </span>
</template>

<script setup>
import { computed } from 'vue'

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

const formattedP = computed(() => {
  const val = parseFloat(props.value)
  if (isNaN(val)) return props.value
  if (val < 0.001) return '<0.001'
  return val.toFixed(3)
})

const formattedVal = computed(() => {
    const val = parseFloat(props.value)
    if (isNaN(val)) return props.value
    return val.toFixed(props.digits)
})

const formattedLower = computed(() => {
    const val = parseFloat(props.lower)
    if (isNaN(val)) return props.lower
    return val.toFixed(props.digits)
})

const formattedUpper = computed(() => {
    const val = parseFloat(props.upper)
    if (isNaN(val)) return props.upper
    return val.toFixed(props.digits)
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
