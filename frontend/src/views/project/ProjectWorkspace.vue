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

onMounted(() => {
    fetchProjectData()
})
</script>

<style scoped>
.project-wrapper {
    /* Padding handled by MainLayout */
}
</style>
