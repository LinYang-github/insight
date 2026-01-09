<template>
  <div class="preprocessing-container">
     <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>
    
    <div v-else-if="!metadata">
         <el-empty description="无法获取数据元信息" />
    </div>

    <div v-else>
        <!-- Imputation Section -->
        <el-card shadow="hover" class="mb-4">
            <template #header>
                <div class="card-header">
                    <span>缺失值处理 (Missing Value Imputation)</span>
                    <el-button type="primary" size="small" @click="handleImpute" :loading="processing">应用并另存为新数据集</el-button>
                </div>
            </template>
            <el-table :data="missingData" style="width: 100%" stripe border size="small">
                 <el-table-column prop="name" label="变量名" />
                 <el-table-column prop="type" label="类型" width="100" />
                 <el-table-column prop="missing" label="缺失数量" width="100">
                      <template #default="scope">
                          <span :class="{ 'red-text': scope.row.missing > 0 }">{{ scope.row.missing }}</span>
                      </template>
                 </el-table-column>
                 <el-table-column label="处理策略" width="200">
                     <template #default="scope">
                         <el-select v-model="imputeStrategies[scope.row.name]" placeholder="选择策略" size="small" :disabled="scope.row.missing === 0">
                             <el-option label="不处理 (Ignore)" value="ignore" />
                             <el-option label="删除行 (Drop Rows)" value="drop" />
                             <el-option v-if="isNumeric(scope.row.type)" label="均值填补 (Mean)" value="mean" />
                             <el-option v-if="isNumeric(scope.row.type)" label="中位数填补 (Median)" value="median" />
                             <el-option label="众数填补 (Mode)" value="mode" />
                         </el-select>
                     </template>
                 </el-table-column>
            </el-table>
        </el-card>

        <!-- Encoding Section -->
        <el-card shadow="hover">
            <template #header>
                 <div class="card-header">
                    <span>变量因子化 (Factorization / Encoding)</span>
                    <el-button type="success" size="small" @click="handleEncode" :loading="processing">应用并另存为新数据集</el-button>
                </div>
            </template>
            
            <el-alert title="将文本/分类变量转换为数值编码 (Label Encoding)，以便模型识别。" type="info" show-icon style="margin-bottom: 10px" />
            
            <el-checkbox-group v-model="selectedEncodeCols">
                <el-row :gutter="20">
                     <el-col :span="6" v-for="col in categoricalCols" :key="col.name">
                         <el-checkbox :label="col.name" border style="width: 100%; margin-bottom: 10px" />
                     </el-col>
                </el-row>
            </el-checkbox-group>
            
            <div v-if="categoricalCols.length === 0" class="empty-text">
                没有检测到分类变量。
            </div>
        </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'

const props = defineProps({
    datasetId: { type: Number, required: true },
    metadata: { type: Object, default: null }
})

const emit = defineEmits(['dataset-created'])

const loading = ref(false)
const processing = ref(false)
const imputeStrategies = ref({})
const selectedEncodeCols = ref([])

const missingData = computed(() => {
    if (!props.metadata) return []
    return props.metadata.variables.filter(v => true) // All variables
})

const categoricalCols = computed(() => {
    if (!props.metadata) return []
    return props.metadata.variables.filter(v => v.type === 'object' || v.type === 'category' || v.type === 'string')
})

const isNumeric = (type) => {
    return ['int64', 'float64', 'int', 'float'].includes(type)
}

// Initialize strategies
watch(() => props.metadata, (meta) => {
    if (meta) {
        const strats = {}
        meta.variables.forEach(v => {
            strats[v.name] = 'ignore'
        })
        imputeStrategies.value = strats
    }
}, { immediate: true })


const handleImpute = async () => {
    // Filter out 'ignore'
    const activeStrategies = {}
    for (const [col, method] of Object.entries(imputeStrategies.value)) {
        if (method !== 'ignore') {
            activeStrategies[col] = method
        }
    }
    
    if (Object.keys(activeStrategies).length === 0) {
        ElMessage.warning('请至少为一个变量选择处理策略')
        return
    }
    
    processing.value = true
    try {
        const { data } = await api.post('/preprocessing/impute', {
            dataset_id: props.datasetId,
            strategies: activeStrategies
        })
        ElMessage.success('缺失值处理成功，已保存为新数据集')
        emit('dataset-created', data.new_dataset_id)
    } catch (error) {
        ElMessage.error(error.response?.data?.message || '处理失败')
    } finally {
        processing.value = false
    }
}

const handleEncode = async () => {
    if (selectedEncodeCols.value.length === 0) {
        ElMessage.warning('请选择至少一个变量进行因子化')
        return
    }
    
    processing.value = true
    try {
         const { data } = await api.post('/preprocessing/encode', {
            dataset_id: props.datasetId,
            columns: selectedEncodeCols.value
        })
        ElMessage.success('因子化成功，已保存为新数据集')
        emit('dataset-created', data.new_dataset_id)
    } catch (error) {
        ElMessage.error(error.response?.data?.message || '处理失败')
    } finally {
        processing.value = false
    }
}

</script>

<style scoped>
.mb-4 {
    margin-bottom: 20px;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.red-text {
    color: red;
    font-weight: bold;
}
.empty-text {
    color: #909399;
    font-size: 14px;
    padding: 20px;
    text-align: center;
}
</style>
