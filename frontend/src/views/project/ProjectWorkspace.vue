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
                {{ dataset.metadata.row_count }} Rows • {{ dataset.metadata.variables?.length }} Vars
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
                <!-- TODO: Check missing values for status -->
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
         <!-- Dynamic Component Cache could be used here if we want to keep state -->
         <!-- Using v-if/v-show or simple div mapping -->
         <div v-if="activeTabName === 'data'">
             <DataTab :projectId="route.params.id" :dataset="dataset" @dataset-updated="handleDatasetUpdate" />
         </div>
         <div v-else-if="activeTabName === 'data-mgmt'">
             <DataManagementTab 
                :datasets="datasetList"
                :activeDatasetId="dataset?.id"
                @dataset-switched="handleSwitchDataset" 
                @refresh-list="fetchDatasetList"
             />
         </div>
         <div v-else-if="activeTabName === 'preprocessing'">
             <PreprocessingTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" @dataset-created="handleDatasetCreated" />
         </div>
         <div v-else-if="activeTabName === 'clinical'">
             <ClinicalTab :dataset="dataset" :metadata="dataset?.metadata" @dataset-updated="handleDatasetUpdate" />
         </div>
         <div v-else-if="activeTabName === 'table1'">
             <TableOneTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
         </div>
         <div v-else-if="activeTabName === 'eda'">
             <EdaTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
         </div>
         <div v-else-if="activeTabName === 'survival'">
             <SurvivalTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
         </div>
         <div v-else-if="activeTabName === 'psm'">
             <PsmTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" @dataset-created="handleDatasetCreated" />
         </div>
         <div v-else-if="activeTabName === 'modeling'">
              <ModelingTab :projectId="route.params.id" :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
         </div>
         <div v-else-if="activeTabName === 'advanced'">
             <AdvancedModelingTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
         </div>
         <div v-else-if="activeTabName === 'viz'">
             <ClinicalVizTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
         </div>
         <div v-else-if="activeTabName === 'longitudinal'">
             <LongitudinalTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
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
import api from '../../api/client'

import { Upload, Brush, DataLine, TrendCharts, List, Timer, Connection, FirstAidKit, FolderOpened, Histogram, Cpu, Document, Odometer } from '@element-plus/icons-vue'

const route = useRoute()
const dataset = ref(null)
const datasetList = ref([]) // All datasets for list
const activeTabName = ref('data')

const handleTabChange = (name) => {
    // Logic if needed
}

const fetchProjectData = async () => {
    try {
        const { data } = await api.get(`/data/metadata/${route.params.id}`)
        dataset.value = data
        // Also fetch all datasets for management? 
        // Currently metadata endpoint returns "latest".
        // We probably need a LIST endpoint.
        // For now, let's assume metadata endpoint is extended OR we add a list endpoint.
        // Wait, current design is: 1 project = N datasets.
        // Let's add GET /data/list/<project_id> later?
        // Or reuse metadata endpoint if it returns list.
        // Checking data.py... /metadata/<id> returns single Dataset metadata.
        // We need a way to list ALL datasets. 
        fetchDatasetList()
    } catch (error) {
        // No dataset yet
    }
}

const fetchDatasetList = async () => {
    try {
        const { data } = await api.get(`/projects/${route.params.id}`)
         // Project response usually includes datasets relationship?
         // Let's check project.py or just use what we have.
         // Actually, let's add a specialized endpoint or just rely on Project details.
         // For expediency, let's try to get list from project detail.
         datasetList.value = data.datasets || []
         
         // Find active one if exists and set it?
         if(dataset.value && datasetList.value.length > 0){
             // ensure dataset.value matches one in list
         }
    } catch (e) {
        console.error(e)
    }
}


const persistActiveDataset = async (dsId) => {
    if (!dsId) return
    try {
        await api.put(`/projects/${route.params.id}`, { active_dataset_id: dsId })
    } catch(e) {
        console.error("Failed to persist active dataset", e)
    }
}

const handleDatasetUpdate = (newDataset) => {
    dataset.value = newDataset
    persistActiveDataset(newDataset.dataset_id || newDataset.id)
    fetchDatasetList()
    // Auto advance locally, or stay? Usually stay if clinical tool.
    // But original code advanced to preprocessing?
    // Only if it's import? 
    // Logic: If activeTab is 'data', move to 'preprocessing'. 
    // If 'clinical', stay in 'clinical'.
    if (activeTabName.value === 'data') {
        activeTabName.value = 'preprocessing'
    }
}

const handleDatasetCreated = (newDatasetId) => {
    fetchProjectData()
    fetchDatasetList()
}

const handleSwitchDataset = async (targetDataset) => {
    dataset.value = targetDataset
    await persistActiveDataset(targetDataset.id || targetDataset.dataset_id)
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
