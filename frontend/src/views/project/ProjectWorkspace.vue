<template>
  <div class="project-wrapper">
     <el-tabs type="border-card">
        <el-tab-pane label="数据管理">
            <DataTab 
                :projectId="route.params.id" 
                :dataset="dataset"
                @dataset-updated="handleDatasetUpdate"
            />
        </el-tab-pane>
        <el-tab-pane label="数据探索 (EDA)">
            <EdaTab :datasetId="dataset?.dataset_id" />
        </el-tab-pane>
        <el-tab-pane label="数据清洗 (Cleaning)">
            <PreprocessingTab 
                :datasetId="dataset?.dataset_id" 
                :metadata="dataset?.metadata"
                @dataset-created="handleDatasetCreated"
            />
        </el-tab-pane>
        <el-tab-pane label="统计建模">
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
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import DataTab from './components/DataTab.vue'
import ModelingTab from './components/ModelingTab.vue'
import EdaTab from './components/EdaTab.vue'
import PreprocessingTab from './components/PreprocessingTab.vue'
import api from '../../api/client'

const route = useRoute()
const dataset = ref(null)

const fetchProjectData = async () => {
    try {
        const { data } = await api.get(`/data/metadata/${route.params.id}`)
        dataset.value = data
    } catch (error) {
        // No dataset yet, ignore
    }
}

const handleDatasetUpdate = (newDataset) => {
    dataset.value = newDataset
}

const handleDatasetCreated = (newDatasetId) => {
    // Refresh to switch to new dataset, or just notify user.
    // Ideally we reload project data. 
    // For MVP, we might need to emit up or just re-fetch if dataset is just a prop.
    // The dataset prop comes from fetchProjectData. So calling it again refreshes.
    // But fetchProjectData gets the *active* or *latest* dataset? 
    // Currently backend get_metadata returns the Project's "primary" dataset or list?
    // Let's check fetchProjectData logic.
    fetchProjectData()
}

onMounted(() => {
    fetchProjectData()
})
</script>

<style scoped>
.project-wrapper {
    /* Padding handled by MainLayout */
}
</style>
