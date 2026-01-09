
<template>
  <div class="psm-container">
    <el-row :gutter="20">
        <!-- Config Panel -->
        <el-col :span="6">
            <el-card class="box-card">
                <template #header>
                    <div class="card-header">
                        <span>参数配置</span>
                    </div>
                </template>
                <el-form label-position="top">
                    <el-form-item label="处理组变量 (Treatment)">
                        <el-select v-model="config.treatment" placeholder="Binary (0/1)" filterable style="width: 100%">
                             <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-form-item label="协变量 (Covariates)">
                        <el-select v-model="config.covariates" multiple placeholder="Select Confounders" filterable style="width: 100%">
                             <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>
                    
                    <el-form-item>
                        <el-checkbox v-model="config.save">同时保存匹配后数据集</el-checkbox>
                    </el-form-item>

                    <el-button type="primary" style="width: 100%" @click="runPSM" :loading="loading">开始匹配 (Run Matching)</el-button>
                </el-form>
            </el-card>
        </el-col>

        <!-- Result Panel -->
        <el-col :span="18">
            <el-card class="box-card" v-loading="loading">
                 <template #header>
                    <div class="card-header">
                        <span>匹配效果评估 (Balance Diagnostics)</span>
                    </div>
                </template>
                
                <div v-if="results">
                     <el-alert
                        title="匹配成功"
                        type="success"
                        :description="`原始对照组 ${results.stats.n_control} 例，处理组 ${results.stats.n_treated} 例。匹配后共 ${results.stats.n_matched} 例。`"
                        show-icon
                        :closable="false"
                        style="margin-bottom: 20px"
                     />
                     <el-alert v-if="results.new_dataset_id" title="新数据集已保存" type="info" show-icon style="margin-bottom: 20px" />
                     
                     <el-table :data="results.balance" style="width: 100%" border stripe>
                        <el-table-column prop="variable" label="协变量" />
                        <el-table-column prop="smd_pre" label="匹配前 SMD">
                            <template #default="scope">{{ scope.row.smd_pre.toFixed(3) }}</template>    
                        </el-table-column>
                        <el-table-column prop="smd_post" label="匹配后 SMD">
                            <template #default="scope">
                                <span :style="{ fontWeight: 'bold', color: scope.row.smd_post < 0.1 ? 'green' : 'red' }">
                                    {{ scope.row.smd_post.toFixed(3) }}
                                </span>
                            </template>
                        </el-table-column>
                         <el-table-column label="评估">
                            <template #default="scope">
                                <el-tag :type="scope.row.smd_post < 0.1 ? 'success' : 'warning'">
                                    {{ scope.row.smd_post < 0.1 ? 'Balanced' : 'Unbalanced' }}
                                </el-tag>
                            </template>
                        </el-table-column>
                     </el-table>
                </div>
                <el-empty v-else description="请配置参数并运行匹配" />
                
            </el-card>
        </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const emit = defineEmits(['dataset-created'])

const loading = ref(false)
const results = ref(null)

const config = reactive({
    treatment: null,
    covariates: [],
    save: false
})

const variableOptions = computed(() => {
    if (!props.metadata) return []
    if (props.metadata.variables) {
         return props.metadata.variables.map(v => ({ label: v.name, value: v.name }))
    }
    return Object.keys(props.metadata).map(k => ({ label: k, value: k }))
})

const runPSM = async () => {
    if (!config.treatment || config.covariates.length === 0) {
        ElMessage.warning("请选择处理变量和至少一个协变量")
        return
    }

    loading.value = true
    results.value = null
    
    try {
        const { data } = await api.post('/statistics/psm', {
            dataset_id: props.datasetId,
            ...config
        })
        
        results.value = data
        
        if (data.new_dataset_id) {
            emit('dataset-created', data.new_dataset_id)
            ElMessage.success("匹配后数据集已保存")
        }
        
    } catch (error) {
        ElMessage.error(error.response?.data?.message || "匹配失败")
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.psm-container {
    padding: 20px;
}
</style>
