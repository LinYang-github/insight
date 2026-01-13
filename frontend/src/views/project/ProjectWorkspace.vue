<template>
  <el-container class="project-container">
    <el-aside width="240px" class="project-sidebar">
        <div class="project-info-header" v-if="dataset">
            <div class="info-label">当前数据集 (Active Dataset)</div>
            <div class="info-value" :title="dataset.name">
                <el-icon><Document /></el-icon>
                <span>{{ dataset.name }}</span>
            </div>
            <div class="info-meta" v-if="dataset.metadata">
                {{ dataset.metadata.row_count }} 行 • {{ dataset.metadata.variables?.length }} 个变量
            </div>
        </div>

        <el-menu
            :default-active="activeTabName"
            class="el-menu-vertical"
            @select="(index) => activeTabName = index"
        >
            <div class="menu-group-title">📂 数据准备 (Data Readiness)</div>
            <el-menu-item index="data">
                <el-icon><Upload /></el-icon>
                <span>数据导入</span>
                <span class="status-dot" :class="dataset ? 'green' : 'gray'"></span>
            </el-menu-item>
             <el-menu-item index="data-mgmt" :disabled="!dataset">
                 <el-icon><FolderOpened /></el-icon>
                 <span>数据管理</span>
             </el-menu-item>
            <el-menu-item index="preprocessing" :disabled="!dataset">
                <el-icon><Brush /></el-icon>
                <span>数据体检 (Health Check)</span>
                <!-- TODO: 检查缺失值以确定状态 -->
                <span class="status-dot green"></span> 
            </el-menu-item>
            <el-menu-item index="clinical" :disabled="!dataset">
                <el-icon><FirstAidKit /></el-icon>
                <span>专科工程 (Clinical)</span>
            </el-menu-item>

            <div class="menu-group-title">📊 基线特征 (Baseline)</div>
             <el-menu-item index="table1" :disabled="!dataset">
                <el-icon><List /></el-icon>
                <span>基线表 (Table 1)</span>
            </el-menu-item>
            <el-menu-item index="eda" :disabled="!dataset">
                <el-icon><DataLine /></el-icon>
                <span>数据分布 (EDA)</span>
            </el-menu-item>
            
            <div class="menu-group-title">🎯 统计推断 (Inference)</div>
             <el-menu-item index="survival" :disabled="!dataset">
                <el-icon><Timer /></el-icon>
                <span>生存分析 (KM)</span>
            </el-menu-item>
             <el-menu-item index="psm" :disabled="!dataset">
                <el-icon><Connection /></el-icon>
                <span>倾向匹配 (PSM)</span>
            </el-menu-item>
             <el-menu-item index="iptw" :disabled="!dataset">
                <el-icon><ScaleToOriginal /></el-icon>
                <span>逆概率加权 (IPTW)</span>
            </el-menu-item>
             <el-menu-item index="competing" :disabled="!dataset">
                <el-icon><PieChart /></el-icon>
                <span>竞争风险 (Fine-Gray)</span>
            </el-menu-item>

            <div class="menu-group-title">🤖 多因素建模 (Modeling)</div>
            <el-menu-item index="modeling" :disabled="!dataset">
                <el-icon><TrendCharts /></el-icon>
                <span>回归建模 (Modeling)</span>
            </el-menu-item>
            <el-menu-item index="advanced" :disabled="!dataset">
                <el-icon><Histogram /></el-icon>
                <span>高级建模 (Advanced)</span>
            </el-menu-item>
            <el-menu-item index="longitudinal" :disabled="!dataset">
                <el-icon><Odometer /></el-icon>
                <span>纵向分析 (Longitudinal)</span>
            </el-menu-item>
            <el-menu-item index="viz" :disabled="!dataset">
                <el-icon><Cpu /></el-icon>
                <span>临床应用 (Nomogram)</span>
            </el-menu-item>
        </el-menu>
    </el-aside>

    <el-main class="project-main">
         <!-- 如果需要保留状态，可以在此处使用 Dynamic Component Cache -->
         <!-- 使用 v-if/v-show 或简单的 div 映射 -->
         <div v-if="activeTabName === 'data'">
             <DataTab :projectId="route.params.id" :dataset="dataset" @dataset-updated="handleDatasetUpdate" />
         </div>
         <div v-else-if="activeTabName === 'data-mgmt'">
             <DataManagementTab 
                :datasets="datasetList"
                :activeDatasetId="dataset?.dataset_id || dataset?.id"
                @dataset-switched="handleSwitchDataset" 
                @refresh-list="fetchDatasetList"
             />
         </div>
         <div v-else-if="activeTabName === 'preprocessing'">
             <PreprocessingTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" @dataset-created="handleDatasetCreated" />
         </div>
         <div v-else-if="activeTabName === 'clinical'">
             <ClinicalTab v-if="dataset?.dataset_id" :dataset="dataset" :metadata="dataset.metadata" @dataset-updated="handleDatasetUpdate" />
         </div>
         <div v-else-if="activeTabName === 'table1'">
             <TableOneTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'eda'">
             <EdaTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'survival'">
             <SurvivalTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'psm'">
             <PsmTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" @dataset-created="handleDatasetCreated" />
         </div>
         <div v-else-if="activeTabName === 'iptw'">
             <IPTWTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'competing'">
             <CompetingRiskTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'modeling'">
              <ModelingTab v-if="dataset?.dataset_id" :projectId="route.params.id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'advanced'">
             <AdvancedModelingTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'viz'">
             <ClinicalVizTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
         <div v-else-if="activeTabName === 'longitudinal'">
             <LongitudinalTab v-if="dataset?.dataset_id" :datasetId="dataset.dataset_id" :metadata="dataset.metadata" />
         </div>
    </el-main>
  </el-container>
</template>

<script setup>
/**
 * ProjectWorkspace.vue
 * 项目工作台主布局。
 * 
 * 职责：
 * 1. 管理左侧线性工作流导航（数据导入 -> 预处理 -> 描述性统计 -> 建模）。
 * 2. 维护数据集 (Dataset) 上下文，确保各子组件共享最新的元数据。
 * 3. 处理数据集更新事件，实现流程间的自动跳转（如导入成功后跳转至预处理）。
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import DataTab from './components/DataTab.vue'
import ModelingTab from './components/ModelingTab.vue'
import EdaTab from './components/EdaTab.vue'
import PreprocessingTab from './components/PreprocessingTab.vue'
import TableOneTab from './components/TableOneTab.vue'
import SurvivalTab from './components/SurvivalTab.vue'
import ClinicalTab from './components/ClinicalTab.vue'
import DataManagementTab from './components/DataManagementTab.vue'
import AdvancedModelingTab from './components/AdvancedModelingTab.vue'
import ClinicalVizTab from './components/ClinicalVizTab.vue'
import LongitudinalTab from './components/LongitudinalTab.vue'
import PsmTab from './components/PsmTab.vue'
import IPTWTab from './components/IPTWTab.vue'
import CompetingRiskTab from './components/CompetingRiskTab.vue'
import api from '../../api/client'

import { Upload, Brush, DataLine, TrendCharts, List, Timer, Connection, FirstAidKit, FolderOpened, Histogram, Cpu, Document, Odometer, ScaleToOriginal, PieChart } from '@element-plus/icons-vue'

const route = useRoute()
const dataset = ref(null) // 当前工作区的活跃数据集对象
const datasetList = ref([]) // 当前项目下的所有数据集列表
const activeTabName = ref('data') // 当前选中的左侧导航 Tab 名称

const handleTabChange = (name) => {
    // 逻辑占位
}

/**
 * 获取项目的基础元数据和最近活跃的数据集。
 */
const fetchProjectData = async () => {
    try {
        const { data } = await api.get(`/data/metadata/${route.params.id}`)
        dataset.value = data
        // 同时获取所有数据集以供管理？
        // 目前元数据端点仅返回“最新”的一条。
        // 我们可能需要一个专门的列表端点。
        // 暂时假设元数据端点已扩展，或者我们稍后添加列表端点。
        // 等等，当前设计是：1 个项目对应 N 个数据集。
        // 稍后添加 GET /data/list/<project_id>？
        // 或者如果元数据端点返回列表则重用它。
        // 检查 data.py... /metadata/<id> 返回单个数据集元数据。
        // 我们需要一种列出所有数据集的方法。
        fetchDatasetList()
    } catch (error) {
        // 暂无数据集
    }
}

/**
 * 获取该项目关联的所有历史数据集列表。
 */
const fetchDatasetList = async () => {
    try {
        const { data } = await api.get(`/projects/${route.params.id}`)
         // 项目响应通常包含数据集关联关系？
         // 检查 project.py 或者直接使用现有数据。
         // 实际上，让我们添加一个专用端点或者直接依赖项目详情。
         // 为了快速实现，尝试从项目详情中获取列表。
         datasetList.value = data.datasets || []
         
         // 如果存在活跃数据集，在列表中找到并设置？
         if(dataset.value && datasetList.value.length > 0){
             // 确保 dataset.value 与列表中的某项匹配
         }
    } catch (e) {
        console.error(e)
    }
}


/**
 * 将当前选中的数据集 ID 同步到服务器项目配置中，实现断点续作。
 */
const persistActiveDataset = async (dsId) => {
    if (!dsId) return
    try {
        await api.put(`/projects/${route.params.id}`, { active_dataset_id: dsId })
    } catch(e) {
        console.error("无法持久化活跃数据集状态", e)
    }
}

/**
 * 处理数据集全局更新事件。
 * 通常由子组件（如数据导入、特征工程）触发。
 */
const handleDatasetUpdate = (newDataset) => {
    dataset.value = newDataset
    persistActiveDataset(newDataset.dataset_id || newDataset.id)
    fetchDatasetList()
    // 逻辑：如果当前在“数据导入”页，则自动跳转到“数据体检”页。
    if (activeTabName.value === 'data') {
        activeTabName.value = 'preprocessing'
    }
}

const handleDatasetCreated = (newDatasetId) => {
    fetchProjectData()
    fetchDatasetList()
}

/**
 * 切换项目当前活跃的数据集，所有子组件将自动重载对应数据。
 */
const handleSwitchDataset = async (targetDataset) => {
    // 规范化数据集对象，确保 dataset_id 存在
    const normalized = {
        ...targetDataset,
        dataset_id: targetDataset.dataset_id || targetDataset.id
    }
    dataset.value = normalized
    await persistActiveDataset(normalized.dataset_id)
}

onMounted(() => {
    fetchProjectData()
})
</script>

<style scoped>
.project-container {
    height: calc(100vh - 60px); /* Adjust based on MainLayout header */
    background: #f5f7fa;
}

.project-sidebar {
    background: #fff;
    border-right: 1px solid #e6e6e6;
    overflow-y: auto;
}

.project-main {
    padding: 20px;
    overflow-y: auto;
}

.menu-group-title {
    padding: 15px 20px 5px;
    font-size: 12px;
    font-weight: bold;
    color: #909399;
}

.status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-left: auto;
}
.status-dot.green { background-color: #67C23A; }
.status-dot.red { background-color: #F56C6C; }
.status-dot.gray { background-color: #E4E7ED; }

.project-info-header {
    padding: 15px 20px;
    background: #f0f9eb;
    border-bottom: 1px solid #e1f3d8;
}
.info-label {
    font-size: 11px;
    color: #67C23A;
    margin-bottom: 4px;
    text-transform: uppercase;
    font-weight: bold;
}
.info-value {
    font-size: 13px;
    font-weight: 600;
    color: #2c3e50;
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.info-meta {
    font-size: 11px;
    color: #909399;
    margin-top: 4px;
}
</style>
