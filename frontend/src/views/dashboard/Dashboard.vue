<template>
  <div class="dashboard-container">
    <div class="header-actions">
      <h2>我的项目</h2>
      <el-button type="primary" :icon="Plus" @click="showModal = true">新建项目</el-button>
    </div>

    <el-row :gutter="20">
       <el-col :span="8" v-for="project in projects" :key="project.id" style="margin-bottom: 20px;">
          <el-card shadow="hover" class="project-card">
             <template #header>
                 <div class="card-header">
                     <span>{{ project.name }}</span>
                     <el-button type="danger" link @click.stop="handleDelete(project.id)">删除</el-button>
                 </div>
             </template>
             <div class="card-content">
                {{ project.description || '暂无描述' }}
             </div>
             <div class="card-footer">
                <el-button type="primary" plain size="small" @click="enterProject(project.id)">打开项目</el-button>
             </div>
          </el-card>
       </el-col>
    </el-row>
    
    <el-dialog v-model="showModal" title="新建项目" width="500px">
         <el-form label-width="100px">
             <el-form-item label="项目名称">
                 <el-input v-model="newProject.name" placeholder="请输入项目名称" />
             </el-form-item>
             <el-form-item label="项目描述">
                 <el-input v-model="newProject.description" type="textarea" placeholder="请输入项目描述" />
             </el-form-item>
         </el-form>
         <template #footer>
             <span class="dialog-footer">
                 <el-button @click="showModal = false">取消</el-button>
                 <el-button type="primary" @click="handleCreate">创建</el-button>
             </span>
         </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../../api/client'

const router = useRouter()

const projects = ref([])
const showModal = ref(false)
const newProject = reactive({ name: '', description: '' })

const fetchProjects = async () => {
    try {
        const { data } = await api.get('/projects/')
        projects.value = data.projects
    } catch (error) {
        ElMessage.warning('项目加载失败')
    }
}

const handleCreate = async () => {
    if(!newProject.name) return ElMessage.warning('请输入项目名称')
    try {
        await api.post('/projects/', newProject)
        ElMessage.success('创建成功')
        showModal.value = false
        newProject.name = ''
        newProject.description = ''
        fetchProjects()
    } catch (error) {
        ElMessage.error('创建失败')
    }
}

const handleDelete = (id) => {
    ElMessageBox.confirm(
        '确任要删除该项目吗?',
        '警告',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        }
    ).then(async () => {
         try {
            await api.delete(`/projects/${id}`)
            ElMessage.success('删除成功')
            fetchProjects()
        } catch (error) {
            ElMessage.error('删除失败')
        }
    }).catch(() => {})
}

const enterProject = (id) => {
    router.push(`/project/${id}`)
}

onMounted(() => {
    fetchProjects()
})
</script>

<style scoped>
.dashboard-wrapper {
   
}
.header-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
.card-content {
    min-height: 40px;
    margin-bottom: 15px;
    color: #666;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.card-footer {
    display: flex;
    justify-content: flex-end;
}
</style>
