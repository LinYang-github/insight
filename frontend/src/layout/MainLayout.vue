<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="aside-menu">
      <div class="logo-area">
        <el-icon :size="24" color="#409EFF" style="margin-right: 8px"><Platform /></el-icon>
        <h3>Insight 平台</h3>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        background-color="transparent"
        text-color="#303133"
        active-text-color="#409EFF"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>首页仪表盘</span>
        </el-menu-item>
        
        <el-sub-menu index="projects">
          <template #title>
            <el-icon><Folder /></el-icon>
            <span>项目管理</span>
          </template>
           <el-menu-item index="/projects/list">
             <el-icon><List /></el-icon>
             <span>我的项目</span>
           </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/settings" disabled>
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
           <h3 style="margin:0">{{ headerTitle }}</h3>
        </div>
        <div class="header-right">
          <div class="user-info" v-if="userStore.user">
             <el-dropdown trigger="click" @command="handleCommand">
                <span class="el-dropdown-link">
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
.aside-menu {
  background-color: #fff;
  border-right: 1px solid #e6e6e6;
  display: flex; flex-direction: column;
}
.logo-area {
  height: 60px; display: flex; align-items: center; justify-content: center;
  border-bottom: 1px solid #e6e6e6;
  color: #303133;
}
.layout-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex; justify-content: space-between; align-items: center; height: 60px;
  padding: 0 20px;
}
.layout-main { 
    background-color: #f5f7fa; 
    padding: 20px; 
}
.el-dropdown-link {
  cursor: pointer;
  display: flex;
  align-items: center;
  color: #409EFF;
}
</style>
