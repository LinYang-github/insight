<template>
  <div class="preprocessing-container">
     <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>
    
    <div v-else-if="!metadata">
         <el-empty description="无法获取数据元信息" />
    </div>

    <div v-else>
        <!-- Data Repair Section -->
        <el-card shadow="hover" class="mb-4">
            <template #header>
                <div class="card-header">
                    <div style="display: flex; align-items: center;">
                        <span>缺失值处理 (Data Repair)</span>
                         <el-tooltip content="修补数据中的空缺值，避免模型运行报错。" placement="top">
                            <el-icon style="margin-left: 5px; cursor: pointer;"><QuestionFilled /></el-icon>
                        </el-tooltip>
                    </div>
                    <div style="display: flex; gap: 10px; align-items: center;">
                         <el-popover placement="bottom" title="保存选项 (Output Options)" :width="250" trigger="click">
                            <template #reference>
                                <el-button size="small">输出设置: {{ saveMode === 'new' ? '另存为新' : '覆盖当前' }} <el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                            </template>
                            <el-radio-group v-model="saveMode" style="display: flex; flex-direction: column; align-items: flex-start;">
                                <el-radio value="new" size="small">另存为新数据集 (Save as New)</el-radio>
                                <el-radio value="overwrite" size="small">覆盖当前数据集 (Overwrite)</el-radio>
                            </el-radio-group>
                        </el-popover>
                        <el-divider direction="vertical" />
                        <el-button 
                            type="primary" 
                            size="small" 
                            @click="handleSmartFix" 
                            :loading="isSuggesting" 
                            icon="MagicStick"
                            class="ai-btn"
                        >
                            {{ isSuggesting ? 'AI 正在分析...' : 'AI 一键智修' }}
                        </el-button>
                        <el-button type="success" size="small" @click="handleImpute" :loading="processing">应用自定义策略</el-button>
                    </div>
                </div>
            </template>
            <!-- Guidance Alert -->
            <el-alert
                v-if="aiReasons.length > 0"
                title="AI 修复建议理由"
                type="success"
                show-icon
                class="mb-4"
                :closable="true"
            >
                 <template #default>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #606266;">
                        <li v-for="(r, idx) in aiReasons" :key="idx">{{ r }}</li>
                    </ul>
                 </template>
            </el-alert>
            
            <el-alert
                v-else
                title="操作说明"
                type="info"
                show-icon
                :closable="false"
                class="mb-4"
            >
                <template #default>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #606266;">
                        <li><b>AI 一键智修</b>：利用 LLM 根据变量语义和缺失率自动推荐填补策略。</li>
                        <li><b>应用策略</b>：任何提交的操作都将生成一个<b>新版本的数据集</b>，系统会自动切换至该版本。</li>
                    </ul>
                </template>
            </el-alert>
            <el-table :data="missingData" style="width: 100%" stripe border size="small">
                 <el-table-column prop="name" label="变量名" />
                 <el-table-column prop="type" label="类型" width="100" />
                 <el-table-column prop="missing" label="缺失数量" width="100">
                      <template #default="scope">
                          <span :class="{ 'red-text': (scope.row.missing || scope.row.missing_count) > 0 }">
                            {{ scope.row.missing !== undefined ? scope.row.missing : scope.row.missing_count }}
                          </span>
                      </template>
                 </el-table-column>
                 <el-table-column label="处理策略 (Strategy)" width="220">
                     <template #default="scope">
                         <el-select v-model="imputeStrategies[scope.row.name]" placeholder="选择策略" size="small" :disabled="(scope.row.missing || scope.row.missing_count) === 0" style="width: 100%">
                             <el-option label="忽略 (Ignore)" value="ignore" />
                             <el-option label="剔除缺失行 (Drop Rows)" value="drop" />
                             <el-option v-if="isNumeric(scope.row.type)" label="均值填补 (Mean)" value="mean" />
                             <el-option v-if="isNumeric(scope.row.type)" label="中位数填补 (Median)" value="median" />
                             <el-option v-if="isNumeric(scope.row.type)" label="多重插补 (MICE)" value="mice" />
                             <el-option v-if="isNumeric(scope.row.type)" label="随机森林 (Random Forest)" value="random_forest" />
                             <el-option label="众数填补 (Mode)" value="mode" />
                         </el-select>
                     </template>
                 </el-table-column>
            </el-table>
        </el-card>

        <!-- Digitization Section -->
        <el-card shadow="hover">
            <template #header>
                 <div class="card-header">
                     <div style="display: flex; align-items: center;">
                        <span>文本数值化 (Digitization)</span>
                        <el-tooltip content="将文本/分类变量转换为计算机可读的数值 (0, 1, 2...)。" placement="top">
                            <el-icon style="margin-left: 5px; cursor: pointer;"><QuestionFilled /></el-icon>
                        </el-tooltip>
                    </div>
                    <el-button type="success" size="small" @click="handleEncode" :loading="processing">应用并另存为新数据集</el-button>
                </div>
            </template>
            
            <!-- ============================== -->
            <!-- 提示信息区 (Info Alert)        -->
            <!-- ============================== -->
            <el-alert title="勾选不仅是“分类”且目前是“文本”格式的变量，将其转换为数字编码。" type="info" show-icon style="margin-bottom: 10px" />
            
            <!-- ============================== -->
            <!-- 因子化变量选择区 (Config Panel) -->
            <!-- ============================== -->
            <el-checkbox-group v-model="selectedEncodeCols">
                <el-row :gutter="20">
                     <el-col :span="6" v-for="col in categoricalCols" :key="col.name">
                         <el-checkbox :label="col.name" border style="width: 100%; margin-bottom: 10px" />
                     </el-col>
                </el-row>
            </el-checkbox-group>
            
            <div v-if="categoricalCols.length === 0" class="empty-text">
                没有检测到需要转换的分类变量。
            </div>
        </el-card>
    </div>
  </div>
</template>

<script setup>
/**
 * PreprocessingTab.vue
 * 数据清洗与预处理组件。
 * 
 * 职责：
 * 1. 识别并修补缺失值（Imputation）。
 * 2. 文本变量数值化编码（One-Hot Encoding）。
 * 3. 触发后端生成并持久化处理后的新数据集。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { QuestionFilled, MagicStick } from '@element-plus/icons-vue'
import api from '../../../api/client'

const props = defineProps({
    datasetId: { type: Number, required: true },
    metadata: { type: Object, default: null }
})

const emit = defineEmits(['dataset-created'])

const loading = ref(false)
const processing = ref(false)
const isSuggesting = ref(false)
const aiReasons = ref([])
const imputeStrategies = ref({})
const selectedEncodeCols = ref([])
const saveMode = ref('new') // 'new' or 'overwrite'

// 可重用的保存选项控制 (如有需要可提取)
// For now, let's just make sure we pass it.

const missingData = computed(() => {
    if (!props.metadata) return []
    return props.metadata.variables.filter(v => true) // All variables
})

const categoricalCols = computed(() => {
    if (!props.metadata) return []
    return props.metadata.variables.filter(v => ['object', 'category', 'string', 'categorical', 'text/id'].includes(v.type) || (v.type === 'numerical' && v.unique_count < 10)) // Legacy fallback
})

const isNumeric = (type) => {
    return ['int64', 'float64', 'int', 'float', 'continuous', 'numerical'].includes(type)
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

const handleSmartFix = async () => {
    /**
     * AI 智能修复逻辑：
     * 1. 调用 AI 接口获取推荐策略。
     * 2. 更新界面上的策略选择。
     * 3. 提示用户查看理由并手动决定是否立即“应用”。
     */
    isSuggesting.value = true
    aiReasons.value = []
    try {
        const { data } = await api.post('/preprocessing/ai-suggest-strategies', {
            dataset_id: props.datasetId
        })
        
        const recs = data.strategies || {}
        aiReasons.value = data.reasons || []
        
        // Update local strategies
        for (const [col, method] of Object.entries(recs)) {
            if (imputeStrategies.value.hasOwnProperty(col)) {
                imputeStrategies.value[col] = method
            }
        }
        
        ElMessage({
            message: 'AI 策略生成成功，已更新下方表格。请核选后点击“应用自定义策略”执行。',
            type: 'success',
            duration: 6000
        })
    } catch (e) {
        console.error("AI Suggestion failed", e)
        ElMessage.error(e.response?.data?.message || 'AI 建议生成失败')
    } finally {
        isSuggesting.value = false
    }
}

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
            strategies: activeStrategies,
            save_mode: saveMode.value
        })
        ElMessage.success({
            message: '处理成功！已为您生成并切换至修复后的数据集版本。',
            duration: 5000
        })
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
            columns: selectedEncodeCols.value,
            save_mode: saveMode.value
        })
        ElMessage.success({
            message: '因子化处理完成！已为您生成并切换至新版数据集。',
            duration: 5000
        })
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
.ai-btn {
    background: linear-gradient(45deg, #a855f7, #6366f1);
    border: none;
    transition: all 0.3s;
}
.ai-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(168, 85, 247, 0.4);
}
</style>
