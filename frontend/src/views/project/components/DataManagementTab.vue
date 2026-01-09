<template>
  <div class="data-management-tab">
     <el-card shadow="never" class="dataset-card">
         <template #header>
            <div class="card-header">
                <span>📁 数据集管理 (Dataset Management)</span>
            </div>
         </template>

         <el-table :data="sortedDatasets" stripe style="width: 100%" v-loading="loading">
             <!-- Status -->
             <el-table-column width="60" align="center">
                 <template #default="{ row }">
                     <el-icon v-if="row.id === activeDatasetId" color="#67C23A" size="18"><CircleCheckFilled /></el-icon>
                     <el-tooltip content="这是当前活跃的数据集" placement="top" v-if="row.id === activeDatasetId">
                        <span style="display:none">Active</span>
                     </el-tooltip>
                 </template>
             </el-table-column>

             <el-table-column prop="name" label="文件名 (Name)" min-width="250">
                 <template #default="{ row }">
                     <span class="dataset-name">{{ row.name }}</span>
                 </template>
             </el-table-column>

             <el-table-column prop="created_at" label="创建时间 (Created At)" width="180">
                 <template #default="{ row }">
                     {{ formatDate(row.created_at) }}
                 </template>
             </el-table-column>
             
             <!-- Need file size or row count if available in metadata? -->
             <el-table-column label="详情 (Details)" width="150">
                 <template #default="{ row }">
                     <span v-if="row.meta_data && row.meta_data.row_count" class="meta-tag">
                        {{ row.meta_data.row_count }} 行
                     </span>
                      <span v-if="row.meta_data && row.meta_data.variables" class="meta-tag">
                        {{ row.meta_data.variables.length }} 变量
                     </span>
                 </template>
             </el-table-column>

             <el-table-column label="操作 (Actions)" width="200" align="right">
                 <template #default="{ row }">
                     <el-button-group>
                         <el-button size="small" @click="handleSetActive(row)" :disabled="row.id === activeDatasetId" :type="row.id === activeDatasetId ? 'success' : ''">
                             {{ row.id === activeDatasetId ? '活跃' : '启用' }}
                         </el-button>
                         <el-button size="small" icon="Edit" @click="openRename(row)" />
                         <el-button size="small" type="danger" icon="Delete" @click="confirmDelete(row)" />
                     </el-button-group>
                 </template>
             </el-table-column>
         </el-table>
     </el-card>

     <!-- Rename Dialog -->
     <el-dialog v-model="renameDialogVisible" title="重命名数据集" width="30%">
         <el-form label-position="top">
             <el-form-item label="新名称">
                 <el-input v-model="renameForm.newName" placeholder="请输入文件名 (包含后缀)" />
             </el-form-item>
         </el-form>
         <template #footer>
             <span class="dialog-footer">
                 <el-button @click="renameDialogVisible = false">取消</el-button>
                 <el-button type="primary" @click="handleRename" :loading="renaming">确定</el-button>
             </span>
         </template>
     </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, Edit, Delete } from '@element-plus/icons-vue'
import api from '../../../api/client'
import dayjs from 'dayjs'

const props = defineProps({
    datasets: {
        type: Array,
        default: () => []
    },
    activeDatasetId: {
        type: Number,
        default: null
    }
})

const emit = defineEmits(['dataset-switched', 'refresh-list'])

const loading = ref(false)
const renameDialogVisible = ref(false)
const renaming = ref(false)
const renameForm = ref({
    id: null,
    newName: ''
})

const sortedDatasets = computed(() => {
    // Sort by created_at desc
    return [...props.datasets].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
})

const formatDate = (dateStr) => {
    return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

const handleSetActive = (dataset) => {
    emit('dataset-switched', dataset)
    ElMessage.success(`已切换至: ${dataset.name}`)
}

// Rename Logic
const openRename = (dataset) => {
    renameForm.value.id = dataset.id
    renameForm.value.newName = dataset.name
    renameDialogVisible.value = true
}

const handleRename = async () => {
    renaming.value = true
    try {
        await api.put(`/data/${renameForm.value.id}/rename`, {
            name: renameForm.value.newName
        })
        ElMessage.success('重命名成功')
        renameDialogVisible.value = false
        emit('refresh-list')
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '重命名失败')
    } finally {
        renaming.value = false
    }
}

// Delete Logic
const confirmDelete = (dataset) => {
    ElMessageBox.confirm(
        `确定要永久删除数据集 "${dataset.name}" 吗？此操作无法撤销。`,
        '警告',
        {
            confirmButtonText: '确定删除',
            cancelButtonText: '取消',
            type: 'warning',
        }
    ).then(async () => {
        try {
            await api.delete(`/data/${dataset.id}`)
            ElMessage.success('删除成功')
            emit('refresh-list')
            // If deleted active dataset, maybe switch to another?
            // Parent component handles refreshing, if active is gone, it handles fallback.
        } catch (e) {
            ElMessage.error(e.response?.data?.message || '删除失败')
        }
    }).catch(() => {})
}

</script>

<style scoped>
.data-management-tab {
    padding: 10px;
}
.dataset-name {
    font-weight: 500;
}
.meta-tag {
    display: inline-block;
    background-color: #f0f2f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
    color: #606266;
    margin-right: 5px;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
</style>
