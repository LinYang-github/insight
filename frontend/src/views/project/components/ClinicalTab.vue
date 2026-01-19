<template>
  <div class="clinical-tab">
     <el-row :gutter="20">
        <!-- Left: Tool Selection -->
        <el-col :span="8">
            <el-card class="tool-list">
                <template #header>
                    <div class="card-header">
                        <span>🩺 临床工具箱 (Clinical Toolbox)</span>
                    </div>
                </template>
                <el-collapse v-model="activeTool" accordion>
                    <el-collapse-item title="eGFR 自动计算器" name="egfr">
                        <div class="tool-desc">
                            根据肌酐、年龄、性别等指标自动计算肾小球滤过率 (eGFR)。
                        </div>
                        <el-radio-group v-model="egfrMethod" class="method-select">
                            <el-radio value="egfr_ckdepi2021" border>CKD-EPI 2021 (推荐)</el-radio>
                            <el-radio value="egfr_ckdepi2009" border>CKD-EPI 2009</el-radio>
                            <el-radio value="egfr_mdrd" border>MDRD (简化版)</el-radio>
                            <el-radio value="egfr_schwartz" border>Schwartz (儿童)</el-radio>
                        </el-radio-group>
                    </el-collapse-item>
                    
                     <el-collapse-item title="CKD 自动分期" name="staging">
                        <div class="tool-desc">
                            根据 eGFR 和 ACR 进行 KDIGO 分期 (G1-G5, A1-A3) 及风险分层。
                        </div>
                    </el-collapse-item>
                    
                    <el-collapse-item title="纵向数据分析 (Longitudinal)" name="slope">
                        <div class="tool-desc">
                            分析 eGFR 随时间变化的趋势。包含：
                            1. 宽表转长表 (Wide to Long)
                            2. 斜率计算 (OLS Slope)
                        </div>
                    </el-collapse-item>
                </el-collapse>
            </el-card>
        </el-col>
        
        <!-- Right: Configuration & Execution -->
        <el-col :span="16">
            <el-card v-if="activeTool === 'egfr'">
                 <template #header>
                    <div class="card-header">
                        <span>⚙️ 参数映射 (Variable Mapping)</span>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <el-button 
                                type="primary" 
                                link 
                                :icon="MagicStick" 
                                @click="suggestRoles('egfr')"
                                :loading="isSuggestingRoles"
                            >
                                AI 智能推荐
                            </el-button>
                            <el-popover placement="bottom" title="保存选项 (Output Options)" :width="250" trigger="click">
                                <template #reference>
                                    <el-button size="small">输出设置: {{ saveMode === 'new' ? '另存为新' : '覆盖当前' }} <el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                                </template>
                                <el-radio-group v-model="saveMode" style="display: flex; flex-direction: column; align-items: flex-start;">
                                    <el-radio value="new" size="small">另存为新数据集 (Save as New)</el-radio>
                                    <el-radio value="overwrite" size="small">覆盖当前数据集 (Overwrite)</el-radio>
                                </el-radio-group>
                            </el-popover>
                             <el-button type="primary" @click="handleDerive" :loading="calculating" :disabled="!canCalculate">
                                立即计算 (Calculate)
                            </el-button>
                        </div>
                    </div>
                </template>
                
                <el-alert
                    title="公式说明"
                    type="info"
                    :closable="false"
                    show-icon
                    style="margin-bottom: 20px"
                >
                    <div v-if="egfrMethod === 'egfr_ckdepi2021'">
                        <b>CKD-EPI 2021 (新标准)</b>: 去种族化公式，适用于所有成年人群。
                        <div style="margin-top:5px; color:#E6A23C">
                             <el-icon><InfoFilled /></el-icon> <b>为什么首选?</b> 2021版公式移除了种族系数，消除了医疗中的潜在种族偏见，被 ASN/NKF 权威指南列为当前推荐公式。
                        </div>
                        <br/>需映射: <code>血肌酐 (Scr)</code>, <code>年龄 (Age)</code>, <code>性别 (Sex)</code>
                    </div>
                    <div v-else-if="egfrMethod === 'egfr_ckdepi2009'">
                        <b>CKD-EPI 2009</b>: 经典公式。需额外映射 <code>种族 (Race)</code>（如未提供则默认非黑人）。
                    </div>
                    <div v-else-if="egfrMethod === 'egfr_mdrd'">
                        <b>MDRD</b>: 适用于旧数据对比。
                    </div>
                     <div v-else-if="egfrMethod === 'egfr_schwartz'">
                        <b>Bedside Schwartz</b>: 专用于 18 岁以下儿童。需映射 <code>身高 (Height)</code> (cm)。
                    </div>
                </el-alert>
                
                <el-form label-position="top">
                    <el-row :gutter="20">
                        <el-col :span="12">
                             <el-form-item label="血肌酐 (Serum Creatinine, mg/dL)" required>
                                <el-select v-model="params.scr" placeholder="选择肌酐列" filterable>
                                    <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                             </el-form-item>
                        </el-col>
                         <el-col :span="12">
                             <el-form-item label="年龄 (Age, years)" required>
                                <el-select v-model="params.age" placeholder="选择年龄列" filterable>
                                    <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                             </el-form-item>
                        </el-col>
                    </el-row>
                    
                    <el-row :gutter="20">
                         <el-col :span="12">
                             <el-form-item label="性别 (Sex)" required>
                                <el-select v-model="params.sex" placeholder="选择性别列 (F/M or 0/1)" filterable>
                                    <el-option v-for="v in catVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                                <div class="form-helper">支持格式: (F, Female, Woman, 0) 为女性，其他为男性</div>
                             </el-form-item>
                        </el-col>
                        
                        <!-- Race (Optional for CKD-EPI 2009 / MDRD) -->
                        <el-col :span="12" v-if="['egfr_ckdepi2009', 'egfr_mdrd'].includes(egfrMethod)">
                             <el-form-item label="种族 (Race) - 可选">
                                <el-select v-model="params.race" placeholder="选择种族列 (Black/Non-Black)" filterable clearable>
                                    <el-option v-for="v in catVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                                <div class="form-helper">若留空，默认视为 Non-Black</div>
                             </el-form-item>
                        </el-col>
                        
                         <!-- Height (For Schwartz) -->
                        <el-col :span="12" v-if="egfrMethod === 'egfr_schwartz'">
                             <el-form-item label="身高 (Height, cm)" required>
                                <el-select v-model="params.height" placeholder="选择身高列" filterable>
                                    <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                             </el-form-item>
                        </el-col>

                    </el-row>
                </el-form>
                
            </el-card>
            <el-card v-else-if="activeTool === 'staging'">
                 <template #header>
                    <div class="card-header">
                        <span>📊 CKD 分期 (Staging & Risk)</span>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <el-button 
                                type="primary" 
                                link 
                                :icon="MagicStick" 
                                @click="suggestRoles('staging')"
                                :loading="isSuggestingRoles"
                            >
                                AI 智能推荐
                            </el-button>
                            <el-popover placement="bottom" title="保存选项 (Output Options)" :width="250" trigger="click">
                                <template #reference>
                                    <el-button size="small">输出设置: {{ saveMode === 'new' ? '另存为新' : '覆盖当前' }} <el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                                </template>
                                <el-radio-group v-model="saveMode" style="display: flex; flex-direction: column; align-items: flex-start;">
                                    <el-radio value="new" size="small">另存为新数据集 (Save as New)</el-radio>
                                    <el-radio value="overwrite" size="small">覆盖当前数据集 (Overwrite)</el-radio>
                                </el-radio-group>
                            </el-popover>
                            <el-button type="primary" @click="handleStage" :loading="calculating" :disabled="!canStage">
                                立即分期 (Stage)
                            </el-button>
                        </div>
                    </div>
                </template>
                
                <el-alert
                    title="分期说明 (KDIGO 2012)"
                    type="warning"
                    :closable="false"
                    show-icon
                    style="margin-bottom: 20px"
                >
                    <div>
                        <b>G-Stage (G1-G5)</b>: 基于 eGFR。
                        <br/>
                        <b>A-Stage (A1-A3)</b>: 基于 ACR/PCR。
                        <br/>
                        <b>风险分层</b>: 综合 G/A 分期生成的 4 级颜色预警 (Low/Moderate/High/Very High)。
                    </div>
                </el-alert>

                <el-form label-position="top">
                    <el-row :gutter="20">
                         <el-col :span="12">
                             <el-form-item label="eGFR 列 (必选)" required>
                                <el-select v-model="stagingParams.egfr" placeholder="选择 eGFR 变量" filterable>
                                    <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                             </el-form-item>
                        </el-col>
                         <el-col :span="12">
                             <el-form-item label="ACR/PCR 列 (可选, mg/g)">
                                <el-select v-model="stagingParams.acr" placeholder="选择白蛋白尿变量" filterable clearable>
                                    <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                                <div class="form-helper">用于计算 A 分期及风险分层</div>
                             </el-form-item>
                        </el-col>
                    </el-row>
                </el-form>
            </el-card>

            <el-card v-else-if="activeTool === 'slope'">
                 <template #header>
                    <div class="card-header">
                        <span>📈 纵向趋势分析 (Slope Analysis)</span>
                        <div style="display: flex; gap: 10px; align-items: center;">
                             <el-button 
                                type="primary" 
                                link 
                                :icon="MagicStick" 
                                @click="suggestRoles('slope')"
                                :loading="isSuggestingRoles"
                            >
                                AI 智能推荐
                            </el-button>
                             <!-- Melt Actions -->
                             <template v-if="slopeMode === 'melt'">
                                <el-popover placement="bottom" title="保存选项 (Output Options)" :width="250" trigger="click">
                                    <template #reference>
                                        <el-button size="small">输出设置: {{ saveMode === 'new' ? '另存为新' : '覆盖当前' }} <el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                                    </template>
                                    <el-radio-group v-model="saveMode" style="display: flex; flex-direction: column; align-items: flex-start;">
                                        <el-radio value="new" size="small">另存为新数据集 (Save as New)</el-radio>
                                        <el-radio value="overwrite" size="small">覆盖当前数据集 (Overwrite)</el-radio>
                                    </el-radio-group>
                                </el-popover>
                                <el-button type="primary" @click="handleMelt" :loading="calculating" :disabled="!canMelt">
                                    开始转换 (Convert)
                                </el-button>
                             </template>

                             <!-- Slope Actions -->
                             <template v-if="slopeMode === 'calc'">
                                <el-popover placement="bottom" title="保存选项 (Output Options)" :width="250" trigger="click">
                                    <template #reference>
                                        <el-button size="small">输出设置: {{ saveMode === 'new' ? '另存为新' : '覆盖当前' }} <el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
                                    </template>
                                    <el-radio-group v-model="saveMode" style="display: flex; flex-direction: column; align-items: flex-start;">
                                        <el-radio value="new" size="small">另存为新数据集 (Save as New)</el-radio>
                                        <el-radio value="overwrite" size="small">覆盖当前数据集 (Overwrite)</el-radio>
                                    </el-radio-group>
                                </el-popover>
                                <el-button type="primary" @click="handleSlope" :loading="calculating" :disabled="!canSlope">
                                    计算斜率 (Calculate Slope)
                                </el-button>
                             </template>
                        </div>
                    </div>
                </template>
                
                <el-tabs v-model="slopeMode">
                    <el-tab-pane value="步骤 1: 宽表转长表" name="melt">
                        <el-alert title="什么是宽表转长表?" type="info" :closable="false" style="margin-bottom: 20px">
                             <div style="line-height: 1.6">
                                 纵向分析（如计算斜率、线性混合模型）需要数据处于<b>长格式 (Long Format)</b>。
                                 <br/>
                                 <b>转换前 (宽表)</b>: 每个患者一行，不同时间点为不同列 (e.g. <code>eGFR_0m</code>, <code>eGFR_6m</code>)。
                                 <br/>
                                 <b>转换后 (长表)</b>: 每个患者多行，由 <code>Time</code> 列标记时间点。
                             </div>
                        </el-alert>
                         <el-form label-position="top">
                             <el-form-item label="病人 ID列 (Patient ID)" required>
                                <el-select v-model="meltParams.id_col" placeholder="选择ID列" filterable>
                                    <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                </el-select>
                             </el-form-item>
                             
                             <el-form-item label="时间点映射 (Time Points)" required>
                                 <div v-for="(item, index) in meltParams.points" :key="index" style="display: flex; gap: 10px; margin-bottom: 5px">
                                     <el-select v-model="item.col" placeholder="选择数值列 (e.g. Scr_T1)" filterable size="small">
                                         <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                     </el-select>
                                     <el-input v-model="item.time" placeholder="时间值 (e.g. 0, 6, 12)" size="small" style="width: 100px" type="number"/>
                                     <el-button @click="removeMeltPoint(index)" circle size="small" icon="Minus" />
                                 </div>
                                 <el-button size="small" @click="addMeltPoint" icon="Plus">添加时间点</el-button>
                             </el-form-item>
                             

                         </el-form>
                    </el-tab-pane>
                    
                    <el-tab-pane value="步骤 2: 计算斜率" name="calc">
                        <el-alert title="如何解读斜率 (Slope)?" type="success" :closable="false" style="margin-bottom: 20px">
                             <div>
                                 <b>定义</b>: eGFR 随时间变化的速率 (ml/min/1.73m²/year)。
                                 <br/>
                                 <b>解读</b>: 
                                 <li><b>负值 (e.g. -5.0)</b>: 代表肾功能下降。数值越小（负得越多），进展越快。</li>
                                 <li><b>正值</b>: 代表肾功能改善（较少见）。</li>
                                 <br/>
                                 <i>注: 计算基于普通最小二乘法 (OLS) 回归。</i>
                             </div>
                        </el-alert>
                        <el-form label-position="top">
                             <el-row :gutter="20">
                                <el-col :span="8">
                                     <el-form-item label="ID 列" required>
                                        <el-select v-model="slopeParams.id_col" placeholder="ID" filterable>
                                            <el-option v-for="v in allVars" :key="v.name" :label="v.name" :value="v.name" />
                                        </el-select>
                                     </el-form-item>
                                </el-col>
                                <el-col :span="8">
                                     <el-form-item label="时间列 (Time)" required>
                                        <el-select v-model="slopeParams.time_col" placeholder="Time" filterable>
                                            <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                        </el-select>
                                     </el-form-item>
                                </el-col>
                                <el-col :span="8">
                                     <el-form-item label="数值列 (Value)" required>
                                        <el-select v-model="slopeParams.value_col" placeholder="eGFR" filterable>
                                            <el-option v-for="v in numVars" :key="v.name" :label="v.name" :value="v.name" />
                                        </el-select>
                                     </el-form-item>
                                </el-col>
                             </el-row>

                        </el-form>
                    </el-tab-pane>
                </el-tabs>
            </el-card>
        </el-col>
     </el-row>
     
     <!-- Result Dialog: Not needed, we just switch dataset like Preprocessing -->
  </div>
</template>

<script setup>
/**
 * ClinicalTab.vue
 * 临床肾脏病学术工具箱。
 * 
 * 职责：
 * 1. eGFR 计算器：支持 CKD-EPI 2021/2009, MDRD, Schwartz 等多种公式自动衍生。
 * 2. CKD 自动分期：根据 KDIGO 2012 指南自动生成 G/A 分期及风险分层变量。
 * 3. 纵向数据转换：提供“宽表转长表”功能，为后续纵向分析做准备。
 * 4. 肾功能斜率计算：采用 OLS 方法计算个体 eGFR 变化速率。
 */
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../../api/client'
import { MagicStick, ArrowDown, InfoFilled, Plus, Minus } from '@element-plus/icons-vue'

const props = defineProps({
    dataset: Object,
    metadata: Object
})

const emit = defineEmits(['dataset-updated'])

const activeTool = ref('egfr') // 当前活跃的工具模块 (egfr/staging/slope)
const egfrMethod = ref('egfr_ckdepi2021') // 当前选中的 eGFR 计算公式
const calculating = ref(false) // 计算状态
const isSuggestingRoles = ref(false) // AI 推荐状态

const params = ref({
    scr: '',   // 血肌酐变量名
    age: '',   // 年龄变量名
    sex: '',   // 性别变量名
    race: '',  // 种族变量名（可选）
    height: '' // 身高变量名（Schwartz 专用）
})

const stagingParams = ref({
    egfr: '',
    acr: ''
})

const saveMode = ref('new') // 'new' or 'overwrite'

const slopeMode = ref('melt')
const meltParams = ref({
    id_col: '',
    points: [{ col: '', time: '' }]
})
const slopeParams = ref({
    id_col: '',   // 患者 ID 列
    time_col: '', // 时间轴列 (Time)
    value_col: '' // 待计算斜率的数值列
})

// Variables
const allVars = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables
})

const numVars = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables.filter(v => v.type === 'continuous')
})

const catVars = computed(() => {
    if (!props.metadata || !props.metadata.variables) return []
    return props.metadata.variables // Sex/Race can be string or int (0/1)
})

const canCalculate = computed(() => {
    if (egfrMethod.value === 'egfr_schwartz') {
        return params.value.scr && params.value.height
    }
    // Standard adult formulas
    // CKD-EPI 2021 only checks Scr, Age, Sex
    // Other Race is optional
    return params.value.scr && params.value.age && params.value.sex
})

/**
 * AI 智能角色推荐
 */
const suggestRoles = async (toolType) => {
    isSuggestingRoles.value = true
    try {
        const { data } = await api.post('/clinical/ai-suggest-roles', {
            dataset_id: props.dataset.dataset_id,
            tool_type: toolType
        })
        
        let reason = data.reasoning || '基于变量名智能推荐'
        let appliedCount = 0

        if (toolType === 'egfr') {
            if (data.scr) { params.value.scr = data.scr; appliedCount++ }
            if (data.age) { params.value.age = data.age; appliedCount++ }
            if (data.sex) { params.value.sex = data.sex; appliedCount++ }
            if (data.race) { params.value.race = data.race; appliedCount++ }
            if (data.height) { params.value.height = data.height; appliedCount++ }
        } else if (toolType === 'staging') {
            if (data.egfr) { stagingParams.value.egfr = data.egfr; appliedCount++ }
            if (data.acr) { stagingParams.value.acr = data.acr; appliedCount++ }
        } else if (toolType === 'slope') {
            if (data.id_col) { 
                slopeParams.value.id_col = data.id_col
                meltParams.value.id_col = data.id_col // Also set for melt
                appliedCount++ 
            }
            if (data.time_col) { slopeParams.value.time_col = data.time_col; appliedCount++ }
            if (data.value_col) { slopeParams.value.value_col = data.value_col; appliedCount++ }
        }
        
        if (appliedCount > 0) {
            ElMessage({
                message: `AI 已为您推荐 ${appliedCount} 个变量映射。\n理由: ${reason}`,
                type: 'success',
                duration: 5000
            })
        } else {
            ElMessage.warning('AI 未能识别出相关变量，请手动选择。')
        }

    } catch (e) {
        console.error("AI Suggestion failed", e)
        ElMessage.error(e.response?.data?.message || 'AI 推荐失败，请检查 API Key 配置')
    } finally {
        isSuggestingRoles.value = false
    }
}

/**
 * 执行 eGFR 衍生计算。
 */
const handleDerive = async () => {
    calculating.value = true
    try {
        const payload = {
            dataset_id: props.dataset.dataset_id,
            type: egfrMethod.value,
            params: {
                scr: params.value.scr,
                age: params.value.age,
                sex: params.value.sex,
                race: params.value.race,
                height: params.value.height
            },
            save_mode: saveMode.value
        }
        
        const { data } = await api.post('/clinical/derive-egfr', payload)
        
        ElMessage.success('计算成功！已生成新数据集。')
        
        // Notify parent to switch dataset
        emit('dataset-updated', data.new_dataset)
        
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '计算失败')
    } finally {
        calculating.value = false
    }
}

const canStage = computed(() => {
    return !!stagingParams.value.egfr
})

/**
 * 执行 CKD 分期与风险分层计算。
 */
const handleStage = async () => {
    calculating.value = true
    try {
        const payload = {
            dataset_id: props.dataset.dataset_id,
            params: {
                egfr: stagingParams.value.egfr,
                acr: stagingParams.value.acr
            },
            save_mode: saveMode.value
        }
        
        const { data } = await api.post('/clinical/stage-ckd', payload)
        ElMessage.success('分期完成！已生成 G/A/Risk 变量。')
        emit('dataset-updated', data.new_dataset)
        
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '分期失败')
    } finally {
        calculating.value = false
    }

}

// Slope Logic
const addMeltPoint = () => {
    meltParams.value.points.push({ col: '', time: '' })
}
const removeMeltPoint = (idx) => {
    meltParams.value.points.splice(idx, 1)
}

const canMelt = computed(() => {
    return meltParams.value.id_col && meltParams.value.points.length >= 2 && meltParams.value.points.every(p => p.col && p.time !== '')
})

/**
 * 执行数据宽表转长表转换。
 */
const handleMelt = async () => {
    calculating.value = true
    try {
        const time_mapping = {}
        meltParams.value.points.forEach(p => {
            time_mapping[p.col] = parseFloat(p.time)
        })
        
        const payload = {
            dataset_id: props.dataset.dataset_id,
            id_col: meltParams.value.id_col,
            time_mapping: time_mapping,
            value_name: 'eGFR_Long', // Hardcoded or parameterized?
            save_mode: saveMode.value
        }
         const { data } = await api.post('/clinical/melt', payload)
        ElMessage.success('转换成功！已生成长表数据集。')
        emit('dataset-updated', data.new_dataset)
        slopeMode.value = 'calc' // Auto switch to calc tab
    } catch(e) {
         ElMessage.error(e.response?.data?.message || '转换失败')
    } finally {
        calculating.value = false
    }
}

const canSlope = computed(() => {
    return slopeParams.value.id_col && slopeParams.value.time_col && slopeParams.value.value_col
})

/**
 * 执行 eGFR 变化斜率 (Slope) 计算。
 */
const handleSlope = async () => {
    calculating.value = true
    try {
        const payload = {
            dataset_id: props.dataset.dataset_id,
            id_col: slopeParams.value.id_col,
            time_col: slopeParams.value.time_col,
            value_col: slopeParams.value.value_col,
            save_mode: saveMode.value
        }
        const { data } = await api.post('/clinical/calculate-slope', payload)
        ElMessage.success('计算成功！已生成斜率数据集。')
        emit('dataset-updated', data.new_dataset)
    } catch(e) {
         ElMessage.error(e.response?.data?.message || '计算失败')
    } finally {
        calculating.value = false
    }
}
</script>

<style scoped>
.clinical-tab {
    padding: 10px;
}
.method-select {
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.method-select .el-radio {
    margin-right: 0;
    width: 100%;
}
.tool-desc {
    color: #666;
    font-size: 13px;
    margin-bottom: 10px;
    line-height: 1.5;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.form-helper {
    font-size: 12px;
    color: #909399;
    margin-top: 5px;
}
</style>
