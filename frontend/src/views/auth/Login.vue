<template>
  <div class="login-container">
    <div class="login-wrapper">
      <!-- Left Side: Brand Area -->
      <div class="brand-section">
        <div class="brand-content">
          <div class="logo-area">
            <div class="logo-icon">
              <!-- Simple CSS Logo Placeholder -->
              <div class="logo-circle"></div>
            </div>
            <h1 class="app-name">Insight</h1>
          </div>
          <p class="slogan">赋能临床科研<br>从数据挖掘到循证洞察</p>
          <div class="brand-decoration">
            <div class="circle c1"></div>
            <div class="circle c2"></div>
          </div>
        </div>
      </div>

      <!-- Right Side: Form Area -->
      <div class="form-section">
        <div class="form-content">
          <div class="welcome-text">
            <h2>欢迎回来</h2>
            <p class="subtitle">请登录您的账号以继续使用</p>
          </div>

          <el-form 
            ref="formRef" 
            :model="formValue" 
            :rules="rules" 
            class="login-form"
            size="large"
          >
            <el-form-item prop="username">
              <el-input 
                v-model="formValue.username" 
                placeholder="用户名 / 邮箱" 
                :prefix-icon="User" 
              />
            </el-form-item>
            
            <el-form-item prop="password">
              <el-input 
                v-model="formValue.password" 
                type="password" 
                placeholder="密码" 
                show-password 
                :prefix-icon="Lock"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="rememberMe">记住我</el-checkbox>
              <a href="#" class="forgot-pwd">忘记密码?</a>
            </div>

            <el-button 
              type="primary" 
              class="submit-btn" 
              @click="handleLogin" 
              :loading="loading"
            >
              登 录
            </el-button>

            <div class="register-link">
              还没有账号? <router-link to="/register">立即注册</router-link>
            </div>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const rememberMe = ref(false)
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
        ElMessage.success('登录成功，欢迎回来')
        router.push('/dashboard')
      } catch (error) {
        ElMessage.error(error.response?.data?.message || '登录失败，请检查账号密码')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f0f2f5;
  overflow: hidden;
}

.login-wrapper {
  width: 1000px;
  height: 600px;
  display: flex;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

/* --- Left Side --- */
.brand-section {
  flex: 0.45;
  background: linear-gradient(135deg, #102a55 0%, #3B71CA 100%);
  color: white;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 40px;
  overflow: hidden;
}

.brand-content {
  position: relative;
  z-index: 2;
}

.logo-area {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}

.logo-circle {
  width: 32px;
  height: 32px;
  background: white;
  border-radius: 50%;
  position: relative;
  margin-right: 12px;
}
.logo-circle::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  background: #3B71CA;
  border-radius: 50%;
  top: 8px;
  left: 8px;
}

.app-name {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 1px;
}

.slogan {
  font-size: 20px;
  line-height: 1.6;
  opacity: 0.9;
  font-weight: 300;
}

/* Decorative Circles */
.brand-decoration .circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  z-index: 1;
}
.c1 {
  width: 200px;
  height: 200px;
  top: -50px;
  left: -50px;
}
.c2 {
  width: 300px;
  height: 300px;
  bottom: -100px;
  right: -50px;
}

/* --- Right Side --- */
.form-section {
  flex: 0.55;
  padding: 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.form-content {
  max-width: 360px;
  margin: 0 auto;
  width: 100%;
}

.welcome-text {
  margin-bottom: 40px;
}
.welcome-text h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
}

.login-form :deep(.el-input__wrapper) {
  background-color: #f5f7fa;
  box-shadow: none !important;
  border: 1px solid transparent;
  transition: all 0.3s;
  padding-left: 15px;
}

.login-form :deep(.el-input__wrapper:hover),
.login-form :deep(.el-input__wrapper.is-focus) {
  background-color: #fff;
  border-color: #3B71CA;
  box-shadow: 0 0 0 1px #3B71CA !important;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.forgot-pwd {
  color: #3B71CA;
  font-size: 14px;
  text-decoration: none;
}
.forgot-pwd:hover {
  text-decoration: underline;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  border-radius: 8px;
  font-weight: 500;
  background: linear-gradient(90deg, #3B71CA 0%, #5084df 100%);
  border: none;
  transition: opacity 0.3s;
}
.submit-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 113, 202, 0.3);
}

.register-link {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: #606266;
}
.register-link a {
  color: #3B71CA;
  font-weight: 500;
  text-decoration: none;
  margin-left: 5px;
}
.register-link a:hover {
  text-decoration: underline;
}

/* Animations */
.login-wrapper {
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .login-wrapper {
    flex-direction: column;
    width: 90%;
    height: auto;
    min-height: 500px;
  }
  .brand-section {
    padding: 30px;
    flex: 0 0 120px;
  }
  .slogan, .brand-decoration {
    display: none;
  }
  .logo-area {
    margin-bottom: 0;
  }
  .form-section {
    padding: 40px;
  }
}
</style>
