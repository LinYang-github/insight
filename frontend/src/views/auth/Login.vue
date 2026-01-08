<template>
  <div class="auth-container">
    <el-card class="auth-card" shadow="hover">
      <template #header>
        <div class="auth-header">
          <h3>Insight 登录</h3>
        </div>
      </template>
      <el-form ref="formRef" :model="formValue" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formValue.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="formValue.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-button type="primary" class="auth-button" @click="handleLogin" :loading="loading">
          登录
        </el-button>
        <div class="auth-footer">
            <router-link to="/register">注册新账号</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const formValue = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.login(formValue.username, formValue.password)
        ElMessage.success('登录成功')
        router.push('/dashboard')
      } catch (error) {
        ElMessage.error(error.response?.data?.message || '登录失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}
.auth-card {
  width: 400px;
}
.auth-header {
  text-align: center;
}
.auth-button {
    width: 100%;
}
.auth-footer {
    margin-top: 15px;
    text-align: center;
}
</style>
