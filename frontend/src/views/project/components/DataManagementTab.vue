<template>
  <div class="data-management-tab">
     <el-card shadow="never" class="dataset-card">
         <template #header>
            <div class="card-header">
                <div class="header-left">
                    <span>📁 数据集管理 (Dataset Management)</span>
                </div>
                <div class="header-right">
                    <el-radio-group v-model="viewMode" size="small">
                        <el-radio-button label="list">
                            <el-icon><List /></el-icon> 列表 (List)
                        </el-radio-button>
                        <el-radio-button label="tree">
                            <el-icon><Connection /></el-icon> 血缘 (Lineage)
                        </el-radio-button>
                    </el-radio-group>
                </div>
            </div>
         </template>

         <!-- List View -->
         <div v-if="viewMode === 'list'">
             <el-table :data="sortedDatasets" stripe style="width: 100%" v-loading="loading">
                 <!-- Status -->
                 <el-table-column width="60" align="center">
                     <template #default="{ row }">
                         <el-icon v-if="row.id === activeDatasetId" color="#67C23A" size="18"><CircleCheckFilled /></el-icon>
                     </template>
                 </el-table-column>

                 <el-table-column prop="name" label="文件名 (Name)" min-width="250">
                     <template #default="{ row }">
                         <span class="dataset-name">{{ row.name }}</span>
                         <el-tag size="small" v-if="row.action_type" type="info" class="ml-2">{{ row.action_type }}</el-tag>
                     </template>
                 </el-table-column>

                 <el-table-column prop="created_at" label="创建时间 (Created At)" width="180">
                     <template #default="{ row }">
                         {{ formatDate(row.created_at) }}
                     </template>
                 </el-table-column>
                 
                 <el-table-column label="详情 (Details)" width="150">
                     <template #default="{ row }">
                         <span v-if="row.meta_data && row.meta_data.row_count" class="meta-tag">
                            {{ row.meta_data.row_count }} 行
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
                             <el-button size="small" icon="Download" @click="handleDownload(row)" />
                             <el-button size="small" type="danger" icon="Delete" @click="confirmDelete(row)" />
                         </el-button-group>
                     </template>
                 </el-table-column>
             </el-table>
         </div>

         <!-- Tree View (Lineage) -->
         <div v-else class="lineage-container">
            <el-empty v-if="lineageTreeData.length === 0" description="No Data" />
            <el-tree
                v-else
                :data="lineageTreeData"
                node-key="id"
                default-expand-all
                :expand-on-click-node="false"
            >
                <template #default="{ node, data }">
                    <div class="custom-tree-node" :class="{ 'is-active': data.original.id === activeDatasetId }">
                        <div class="node-main" @click="handleSetActive(data.original)">
                            <el-icon class="node-icon" :class="getActionIconClass(data.original.action_type)">
                                <component :is="getActionIcon(data.original.action_type)" />
                            </el-icon>
                            <span class="node-label">{{ data.label }}</span>
                            
                            <el-tag v-if="data.original.id === activeDatasetId" size="small" type="success" effect="dark" class="active-tag">Active</el-tag>
                            
                            <!-- Action Info Popover -->
                            <el-popover
                                v-if="data.original.action_log"
                                placement="top"
                                title="操作详情 (Operation Details)"
                                :width="300"
                                trigger="hover"
                            >
                                <template #reference>
                                    <el-tag size="small" effect="plain" type="info" class="action-tag">
                                        {{ data.original.action_type || 'Upload' }}
                                    </el-tag>
                                </template>
                                <div class="action-log-content">
                                    <pre>{{ formatActionLog(data.original.action_log) }}</pre>
                                </div>
                            </el-popover>
                        </div>
                        
                        <div class="node-actions">
                            <span class="time-text">{{ formatDate(data.original.created_at) }}</span>
                             <el-button link type="primary" icon="Edit" @click="openRename(data.original)" />
                             <el-button link type="danger" icon="Delete" @click="confirmDelete(data.original)" />
                        </div>
                    </div>
                </template>
            </el-tree>
         </div>

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
import { 
    CircleCheckFilled, Edit, Delete, List, Connection, 
    Document, MagicStick, Cpu, ScaleToOriginal, Download 
} from '@element-plus/icons-vue'
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
const viewMode = ref('list') // 'list' or 'tree'
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

// --- Lineage Tree Logic ---
const lineageTreeData = computed(() => {
    if (!props.datasets || props.datasets.length === 0) return []

    // 1. Create a map for easy lookup
    const datasetMap = {}
    props.datasets.forEach(ds => {
        datasetMap[ds.id] = {
            id: ds.id,
            label: ds.name,
            original: ds,
            children: []
        }
    })

    const roots = []

    // 2. Build Hierarchy
    props.datasets.forEach(ds => {
        const node = datasetMap[ds.id]
        if (ds.parent_id && datasetMap[ds.parent_id]) {
            // Has parent, add to parent's children
            datasetMap[ds.parent_id].children.push(node)
        } else {
            // No parent (or parent not in list), treat as root
            roots.push(node)
        }
    })

    // Sort roots by logic? Maybe oldest first for timeline?
    // Let's keep upload order (id asc)
    roots.sort((a, b) => a.id - b.id)
    
    return roots
})

const getActionIcon = (type) => {
    switch (type) {
        case 'impute': return MagicStick
        case 'encode': return Cpu
        case 'psm': return ScaleToOriginal
        default: return Document // 'upload' or unknown
    }
}

const getActionIconClass = (type) => {
    switch(type) {
        case 'impute': return 'icon-purple'
        case 'encode': return 'icon-orange'
        case 'psm': return 'icon-blue'
        default: return 'icon-gray'
    }
}

const formatActionLog = (logStr) => {
    try {
        if (!logStr) return ''
        const obj = JSON.parse(logStr)
        return JSON.stringify(obj, null, 2)
    } catch {
        return logStr
    }
}

const formatDate = (dateStr) => {
    return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

const handleSetActive = (dataset) => {
    if(dataset.id === props.activeDatasetId) return // Already active
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

// Download Logic
const handleDownload = (dataset) => {
    api.get(`/data/download/dataset/${dataset.id}`, { responseType: 'blob' })
    .then((response) => {
        // Create link
        const href = URL.createObjectURL(response.data);
        const link = document.createElement('a');
        link.href = href;
        
        // Extract filename from header or use dataset.name
        let filename = dataset.name;
        // Simple fallback
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

// Delete Logic
const confirmDelete = (dataset) => {
    ElMessageBox.confirm(
        `确定要永久删除数据集 "${dataset.name}" 吗？若该节点有子节点，子节点也会被级联删除。`,
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
.header-left {
    font-weight: bold;
    font-size: 16px;
}
.ml-2 { margin-left: 8px; }

/* Tree Styles */
.lineage-container {
    padding: 10px;
}
.custom-tree-node {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 14px;
    padding-right: 8px;
    /* transition: all 0.2s; */
}
.custom-tree-node.is-active .node-label {
    color: #67C23A;
    font-weight: bold;
}
.node-main {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
}
.node-icon {
    font-size: 16px;
}
.icon-purple { color: #8e44ad; }
.icon-orange { color: #e67e22; }
.icon-blue { color: #2980b9; }
.icon-gray { color: #95a5a6; }

.node-actions {
    display: flex;
    align-items: center;
    gap: 10px;
}
.time-text {
    font-size: 12px;
    color: #999;
}
.active-tag {
    margin-left: 5px;
}
.action-log-content {
    max-height: 200px;
    overflow-y: auto;
    font-size: 12px;
}
.action-tag {
    cursor: help;
}
</style>
