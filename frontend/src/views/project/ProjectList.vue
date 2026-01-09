<template>
  <div class="project-list-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>我的项目 (My Projects)</span>
          <el-button type="primary" @click="router.push('/dashboard')">新建项目</el-button>
        </div>
      </template>

      <el-table :data="projects" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="项目名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
                {{ formatDate(scope.row.created_at) }}
            </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" type="primary" @click="enterProject(scope.row.id)">进入项目</el-button>
            <el-button size="small" type="danger" @click="deleteProject(scope.row.id)" text bg>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api/client'

const router = useRouter()
const projects = ref([])
const loading = ref(false)

const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
}

const fetchProjects = async () => {
    loading.value = true
    try {
        const { data } = await api.get('/projects/')
        projects.value = data.projects
    } catch (error) {
        ElMessage.error('获取项目列表失败')
    } finally {
        loading.value = false
    }
}

const enterProject = (id) => {
    router.push(`/project/${id}`)
}

const deleteProject = (id) => {
    ElMessageBox.confirm(
        '确定要删除该项目吗？此操作不可恢复。',
        '警告',
        {
            confirmButtonText: '删除',
            cancelButtonText: '取消',
            type: 'warning',
        }
    )
    .then(async () => {
        try {
            await api.delete(`/projects/${id}`)
            ElMessage.success('项目已删除')
            fetchProjects()
        } catch (error) {
            ElMessage.error('删除失败')
        }
    })
    .catch(() => {})
}

onMounted(() => {
    fetchProjects()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
