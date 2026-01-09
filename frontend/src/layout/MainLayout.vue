<template>
  <el-container class="layout-container" direction="vertical">
      <el-header class="layout-header">
        <div class="header-left">
           <div class="logo-area">
              <el-icon :size="24" color="#409EFF" style="margin-right: 8px"><Platform /></el-icon>
              <h3>Insight 平台</h3>
           </div>
           
           <el-menu
            :default-active="activeMenu"
            mode="horizontal"
            class="top-menu"
            router
            background-color="transparent"
            text-color="#303133"
            active-text-color="#409EFF"
            :ellipsis="false" 
           >
             <el-menu-item index="/dashboard">
                <el-icon><Odometer /></el-icon> 首页
             </el-menu-item>
             <el-menu-item index="/projects/list">
                <el-icon><Folder /></el-icon> 项目列表
             </el-menu-item>
             <el-menu-item index="/settings" disabled>
                <el-icon><Setting /></el-icon> 系统设置
             </el-menu-item>
           </el-menu>
        </div>

        <div class="header-right">
           <!-- Project Title Context could go here if needed, but we have breadcrumbs usually -->
           <!-- For now kept simple -->
           
          <div class="user-info" v-if="userStore.user">
             <el-dropdown trigger="click" @command="handleCommand">
                <span class="el-dropdown-link">
                  <el-avatar :size="32" style="margin-right: 8px">{{ userStore.user.username[0].toUpperCase() }}</el-avatar>
                  {{ userStore.user.username }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
          </div>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { Platform, Odometer, Folder, List, Setting, ArrowDown } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => {
    // map route path to menu index
    if (route.path.startsWith('/project/')) return '/projects/list' // keep 'All Projects' active for workspace
    return route.path
})

const headerTitle = computed(() => {
    if (route.name === 'Dashboard') return '项目仪表盘'
    if (route.name === 'ProjectWorkspace') return '项目工作台'
    return 'Insight 平台'
})

const handleCommand = (command) => {
    if (command === 'logout') {
        userStore.logout()
    }
}
</script>

<style scoped>
.layout-container { height: 100vh; }

.layout-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex; justify-content: space-between; align-items: center; 
  height: 60px;
  padding: 0 20px;
}

.header-left {
    display: flex;
    align-items: center;
    height: 100%;
}

.logo-area {
    display: flex; align-items: center;
    margin-right: 40px;
    cursor: pointer;
}

.top-menu {
    border-bottom: none !important;
    height: 60px;
    min-width: 400px;
}

.layout-main { 
    background-color: #f5f7fa; 
    padding: 0; /* Let child components handle padding, e.g. ProjectWorkspace needs full height */
    /* Check if Dashboard needs padding? Yes. */
    overflow: hidden; /* ProjectWorkspace handles scrolling */
}

/* Fix for children that need padding */
:deep(.dashboard-container) {
    padding: 20px;
    overflow-y: auto;
    height: 100%;
}
/* Project List also needs padding */
:deep(.project-list-container) {
    padding: 20px;
    overflow-y: auto;
    height: 100%;
}

.el-dropdown-link {
  cursor: pointer;
  display: flex;
  align-items: center;
  color: #606266;
}
</style>
