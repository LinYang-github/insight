<template>
  <div class="step-wizard">
    <!-- Steps Indicator -->
    <div class="steps-header">
      <el-steps :active="activeStep" finish-status="success" align-center>
        <el-step v-for="(step, index) in steps" :key="index" :title="step.title" :description="step.description" />
      </el-steps>
    </div>

    <!-- Step Content -->
    <div class="step-content">
      <slot :name="currentSlotName"></slot>
    </div>

    <!-- Actions -->
    <div class="step-actions">
      <el-button v-if="activeStep > 0" @click="prev">上一步 (Back)</el-button>
      
      <el-button 
        v-if="activeStep < steps.length - 1" 
        type="primary" 
        @click="next" 
        :disabled="disableNext"
        :loading="loading"
      >
        下一步 (Next)
      </el-button>
      
      <el-button 
        v-else 
        type="success" 
        @click="finish" 
        :loading="loading"
      >
        完成 (Finish)
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  steps: {
    type: Array,
    required: true,
  },
  loading: Boolean,
  disableNext: Boolean,
  modelValue: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue', 'finish'])

const activeStep = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const maxStep = computed(() => props.steps.length - 1)
const currentSlotName = computed(() => props.steps[activeStep.value]?.slot)

const next = () => {
  if (activeStep.value < maxStep.value) {
    activeStep.value++
  }
}

const prev = () => {
  if (activeStep.value > 0) {
    activeStep.value--
  }
}

const finish = () => {
  emit('finish')
}
</script>

<style scoped>
.step-wizard {
    padding: 20px;
}
.steps-header {
    margin-bottom: 30px;
}
.step-content {
    min-height: 300px;
    background: #fff;
    padding: 20px;
    border: 1px solid #EBEEF5;
    border-radius: 4px;
    margin-bottom: 20px;
}
.step-actions {
    display: flex;
    justify-content: flex-end;
}
</style>
