<template>
  <div class="project-wrapper">
    <div class="steps-container">
        <el-steps :active="activeStep" finish-status="success" simple style="margin-bottom: 20px; cursor: pointer">
            <el-step title="上传数据" icon="Upload" @click="activeTabName = 'data'" />
            <el-step title="数据清洗" icon="Brush" @click="activeTabName = 'preprocessing'" />
            <el-step title="探索分析" icon="DataLine" @click="activeTabName = 'eda'" />
            <el-step title="统计描述" icon="List" @click="activeTabName = 'table1'" />
            <el-step title="生存分析" icon="Timer" @click="activeTabName = 'survival'" />
            <el-step title="倾向匹配" icon="Connection" @click="activeTabName = 'psm'" />
            <el-step title="统计建模" icon="TrendCharts" @click="activeTabName = 'modeling'" />
        </el-steps>
    </div>

     <el-tabs type="border-card" v-model="activeTabName" @tab-change="handleTabChange" class="wizard-tabs">
        <el-tab-pane label="数据管理" name="data">
            <DataTab 
                :projectId="route.params.id" 
                :dataset="dataset"
                @dataset-updated="handleDatasetUpdate"
            />
        </el-tab-pane>
        <el-tab-pane label="数据清洗 (Cleaning)" name="preprocessing">
            <PreprocessingTab 
                :datasetId="dataset?.dataset_id" 
                :metadata="dataset?.metadata"
                @dataset-created="handleDatasetCreated"
            />
        </el-tab-pane>
        <el-tab-pane label="数据探索 (EDA)" name="eda">
            <EdaTab :datasetId="dataset?.dataset_id" />
        </el-tab-pane>
        <el-tab-pane label="统计描述 (Table 1)" name="table1">
            <TableOneTab 
                :datasetId="dataset?.dataset_id"
                :metadata="dataset?.metadata"
            />
        </el-tab-pane>
        <el-tab-pane label="生存分析 (Survival)" name="survival">
            <SurvivalTab 
                :datasetId="dataset?.dataset_id"
                :metadata="dataset?.metadata"
            />
        </el-tab-pane>
        <el-tab-pane label="倾向性匹配 (PSM)" name="psm">
            <PsmTab 
                :datasetId="dataset?.dataset_id"
                :metadata="dataset?.metadata"
                @dataset-created="handleDatasetCreated"
            />
        </el-tab-pane>
        <el-tab-pane label="统计建模" name="modeling">
            <ModelingTab 
                :projectId="route.params.id"
                :datasetId="dataset?.dataset_id"
                :metadata="dataset?.metadata"
            />
        </el-tab-pane>
     </el-tabs>
  </div>
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

const activeStep = computed(() => {
    switch (activeTabName.value) {
        case 'data': return 0
        case 'preprocessing': return 1
        case 'eda': return 2
        case 'table1': return 3
        case 'survival': return 4
        case 'psm': return 5
        case 'modeling': return 6
        default: return 0
    }
})

const handleTabChange = (name) => {
    // Logic if needed
}

const fetchProjectData = async () => {
    try {
        const { data } = await api.get(`/data/metadata/${route.params.id}`)
        dataset.value = data
        // If we have data, maybe we want to be at least at preprocessing or eda?
        // But for consistency let's stay where we are or default to data.
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
         // Auto advance to EDA after cleaning
         activeTabName.value = 'eda'
    })
}

onMounted(() => {
    fetchProjectData()
})
</script>

<style scoped>
.project-wrapper {
    /* Padding handled by MainLayout */
}
:deep(.wizard-tabs .el-tabs__header) {
    display: none;
}
</style>
