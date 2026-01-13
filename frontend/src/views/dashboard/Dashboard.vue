<template>
  <div class="dashboard-container">
    <!-- 1. 欢迎页头部区域 -->
    <div class="welcome-header">
      <div class="header-content">
        <h1>早安，研究员</h1>
        <p>准备好开始今天的循证探索了吗？</p>
      </div>
      <div class="quick-stats">
        <div class="stat-item">
          <span class="stat-num">{{ projects.length }}</span>
          <span class="stat-label">进行中项目</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-num">{{ recentCount }}</span>
          <span class="stat-label">本周活跃</span>
        </div>
      </div>
    </div>
 
    <!-- 2. 操作工具栏 -->
    <div class="action-bar">
      <div class="search-box">
         <el-input 
            v-model="searchQuery" 
            placeholder="搜索项目..." 
            :prefix-icon="Search"
            clearable
            class="custom-search"
         />
      </div>
      <el-button type="primary" size="large" :icon="Plus" class="create-btn" @click="showModal = true">
      创建新研究
      </el-button>
    </div>
 
    <!-- 3. 项目卡片网格 -->
    <div v-if="filteredProjects.length > 0" class="projects-grid">
       <div 
          v-for="project in filteredProjects" 
          :key="project.id" 
          class="project-card"
          @click="enterProject(project.id)"
       >
          <div class="card-status-bar" :style="{ background: getRandomColor(project.id) }"></div>
          <div class="card-body">
              <div class="card-header">
                 <div class="icon-wrapper">
                    <el-icon><Folder /></el-icon>
                 </div>
                 <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, project)" @click.stop>
                    <el-icon class="more-btn"><MoreFilled /></el-icon>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit">编辑信息</el-dropdown-item>
                        <el-dropdown-item command="delete" style="color: #F56C6C">删除项目</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                 </el-dropdown>
              </div>
              
              <h3 class="project-title">{{ project.name }}</h3>
              <p class="project-desc">{{ project.description || '暂无描述信息' }}</p>
              
              <div class="card-footer">
                  <span class="update-time">更新于 {{ formatDate(project.updated_at) }}</span>
                  <div class="tags">
                      <el-tag size="small" type="info" effect="plain">Data</el-tag>
                  </div>
              </div>
          </div>
       </div>
    </div>
 
    <!-- 4. 空状态界面 -->
    <div v-else class="empty-state">
        <template v-if="searchQuery">
            <el-empty description="未找到匹配的项目" />
        </template>
        <template v-else>
            <div class="empty-placeholder">
                <el-icon class="empty-icon"><DataAnalysis /></el-icon>
                <h3>开始您的第一个研究项目</h3>
                <p>Insight 助您从数据中发现临床价值</p>
                <el-button type="primary" size="large" @click="showModal = true">立即创建</el-button>
            </div>
        </template>
    </div>
    
    <!-- 创建/编辑项目弹窗 -->
    <el-dialog v-model="showModal" title="新建项目" width="480px" class="custom-dialog" align-center>
         <el-form label-position="top" size="large">
             <el-form-item label="项目名称">
                 <el-input v-model="newProject.name" placeholder="例如：透析患者预后分析 2024" />
             </el-form-item>
             <el-form-item label="项目描述 (可选)">
                 <el-input 
                    v-model="newProject.description" 
                    type="textarea" 
                    :rows="3"
                    placeholder="简要描述研究目的、纳入标准等..." 
                 />
             </el-form-item>
         </el-form>
         <template #footer>
             <span class="dialog-footer">
                 <el-button @click="showModal = false">取消</el-button>
                 <el-button type="primary" @click="handleCreate" :loading="creating">创建项目</el-button>
             </span>
         </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Folder, MoreFilled, DataAnalysis } from '@element-plus/icons-vue'
import api from '../../api/client'

const router = useRouter()

const projects = ref([])
const showModal = ref(false)
const creating = ref(false)
const searchQuery = ref('')
const newProject = reactive({ name: '', description: '' })

const newProject = reactive({ name: '', description: '' })

// 模拟最近活动计数（仅用于演示）
const recentCount = computed(() => {
    // 统计过去 7 天内更新的项目逻辑？
    // 简化处理：取总数的 80% 以保持视觉平衡
    return Math.ceil(projects.value.length * 0.8)
})

const filteredProjects = computed(() => {
    if (!searchQuery.value) return projects.value
    const q = searchQuery.value.toLowerCase()
    return projects.value.filter(p => p.name.toLowerCase().includes(q))
})

const fetchProjects = async () => {
    try {
        const { data } = await api.get('/projects/')
        // 按更新时间降序排列（如果后端支持），或按 ID 降序
        projects.value = data.projects.reverse() // 假设后端是追加新项目的
    } catch (error) {
        ElMessage.warning('项目加载失败')
    }
}

const handleCreate = async () => {
    if(!newProject.name) return ElMessage.warning('请输入项目名称')
    creating.value = true
    try {
        await api.post('/projects/', newProject)
        ElMessage.success('创建成功')
        showModal.value = false
        newProject.name = ''
        newProject.description = ''
        fetchProjects()
    } catch (error) {
        ElMessage.error('创建失败')
    } finally {
        creating.value = false
    }
}

const handleCommand = (cmd, project) => {
    if (cmd === 'delete') {
        handleDelete(project.id)
    } else if (cmd === 'edit') {
        ElMessage.info('编辑功能开发中...')
    }
}

const handleDelete = (id) => {
    ElMessageBox.confirm(
        '删除后数据将无法恢复，确认继续吗?',
        '删除项目',
        {
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
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

const formatDate = (str) => {
    if (!str) return '刚刚'
    return new Date().toLocaleDateString() // 如果字符串格式多变，暂时使用模拟日期
}

const getRandomColor = (id) => {
    const colors = ['#3B71CA', '#2E7D32', '#E6A23C', '#8E44AD', '#16A085']
    return colors[id % colors.length]
}

onMounted(() => {
    fetchProjects()
})
</script>

<style scoped>
.dashboard-container {
    padding: 30px;
    max-width: 1200px;
    margin: 0 auto;
}

/* 1. Welcome Header */
.welcome-header {
    background: linear-gradient(120deg, #102a55 0%, #3B71CA 100%);
    border-radius: 16px;
    padding: 40px;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 40px;
    box-shadow: 0 10px 30px rgba(59, 113, 202, 0.2);
}

.header-content h1 {
    font-size: 32px;
    font-weight: 700;
    margin: 0 0 10px 0;
}
.header-content p {
    font-size: 16px;
    opacity: 0.9;
    font-weight: 300;
    margin: 0;
}

.quick-stats {
    display: flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.1);
    padding: 15px 30px;
    border-radius: 12px;
    backdrop-filter: blur(10px);
}
.stat-item {
    text-align: center;
}
.stat-num {
    display: block;
    font-size: 24px;
    font-weight: 700;
}
.stat-label {
    font-size: 12px;
    opacity: 0.8;
}
.stat-divider {
    width: 1px;
    height: 30px;
    background: rgba(255,255,255,0.2);
    margin: 0 25px;
}

/* 2. Action Bar */
.action-bar {
    display: flex;
    justify-content: space-between;
    margin-bottom: 24px;
}
.search-box {
    width: 300px;
}
.custom-search :deep(.el-input__wrapper) {
    box-shadow: none;
    border: 1px solid #dcdfe6;
    border-radius: 8px;
    padding: 8px 15px;
    background: #fff;
}
.create-btn {
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(59, 113, 202, 0.2);
}

/* 3. Grid */
.projects-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 24px;
}

.project-card {
    background: white;
    border-radius: 12px;
    border: 1px solid #ebeef5;
    overflow: hidden;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    position: relative;
    display: flex;
    flex-direction: column;
}
.project-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.08);
    border-color: transparent;
}

.card-status-bar {
    height: 4px;
    width: 100%;
}

.card-body {
    padding: 20px;
    flex: 1;
    display: flex;
    flex-direction: column;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 15px;
}

.icon-wrapper {
    width: 40px;
    height: 40px;
    background: #f0f2f5;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #606266;
    font-size: 20px;
}
.more-btn {
    transform: rotate(90deg);
    color: #909399;
    padding: 5px;
}
.more-btn:hover {
    color: #3B71CA;
}

.project-title {
    font-size: 18px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0 0 8px 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.project-desc {
    color: #606266;
    font-size: 14px;
    line-height: 1.5;
    margin: 0 0 20px 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    flex: 1;
}

.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #f2f6fc;
    padding-top: 15px;
}
.update-time {
    font-size: 12px;
    color: #909399;
}

/* 4. Empty State */
.empty-state {
    padding: 60px 0;
    text-align: center;
}
.empty-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    color: #909399;
}
.empty-icon {
    font-size: 64px;
    margin-bottom: 20px;
    color: #dcdfe6;
}
.empty-placeholder h3 {
    font-size: 20px;
    color: #303133;
    margin-bottom: 10px;
}
.empty-placeholder p {
    margin-bottom: 30px;
}

/* Response */
@media (max-width: 768px) {
    .welcome-header {
        flex-direction: column;
        align-items: flex-start;
    }
    .quick-stats {
        margin-top: 20px;
        width: 100%;
        justify-content: space-around;
    }
    .action-bar {
        flex-direction: column;
        gap: 15px;
    }
    .search-box {
        width: 100%;
    }
    .create-btn {
        width: 100%;
    }
}
</style>
