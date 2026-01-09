
<template>
  <div class="tableone-container">
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
                    <el-form-item label="分组变量 (Group By)">
                        <el-select v-model="config.groupBy" placeholder="可选 (Optional)" clearable style="width: 100%">
                            <el-option v-for="opt in categoricalOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-form-item label="统计变量 (Variables)">
                        <el-select v-model="config.variables" multiple placeholder="选择变量" filterable style="width: 100%">
                             <el-option v-for="opt in allOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                        </el-select>
                    </el-form-item>

                    <el-button type="primary" style="width: 100%" @click="generateTable" :loading="loading">生成基线表 (Generate)</el-button>
                </el-form>
            </el-card>
        </el-col>

        <!-- Result Panel -->
        <el-col :span="18">
            <el-card class="box-card" v-loading="loading">
                <template #header>
                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Table 1: Baseline Characteristics</span>
                        <el-button v-if="results.length > 0" type="success" size="small" @click="exportExcel">导出 Excel</el-button>
                    </div>
                </template>

                <el-empty v-if="results.length === 0" description="请配置参数并运行" />

                <el-table v-else :data="results" style="width: 100%" border stripe>
                    <el-table-column prop="variable" label="Variable" width="180" />
                    <el-table-column label="Overall">
                        <template #default="scope">
                            <span v-if="scope.row.type === 'numeric'">
                                {{ scope.row.overall.mean }} ({{ scope.row.overall.sd }})
                            </span>
                            <span v-else>
                                <!-- Categorical overall count -->
                                {{ scope.row.overall.n }}
                            </span>
                        </template>
                    </el-table-column>
                    
                    <!-- Dynamic Group Columns -->
                    <!-- We need to know group names. We can extract them from the first result row's groups keys -->
                    <el-table-column v-for="g in groupNames" :key="g" :label="g">
                        <template #default="scope">
                             <div v-if="scope.row.groups">
                                 <span v-if="scope.row.type === 'numeric'">
                                     {{ scope.row.groups[g].mean }} ({{ scope.row.groups[g].sd }})
                                 </span>
                                 <div v-else>
                                     <div v-for="(count, val) in scope.row.groups[g].counts" :key="val">
                                         {{ val }}: {{ count }}
                                     </div>
                                 </div>
                             </div>
                        </template>
                    </el-table-column>

                    <el-table-column v-if="config.groupBy" prop="p_value" label="P-value" width="100" fixed="right">
                         <template #default="scope">
                             <el-tag :type="pValTag(scope.row.p_value)">{{ scope.row.p_value }}</el-tag>
                             <br/>
                             <span style="font-size: 0.8em; color: gray">{{ scope.row.test }}</span>
                         </template>
                    </el-table-column>
                </el-table>
            </el-card>
        </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import api from '../../../api/client'
import { ElMessage } from 'element-plus'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const loading = ref(false)
const results = ref([])
const groupNames = ref([])

const config = reactive({
    groupBy: null,
    variables: []
})

const variableOptions = computed(() => {
    if (!props.metadata) return []
    return Object.keys(props.metadata).map(k => ({
        label: k,
        value: k,
        role: props.metadata[k] // 'target', 'feature', etc (from meta) - actually meta structure is distinct.
        // wait, metadata format in ProjectWorkspace pass is actually simple dict? 
        // Let's assume metadata is { col: type } or { col: {role:..} }. 
        // Previous logs show metadata is a dict of col->type strings from initial inference?
        // Actually Metadata is usually managed. Let's rely on keys for now.
    }))
})

// Filter categorical for GroupBy (usually few unique values, but here just heuristic or user choice)
const categoricalOptions = computed(() => {
    return variableOptions.value // Allow any for now, user knows better
})

const allOptions = computed(() => variableOptions.value)

const generateTable = async () => {
    if (config.variables.length === 0) {
        ElMessage.warning("请至少选择一个统计变量")
        return
    }
    
    loading.value = true
    results.value = []
    groupNames.value = []

    try {
        const { data } = await api.post('/statistics/table1', {
            dataset_id: props.datasetId,
            group_by: config.groupBy,
            variables: config.variables
        })
        
        results.value = data.table1
        
        // Extract group names from first result that has groups
        if (config.groupBy && results.value.length > 0) {
            const first = results.value.find(r => r.groups)
            if (first) {
                groupNames.value = Object.keys(first.groups).sort()
            }
        }
        
        ElMessage.success("生成成功")
    } catch (error) {
        ElMessage.error(error.response?.data?.message || "生成失败")
    } finally {
        loading.value = false
    }
}

const pValTag = (info) => {
    if (info === 'N/A') return 'info'
    if (info === '<0.001') return 'danger'
    const val = parseFloat(info)
    if (!isNaN(val) && val < 0.05) return 'danger'
    return 'success' 
}

const exportExcel = async () => {
    try {
        const response = await api.post('/statistics/table1/export', {
            dataset_id: props.datasetId,
            group_by: config.groupBy,
            variables: config.variables,
            format: 'csv'
        }, { responseType: 'blob' })
        
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', 'Table1_Baseline.csv')
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        ElMessage.success("导出成功")
    } catch (error) {
         ElMessage.error("导出失败")
    }
}
</script>

<style scoped>
.tableone-container {
    padding: 20px;
}
</style>
