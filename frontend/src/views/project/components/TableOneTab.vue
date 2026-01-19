
<template>
  <div class="tableone-container">
    <el-row :gutter="20">
        <!-- Config Panel -->
        <el-col :span="6">
            <el-card class="box-card">
                <template #header>
                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <span>参数配置</span>
                        <el-button 
                            type="primary" 
                            link 
                            :icon="MagicStick" 
                            @click="suggestRoles"
                            :loading="isSuggesting"
                        >
                            AI 智能推荐
                        </el-button>
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
                        <span>基线特征表 (Table 1: Baseline Characteristics)</span>
                        <div v-if="results.length > 0" style="display: flex; gap: 8px;">
                            <el-button 
                                type="primary" 
                                size="small" 
                                @click="runAIAnalysis" 
                                :loading="isAnalyzing"
                                :icon="MagicStick"
                                class="ai-baseline-btn"
                                :disabled="!config.groupBy"
                            >
                                AI 均衡性分析
                            </el-button>
                            <el-button v-if="methodology" type="info" size="small" @click="copyMethodology" plain icon="Document">复制方法学</el-button>
                            <el-button type="success" size="small" @click="exportExcel" icon="Download">导出 Excel</el-button>
                        </div>
                    </div>
                </template>

                <el-empty v-if="results.length === 0" description="请配置参数并运行" />
                
                <PublicationTable 
                    v-else 
                    :data="results" 
                    highlight-current-row
                    @row-click="(row) => selectedRow = row"
                >
                    <el-table-column prop="variable" label="变量 (Variable)" width="180">
                        <template #default="scope">
                            <el-link type="primary" underline="never" @click.stop="openDistribution(scope.row.variable)">
                                {{ scope.row.variable }}
                            </el-link>
                        </template>
                    </el-table-column>
                    <el-table-column label="合计 (Overall)">
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
                             <GlossaryTooltip term="p_value">P 值 (P-value)</GlossaryTooltip>
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
                
                <!-- Global AI Analysis Report -->
                <InterpretationPanel 
                    v-if="globalAnalysis"
                    :interpretation="{ text: globalAnalysis, is_ai: true, level: 'info' }"
                    style="margin-top: 20px;"
                />

                <div v-if="results.length > 0" style="margin-top: 25px;">
                    <el-divider content-position="left">
                        <el-icon><InfoFilled /></el-icon> 变量详析 (Variable Details)
                    </el-divider>
                    <InterpretationPanel 
                        v-if="selectedRow && selectedRow.interpretation"
                        :interpretation="selectedRow.interpretation"
                    />
                    <el-empty v-else description="点击表格行查看该变量的详细智能解读" :image-size="40" />
                </div>
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
 * 1. 提供变量选择和分组设置界面，支持对全人群或分组人群进行基线描述。
 * 2. 智能选择统计方法：正态分布选 T 检验/ANOVA，非正态选非参检验，分类变量选卡方/Fisher。
 * 3. 实时可视化变量分布（直通 DistributionDialog）。
 * 4. 支持复制符合 SCI 发表规范的方法学段落，并支持导出表格。
 */
import { ref, computed, reactive } from 'vue'
import api from '../../../api/client'
import { ElMessage } from 'element-plus'
import { MagicStick, InfoFilled, Document, Download } from '@element-plus/icons-vue'
import InterpretationPanel from './InterpretationPanel.vue'
import GlossaryTooltip from './GlossaryTooltip.vue'
import DistributionDialog from './DistributionDialog.vue'
import PublicationTable from '../../../components/PublicationTable.vue'
import StatValue from '../../../components/StatValue.vue'
import { useVariableOptions } from '../../../composables/useVariableOptions'

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

const loading = ref(false) // 加载状态
const results = ref([])    // Table 1 结果数组
const groupNames = ref([]) // 动态提取的组别名称列表
const selectedRow = ref(null) // 当前选中的行，用于高亮显示智能解读
const globalAnalysis = ref(null) // 全局 AI 分析结论
const isAnalyzing = ref(false)
const isSuggesting = ref(false)

const config = reactive({
    groupBy: null,
    variables: []
})

// 使用公共 Composable 提取变量选项
const { 
    allOptions: variableOptions,
    categoricalOptions: categoricalOnlyOptions
} = useVariableOptions(computed(() => props.metadata))

// Table 1 一般允许所有变量作为行列显示
const categoricalOptions = computed(() => variableOptions.value)
const allOptions = computed(() => variableOptions.value)

const methodology = ref('')

/**
 * 调用后端接口生成基线表数据。
 */
const generateTable = async () => {
    if (config.variables.length === 0) {
        ElMessage.warning("请至少选择一个统计变量")
        return
    }
    
    loading.value = true
    results.value = []
    groupNames.value = []
    methodology.value = ''
    globalAnalysis.value = null
    selectedRow.value = null

    try {
        const { data } = await api.post('/statistics/table1', {
            dataset_id: props.datasetId,
            group_by: config.groupBy,
            variables: config.variables
        })
        
        results.value = data.table1
        methodology.value = data.methodology
        
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

const runAIAnalysis = async () => {
    if (results.value.length === 0) return
    if (!config.groupBy) {
        ElMessage.warning("请先设置‘分组变量’以进行均衡性分析")
        return
    }

    isAnalyzing.value = true
    try {
        const { data } = await api.post('/statistics/ai-analyze-table1', {
            table_data: results.value,
            group_by: config.groupBy
        })
        
        globalAnalysis.value = data.analysis
        ElMessage.success("AI 均衡性分析完成")
    } catch (e) {
        console.error("AI Analysis failed", e)
        ElMessage.error(e.response?.data?.message || "AI 分析失败")
    } finally {
        isAnalyzing.value = false
    }
}

const suggestRoles = async () => {
    isSuggesting.value = true
    try {
        const { data } = await api.post('/statistics/ai-suggest-roles', {
            dataset_id: props.datasetId,
            analysis_type: 'table1'
        })
        
        config.groupBy = data.groupBy || config.groupBy
        config.variables = data.variables || config.variables
        
        ElMessage({
            message: `AI 已为您推荐基线表的最佳配置方案。\n理由: ${data.reason || '基于临床显著性推荐'}`,
            type: 'success',
            duration: 5000
        })
    } catch (e) {
        console.error("AI Role suggestion failed", e)
        ElMessage.error(e.response?.data?.message || "AI 推荐失败")
    } finally {
        isSuggesting.value = false
    }
}

const copyMethodology = () => {
    if (!methodology.value) {
        ElMessage.info('暂无方法学内容')
        return
    }
    navigator.clipboard.writeText(methodology.value).then(() => {
        ElMessage.success('方法学段落已复制')
    }).catch(err => {
        ElMessage.error('复制失败')
    })
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
.ai-baseline-btn {
    background: linear-gradient(45deg, #6366f1, #a855f7);
    border: none;
    transition: all 0.3s ease;
}
.ai-baseline-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
}
.ai-baseline-btn.is-disabled {
    background: #f5f7fa;
    color: #c0c4cc;
}
</style>
