<template>
  <el-container class="project-container">
    <el-aside width="240px" class="project-sidebar">
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
            <el-menu-item index="preprocessing" :disabled="!dataset">
                <el-icon><Brush /></el-icon>
                <span>数据体检 (Health Check)</span>
                <!-- TODO: Check missing values for status -->
                <span class="status-dot green"></span> 
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
        </el-menu>
    </el-aside>

    <el-main class="project-main">
         <!-- Dynamic Component Cache could be used here if we want to keep state -->
         <!-- Using v-if/v-show or simple div mapping -->
         <div v-if="activeTabName === 'data'">
             <DataTab :projectId="route.params.id" :dataset="dataset" @dataset-updated="handleDatasetUpdate" />
         </div>
         <div v-else-if="activeTabName === 'preprocessing'">
             <PreprocessingTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" @dataset-created="handleDatasetCreated" />
         </div>
         <div v-else-if="activeTabName === 'eda'">
             <EdaTab :datasetId="dataset?.dataset_id" />
         </div>
         <div v-else-if="activeTabName === 'table1'">
             <TableOneTab :datasetId="dataset?.dataset_id" :metadata="dataset?.metadata" />
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
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import DataTab from './components/DataTab.vue'
import ModelingTab from './components/ModelingTab.vue'
import EdaTab from './components/EdaTab.vue'
import PreprocessingTab from './components/PreprocessingTab.vue'
import TableOneTab from './components/TableOneTab.vue'
import SurvivalTab from './components/SurvivalTab.vue'
import PsmTab from './components/PsmTab.vue'
import api from '../../api/client'

import { Upload, Brush, DataLine, TrendCharts, List, Timer, Connection } from '@element-plus/icons-vue'

const route = useRoute()
const dataset = ref(null)
const activeTabName = ref('data')

const handleTabChange = (name) => {
    // Logic if needed
}

const fetchProjectData = async () => {
    try {
        const { data } = await api.get(`/data/metadata/${route.params.id}`)
        dataset.value = data
    } catch (error) {
        // No dataset yet
    }
}

const handleDatasetUpdate = (newDataset) => {
    dataset.value = newDataset
    // Auto advance to cleaning
    activeTabName.value = 'preprocessing'
}

const handleDatasetCreated = (newDatasetId) => {
    fetchProjectData().then(() => {
         // Maybe stay on same tab or show success? 
         // User requested flow: "After preprocessing -> Go to Modeling"
         // But preprocessing emits this.
         // Let's keep existing logic or update to stay.
         // Actually user wants "Smart Fix" then go to Modeling.
         // For now, let's just refresh data.
    })
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
</style>
