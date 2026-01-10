<template>
  <div>
    <div class="data-actions">
      <el-upload
        class="upload-demo"
        :action="uploadUrl"
        :headers="headers"
        :on-success="handleUploadFinish"
        :on-error="handleUploadError"
        :show-file-list="false"
      >
        <el-button type="primary">上传文件 (CSV/Excel)</el-button>
      </el-upload>
    </div>

    <el-alert
        title="数据管理指南"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 20px"
    >
        <template #default>
            <div style="font-size: 13px; color: #606266; line-height: 1.6;">
                <li><b>元数据</b>: 系统会自动识别变量类型（数值型、分类型）。若识别有误，可在“预处理”中修正。</li>
                <li><b>数据安全</b>: 您的文件仅保存在本地服务器。任何处理操作都会生成带有时间戳的新版本，原始版本永不丢失。</li>
            </div>
        </template>
    </el-alert>

    <el-card v-if="metadata" class="box-card" shadow="never" style="margin-top: 20px">
         <template #header>
            <div class="card-header">
                <span>数据集元数据 ({{ metadata.row_count }} 行)</span>
                <el-button type="primary" size="small" icon="Download" @click="handleDownload" v-if="dataset">下载 CSV</el-button>
            </div>
         </template>
         <el-table :data="metadata.variables" style="width: 100%" stripe border>
            <el-table-column prop="name" label="变量名" />
            <el-table-column prop="type" label="类型">
                <template #default="scope">
                    <el-tag :type="scope.row.type === 'numerical' ? 'success' : 'warning'">{{ scope.row.type === 'numerical' ? '数值型' : (scope.row.type === 'categorical' ? '分类变量' : '文本') }}</el-tag>
                </template>
            </el-table-column>
            <el-table-column prop="role" label="角色"/>
            <el-table-column prop="missing_count" label="缺失值" />
            <el-table-column prop="unique_count" label="唯一值" />
         </el-table>
    </el-card>
    
    <el-empty v-else description="暂无数据，请先上传文件" style="margin-top: 50px" />
  </div>
</template>

<script setup>
/**
 * DataTab.vue
 * 数据导入与元数据预览组件。
 * 
 * 职责：
 * 1. 提供数据集上传接口。
 * 2. 展示初步解析后的变量元数据（变量名、由于后端推断的类型、缺失值统计等）。
 */
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const props = defineProps({
    projectId: { type: String, required: true },
    dataset: { type: Object, default: null }
})
const emit = defineEmits(['dataset-updated'])

const metadata = ref(null)

watch(() => props.dataset, (newVal) => {
    if (newVal && newVal.metadata) {
        metadata.value = newVal.metadata
    }
}, { immediate: true })

const uploadUrl = computed(() => `/api/data/upload/${props.projectId}`)
const headers = computed(() => ({
    Authorization: `Bearer ${localStorage.getItem('token')}`
}))

const handleUploadFinish = (response) => {
    ElMessage.success('上传成功')
    metadata.value = response.metadata
    emit('dataset-updated', { 
        dataset_id: response.dataset_id, 
        metadata: response.metadata 
    })
}

const handleUploadError = () => {
    ElMessage.error('上传失败')
}

const handleDownload = () => {
    if (!props.dataset) return
    const dsId = props.dataset.dataset_id || props.dataset.id
    
    api.get(`/data/download/dataset/${dsId}`, { responseType: 'blob' })
    .then((response) => {
        const href = URL.createObjectURL(response.data);
        const link = document.createElement('a');
        link.href = href;
        
        // Try to get filename
        let filename = props.dataset.name || 'dataset.csv';
        if (!filename.toLowerCase().endsWith('.csv')) filename += '.csv'

        link.setAttribute('download', filename); 
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(href);
    })
    .catch(e => {
        ElMessage.error("下载失败")
        console.error(e)
    })
}
</script>

<style scoped>
.data-actions {
    margin-bottom: 20px;
}
</style>
