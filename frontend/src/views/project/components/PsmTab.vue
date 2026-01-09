
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
                    <!-- Guidance Alert -->
                    <el-alert
                        title="PSM 操作指南"
                        type="info"
                        show-icon
                        :closable="false"
                        style="margin-bottom: 20px"
                    >
                        <template #default>
                            <div style="font-size: 13px; color: #606266; line-height: 1.6;">
                                <li><b>处理组变量</b>: 分组因素（如：用药 vs 不用药），必须是 0/1 变量。</li>
                                <li><b>协变量</b>: 您希望在组间达到均衡的混杂因素（如：年龄、性别、基线病史）。</li>
                                <li><b>均衡性标准</b>: 匹配后 <b>SMD < 0.1</b> 代表两组达到临床认可的良好均衡。</li>
                            </div>
                        </template>
                    </el-alert>
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
                            <template #header>
                                <span>匹配前 SMD</span>
                                <el-tooltip content="Standardized Mean Difference (标准化均数差)，衡量原始组间的差异。" placement="top">
                                    <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </template>
                            <template #default="scope">{{ scope.row.smd_pre.toFixed(3) }}</template>    
                        </el-table-column>
                        <el-table-column prop="smd_post" label="匹配后 SMD">
                            <template #header>
                                <span>匹配后 SMD</span>
                                <el-tooltip content="匹配后两组间的差异。理想情况下应 < 0.1，表明达到高度均衡。" placement="top">
                                    <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </template>
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
                     
                     <!-- Love Plot -->
                     <div style="margin-top: 30px;">
                        <div class="card-header" style="margin-bottom: 15px; font-weight: bold;">
                             <span>协变量平衡图 (Love Plot)</span>
                        </div>
                        <div id="love-plot" style="width: 100%; height: 500px;"></div>
                     </div>
                </div>
                <el-empty v-else description="请配置参数并运行匹配" />
                
            </el-card>
        </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * PsmTab.vue
 * 倾向性评分匹配 (PSM) 组件。
 * 
 * 职责：
 * 1. 提供处理变量 (Treatment) 和协变量 (Covariates) 的选择。
 * 2. 执行 1:1 最近邻匹配。
 * 3. 展示匹配前后的均衡性诊断（SMD, 标准化均数差）。
 */
import { ref, reactive, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'

/**
 * 评估匹配后的均衡性。
 * @description
 * 临床研究中，SMD < 0.1 通常被认为组间达到良好均衡。
 */

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
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables.map(v => ({ 
        label: v.name, 
        value: v.name 
    }))
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
            ElMessage.success({
                message: "匹配成功！已为您生成并自动切换至匹配后的新数据集版本。",
                duration: 5000
            })
        }
        
        // Render Love Plot
        nextTick(() => {
            renderLovePlot(data.balance)
        })
        
    } catch (error) {
        ElMessage.error(error.response?.data?.message || "匹配失败")
    } finally {
        loading.value = false
    }
}

const renderLovePlot = (balanceData) => {
    // balanceData: [{variable, smd_pre, smd_post}, ...]
    // Sort logic? Usually by pre-match SMD desc? Or just natural order.
    // Let's sort by Pre-match SMD for better visual
    const sorted = [...balanceData].sort((a,b) => Math.abs(a.smd_pre) - Math.abs(b.smd_pre));
    
    const vars = sorted.map(d => d.variable);
    const pre = sorted.map(d => Math.abs(d.smd_pre));
    const post = sorted.map(d => Math.abs(d.smd_post));
    
    const trace1 = {
        x: pre,
        y: vars,
        mode: 'markers',
        name: 'Unmatched',
        marker: { color: '#F56C6C', size: 10, symbol: 'circle-open' }, // Red open circle
        type: 'scatter'
    };
    
    const trace2 = {
        x: post,
        y: vars,
        mode: 'markers',
        name: 'Matched',
        marker: { color: '#67C23A', size: 10, symbol: 'circle' }, // Green filled circle
        type: 'scatter'
    };
    
    const layout = {
        title: 'Covariate Balance (Love Plot)',
        xaxis: { 
            title: 'Absolute Standardized Mean Difference (SMD)', 
            range: [0, Math.max(0.2, ...pre) + 0.1],
            zeroline: true
        },
        yaxis: { 
            title: '',
            automargin: true 
        },
        shapes: [
            {
                type: 'line',
                x0: 0.1, x1: 0.1,
                y0: 0, y1: 1, yref: 'paper',
                line: { color: 'gray', width: 1, dash: 'dash' }
            }
        ],
        margin: { l: 150, r: 20, t: 40, b: 40 },
        legend: { x: 0.8, y: 0.1 }
    };
    
    Plotly.newPlot('love-plot', [trace1, trace2], layout);
}
</script>

<style scoped>
.psm-container {
    padding: 20px;
}
</style>
