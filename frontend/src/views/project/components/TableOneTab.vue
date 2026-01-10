
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
                    <!-- Guidance Alert -->
                    <el-alert
                        title="基线表 (Table 1) 指南"
                        type="info"
                        show-icon
                        :closable="false"
                        style="margin-bottom: 20px"
                    >
                        <template #default>
                            <div style="font-size: 13px; color: #606266; line-height: 1.6;">
                                <li><b>Overall</b>: 全人群的统计描述（均值±标准差 或 频数）。</li>
                                <li><b>P-value</b>: 评估组间均衡性。若 <b>P < 0.05</b>，代表该变量在组间分布不均，建模时可能需要作为混杂因子校正。</li>
                                <li><b>统计检验</b>: 系统根据数据分布自动选择：正态分布选 T检验/ANOVA，非正态选非参检验，分类变量选卡方检验。</li>
                            </div>
                        </template>
                    </el-alert>
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
                
                <PublicationTable 
                    v-else 
                    :data="results" 
                    highlight-current-row
                    @row-click="(row) => selectedRow = row"
                >
                    <el-table-column prop="variable" label="Variable" width="180">
                        <template #default="scope">
                            <el-link type="primary" :underline="false" @click.stop="openDistribution(scope.row.variable)">
                                {{ scope.row.variable }}
                            </el-link>
                        </template>
                    </el-table-column>
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

                    <el-table-column v-if="config.groupBy" prop="p_value" width="150" fixed="right">
                         <template #header>
                             <GlossaryTooltip term="p_value">P-value</GlossaryTooltip>
                         </template>
                         <template #default="scope">
                             <StatValue :value="scope.row.p_value" type="p-value" />
                             
                             <div style="margin-top: 5px;">
                                 <el-tooltip 
                                    v-if="scope.row._meta && scope.row._meta.selection_reason"
                                    :content="scope.row._meta.selection_reason"
                                    placement="left"
                                 >
                                    <span style="font-size: 0.8em; color: gray; cursor: help; border-bottom: 1px dashed gray;">
                                        {{ scope.row.test }}
                                    </span>
                                 </el-tooltip>
                                 <span v-else style="font-size: 0.8em; color: gray">
                                     {{ scope.row.test }}
                                 </span>
                             </div>
                         </template>
                    </el-table-column>
                </PublicationTable>
                
                <InterpretationPanel 
                    v-if="selectedRow && selectedRow.interpretation"
                    :interpretation="selectedRow.interpretation"
                />
                <el-empty v-else-if="results.length > 0" description="点击表格行查看详细智能分析" :image-size="60" />
            </el-card>
        </el-col>
    </el-row>

    <DistributionDialog 
        v-model="distVisible"
        :dataset-id="datasetId"
        :variable="clickedVar"
    />
  </div>
</template>

<script setup>
/**
 * TableOneTab.vue
 * 基线特征描述表 (Table 1) 组件。
 * 
 * 职责：
 * 1. 提供变量选择和分组设置界面。
 * 2. 展示统计描述结果（均值±标准差 或 频数/百分比）。
 * 3. 自动计算组间差异的 P 值（T检验、ANOVA 或 卡方检验）。
 */
import { ref, computed, reactive } from 'vue'
import api from '../../../api/client'
import { ElMessage } from 'element-plus'
import InterpretationPanel from './InterpretationPanel.vue'
import GlossaryTooltip from './GlossaryTooltip.vue'
import DistributionDialog from './DistributionDialog.vue'
import PublicationTable from '../../../components/PublicationTable.vue'
import StatValue from '../../../components/StatValue.vue'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const distVisible = ref(false)
const clickedVar = ref('')

const openDistribution = (varName) => {
    clickedVar.value = varName
    distVisible.value = true
}

const loading = ref(false)
const results = ref([])
const groupNames = ref([])
const selectedRow = ref(null)

const config = reactive({
    groupBy: null,
    variables: []
})

const variableOptions = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables.map(v => ({
        label: v.name,
        value: v.name,
        type: v.type
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
