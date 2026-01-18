<template>
    <div class="settings-container">
        <el-card>
            <template #header>
                <div class="card-header">
                    <h2>⚙️ 系统设置 (Settings)</h2>
                </div>
            </template>
            
            <el-tabs v-model="activeTab" class="settings-tabs">
                <!-- 1. General Tab -->
                <el-tab-pane label="通用 (General)" name="general">
                    <el-form label-position="left" label-width="200px">
                        <el-form-item label="通过主题 (Theme)">
                            <el-switch
                                v-model="settings.theme"
                                active-value="dark"
                                inactive-value="light"
                                active-text="深色模式 (Dark)"
                                inactive-text="浅色模式 (Light)"
                                @change="val => userStore.applyTheme(val)"
                            />
                            <div class="form-helper">主题切换功能敬请期待 (Coming Soon)。</div>
                        </el-form-item>
                    </el-form>
                </el-tab-pane>

                <!-- 2. Statistics Tab -->
                <el-tab-pane label="统计偏好 (Statistics)" name="statistics">
                    <el-form label-position="left" label-width="200px">
                         <el-alert
                            title="应用范围说明"
                            type="info"
                            :closable="false"
                            show-icon
                            style="margin-bottom: 20px"
                        >
                            此设置将应用于所有新生成的统计报表（如 Table 1, 回归分析结果）。
                        </el-alert>
                        
                        <el-form-item label="显著性水平 (P-value Threshold)">
                            <el-select v-model="settings.p_value" placeholder="Select">
                                <el-option label="P < 0.05 (Standard)" :value="0.05" />
                                <el-option label="P < 0.01 (Strict)" :value="0.01" />
                            </el-select>
                        </el-form-item>

                        <el-form-item label="保留小数位 (Decimal Places)">
                            <el-input-number v-model="settings.digits" :min="1" :max="5" />
                        </el-form-item>
                        
                        <el-form-item>
                            <el-button type="primary" @click="saveSettings" :loading="saving">保存偏好 (Save Preferences)</el-button>
                        </el-form-item>
                    </el-form>
                </el-tab-pane>

                <!-- 3. Account Tab -->
                <el-tab-pane label="账户安全 (Account)" name="account">
                    <el-form 
                        ref="pwdFormRef"
                        :model="pwdForm"
                        :rules="pwdRules"
                        label-position="top"
                        style="max-width: 400px"
                    >
                        <el-form-item label="当前密码 (Current Password)" prop="current_password">
                            <el-input v-model="pwdForm.current_password" type="password" show-password />
                        </el-form-item>
                        
                        <el-form-item label="新密码 (New Password)" prop="new_password">
                            <el-input v-model="pwdForm.new_password" type="password" show-password />
                        </el-form-item>
                        
                        <el-form-item label="确认新密码 (Confirm)" prop="confirm_password">
                            <el-input v-model="pwdForm.confirm_password" type="password" show-password />
                        </el-form-item>
                        
                         <el-form-item>
                            <el-button type="danger" @click="changePassword" :loading="changingPwd">修改密码 (Change Password)</el-button>
                        </el-form-item>
                    </el-form>
                </el-tab-pane>

                <!-- 4. AI Setup Tab -->
                <el-tab-pane label="AI 配置 (AI Setup)" name="ai">
                    <el-form label-position="top" style="max-width: 600px">
                        <el-alert
                            title="智能角色推荐协议"
                            type="warning"
                            :closable="false"
                            show-icon
                            style="margin-bottom: 20px"
                        >
                            启用此项将发送您的<b>变量名称（不含原始数据）</b>到第三方大模型。请确保您拥有相关授权。
                        </el-alert>
                        
                        <el-form-item label="API Base URL">
                            <el-input v-model="settings.llm_api_base" placeholder="https://api.openai.com/v1" />
                            <div class="form-helper">连接第三方大模型的 API 入口。</div>
                        </el-form-item>

                        <el-form-item label="API Key">
                            <el-input v-model="settings.llm_key" type="password" show-password placeholder="sk-..." />
                            <div class="form-helper">用于鉴权的密钥，建议使用具有限额保护的 Key。</div>
                        </el-form-item>

                        <el-form-item label="模型名称 (Model Name)">
                            <el-input v-model="settings.llm_model" placeholder="gpt-4o / deepseek-ai/DeepSeek-V3" />
                            <div class="form-helper">指定调用的具体模型 ID。SiliconFlow 示例: <code style="background: #eee; padding: 2px 4px;">deepseek-ai/DeepSeek-V3</code></div>
                        </el-form-item>
                        
                        <el-form-item>
                            <el-button type="primary" @click="saveSettings" :loading="saving">保存 AI 配置 (Save AI Setup)</el-button>
                        </el-form-item>
                    </el-form>
                </el-tab-pane>
            </el-tabs>
        </el-card>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
import { useUserStore } from '../../stores/user'

const activeTab = ref('statistics')
const saving = ref(false)
const changingPwd = ref(false)
const pwdFormRef = ref(null)

const settings = reactive({
    theme: 'light',
    p_value: 0.05,
    digits: 3,
    llm_key: '',
    llm_api_base: 'https://api.openai.com/v1',
    llm_model: 'gpt-4o'
})

const pwdForm = reactive({
    current_password: '',
    new_password: '',
    confirm_password: ''
})

const pwdRules = {
    current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
    new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '至少6位', trigger: 'blur' }],
    confirm_password: [
        { required: true, message: '请确认新密码', trigger: 'blur' },
        { 
            validator: (rule, value, callback) => {
                if (value !== pwdForm.new_password) {
                    callback(new Error('两次密码输入不一致'))
                } else {
                    callback()
                }
            }, 
            trigger: 'blur' 
        }
    ]
}

const userStore = useUserStore()

const fetchSettings = async () => {
    try {
        const { data } = await api.get('/settings/get')
        Object.assign(settings, data)
        userStore.applyTheme(settings.theme)
    } catch (e) {
        console.error(e)
    }
}

const saveSettings = async () => {
    saving.value = true
    try {
        console.log('Saving settings:', settings)
        await api.put('/settings/update', settings)
        userStore.applyTheme(settings.theme)
        ElMessage.success('配置已保存 (Preferences Saved)')
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '保存失败')
    } finally {
        saving.value = false
    }
}

const changePassword = async () => {
    if (!pwdFormRef.value) return
    
    await pwdFormRef.value.validate(async (valid) => {
        if (valid) {
            changingPwd.value = true
            try {
                await api.post('/auth/change-password', {
                    current_password: pwdForm.current_password,
                    new_password: pwdForm.new_password
                })
                ElMessage.success('密码修改成功，请重新登录')
                // Optional: Logout user
            } catch (e) {
                ElMessage.error(e.response?.data?.message || '修改失败')
            } finally {
                changingPwd.value = false
            }
        }
    })
}

onMounted(() => {
    fetchSettings()
})
</script>

<style scoped>
.settings-container {
    padding: 20px;
}
.form-helper {
    font-size: 12px;
    color: #909399;
    margin-top: -10px;
}
</style>
