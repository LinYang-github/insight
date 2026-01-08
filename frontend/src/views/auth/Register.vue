<template>
  <div class="auth-container">
    <el-card class="auth-card" shadow="hover">
      <template #header>
        <div class="auth-header">
          <h3>Insight 注册</h3>
        </div>
      </template>
      <el-form ref="formRef" :model="formValue" :rules="rules" label-position="top">
         <el-form-item label="用户名" prop="username">
          <el-input v-model="formValue.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formValue.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="formValue.password" type="password" placeholder="设置密码" show-password />
        </el-form-item>
        <el-button type="primary" class="auth-button" @click="handleRegister" :loading="loading">
          注册
        </el-button>
        <div class="auth-footer">
            <router-link to="/login">返回登录</router-link>
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
  email: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleRegister = async () => {
    if (!formRef.value) return
    await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.register(formValue.username, formValue.email, formValue.password)
        ElMessage.success('注册成功！请登录。')
        router.push('/login')
      } catch (error) {
        ElMessage.error(error.response?.data?.message || '注册失败')
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
