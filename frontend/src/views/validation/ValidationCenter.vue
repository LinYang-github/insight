
<template>
  <div class="validation-center">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h2 class="title">质量与验证中心 (Quality & Validation Center)</h2>
        <p class="subtitle">
          基于国际标准 R 语言与其内置数据集 (NIST StRD) 的实时验证报告
        </p>
      </div>
      <div class="header-actions">
        <!-- Dataset Selector -->
         <el-select v-model="validationScenario" placeholder="选择验证场景" style="width: 200px; margin-right: 12px">
            <el-option label="标准场景 (Standard)" :value="false" />
            <el-option label="大规模数据 (Large Scale)" :value="true" />
         </el-select>

        <el-button 
            type="primary" 
            size="large" 
            :loading="loading"
            @click="handleRunValidation"
        >
          <el-icon class="el-icon--left"><VideoPlay /></el-icon>
          立即运行验证 (Run Self-Check)
        </el-button>
        <el-button @click="downloadReport" :disabled="!reportData">
            <el-icon class="el-icon--left"><Download /></el-icon>
            导出报告
        </el-button>
      </div>
    </div>

    <!-- Dashboard Cards -->
    <el-row :gutter="20" class="dashboard-cards">
      <el-col :span="8">
        <el-card shadow="hover" class="status-card">
          <template #header>
            <div class="card-header">
              <span>系统状态 (System Status)</span>
              <el-tag :type="overallStatus === 'PASS' ? 'success' : 'danger'" effect="dark">
                {{ overallStatus === 'PASS' ? '✅ Validated' : '⚠️ Attention' }}
              </el-tag>
            </div>
          </template>
          <div class="status-content">
            <div class="metric">
              <div class="label">通过率</div>
              <div class="value">{{ passRate }}%</div>
            </div>
            <div class="metric">
              <div class="label">测试用例</div>
              <div class="value">{{ totalTests }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="hover">
            <template #header>
                <span>验证说明</span>
            </template>
            <div class="info-text">
                本平台算法核心基于 <b>Python Statsmodels (v0.14.1)</b> 与 <b>Lifelines (v0.28.0)</b>。
                <br/>
                如果不确定分析结果是否准确，请点击右上角按钮进行实时校验。校验大约耗时 3-5 秒。
                <br/>
                <small style="color: #909399">最新验证时间: {{ lastRunTime || '尚未运行' }}</small>
            </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="validation-tabs" type="border-card">
      
      <!-- Scientific Benchmarks -->
      <el-tab-pane label="科学性验证 (Scientific)" name="scientific">
        <div v-if="!reportData" class="empty-state">
            <el-empty description="请运行验证以查看详细数据" />
        </div>
        <div v-else>
            <div v-for="(test, index) in reportData.scientific" :key="index" class="benchmark-block">
                <div class="test-header">
                    <h3>{{ test.test_name }}</h3>
                    <div class="test-actions">
                         <el-button-group v-if="test.test_name.includes('Large')">
                             <el-button size="small" text bg @click="handleDownloadData('benchmark_logistic_large.csv')">
                                <el-icon><Download /></el-icon> Data (Large)
                             </el-button>
                         </el-button-group>

                         <el-button-group v-else-if="test.test_name.includes('Logistic')">
                             <el-button size="small" text bg @click="handleDownloadData('benchmark_logistic.csv')">
                                <el-icon><Download /></el-icon> Data
                             </el-button>
                             <el-button size="small" text bg @click="handleDownloadData('open_validation/benchmark_logistic.R')">
                                <el-icon><Download /></el-icon> R Script
                             </el-button>
                         </el-button-group>

                         <el-button-group v-else-if="test.test_name.includes('Cox')">
                             <el-button size="small" text bg @click="handleDownloadData('benchmark_cox.csv')">
                                <el-icon><Download /></el-icon> Data
                             </el-button>
                             <el-button size="small" text bg @click="handleDownloadData('open_validation/benchmark_cox.R')">
                                <el-icon><Download /></el-icon> R Script
                             </el-button>
                         </el-button-group>

                          <el-button-group v-else-if="test.test_name.includes('T-test')">
                             <el-button size="small" text bg @click="handleDownloadData('benchmark_ttest.csv')">
                                <el-icon><Download /></el-icon> Data
                             </el-button>
                             <el-button size="small" text bg @click="handleDownloadData('open_validation/benchmark_ttest.R')">
                                <el-icon><Download /></el-icon> R Script
                             </el-button>
                         </el-button-group>

                        <el-tag :type="test.status === 'PASS' ? 'success' : 'danger'" style="margin-left: 12px">
                            {{ test.status }}
                        </el-tag>
                    </div>
                </div>
                <!-- Scientific Table -->
                <el-table :data="test.metrics" border style="width: 100%" size="small">
                    <el-table-column prop="name" label="指标 (Metric)" width="180" />
                    <el-table-column prop="value_insight" label="Insight 平台计算值" width="180">
                        <template #default="scope">
                            <code>{{ formatNumber(scope.row.value_insight) }}</code>
                        </template>
                    </el-table-column>
                    <el-table-column prop="value_r" label="R 语言标准值 (Expected)" width="180">
                        <template #default="scope">
                            <span style="color: #909399">{{ scope.row.value_r }}</span>
                        </template>
                    </el-table-column>
                    <el-table-column prop="value_sas" label="SAS 标准值 (Ref)" width="180">
                         <template #default="scope">
                            <span style="color: #409EFF">{{ scope.row.value_sas || 'N/A' }}</span>
                        </template>
                    </el-table-column>
                    <el-table-column prop="delta" label="偏差 (Delta)" width="120">
                         <template #default="scope">
                            {{ scope.row.delta.toFixed(6) }}
                        </template>
                    </el-table-column>
                    <el-table-column label="结论" width="120">
                        <template #default="scope">
                            <el-tag v-if="scope.row.pass" type="success" size="small">✅ 通过</el-tag>
                            <el-tag v-else type="danger" size="small">❌ 失败</el-tag>
                        </template>
                    </el-table-column>
                </el-table>

                <!-- Assumptions Section -->
                <div v-if="test.assumptions && test.assumptions.length > 0" class="assumptions-section" style="margin-top: 12px; background: #f8f9fa; padding: 12px; border-radius: 4px;">
                    <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #606266;">📊 自动假设检验 (Automated Assumption Checks)</h4>
                    <el-table :data="test.assumptions" border size="small" style="width: 100%">
                        <el-table-column prop="check" label="检验项目 (Assumption)" />
                        <el-table-column prop="p_value" label="P值 (P-Value)" width="120">
                            <template #default="scope">
                                {{ scope.row.p_value != null ? scope.row.p_value.toFixed(4) : 'N/A' }}
                            </template>
                        </el-table-column>
                        <el-table-column prop="status" label="状态" width="100">
                             <template #default="scope">
                                <el-tag :type="scope.row.status === 'PASS' ? 'success' : 'warning'" size="small" effect="dark">
                                    {{ scope.row.status === 'PASS' ? 'Met' : 'Violated' }}
                                </el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="message" label="结论 (Conclusion)" />
                    </el-table>
                </div>
                <el-divider />
            </div>
        </div>
      </el-tab-pane>

    <!-- Phase 3: Stress Test Sandbox Tab -->
    <el-tab-pane label="压力测试沙箱 (Stress Sandbox)" name="sandbox">
        <div class="sandbox-container">
            <el-row :gutter="20">
                <el-col :span="8">
                    <el-card>
                        <template #header>
                            <div class="card-header">
                                <span>🧪 实验配置 (Config)</span>
                            </div>
                        </template>
                        <el-form label-position="top">
                             <el-form-item label="基础数据集 (Dataset)">
                                <el-select v-model="sandboxConfig.dataset" style="width: 100%">
                                    <el-option label="Logistic Benchmark (GPA data)" value="logistic" />
                                </el-select>
                            </el-form-item>
                             <el-form-item label="注入故障类型 (Fault Injection)">
                                <el-select v-model="sandboxConfig.fault" style="width: 100%">
                                    <el-option label="共线性注入 (Collinearity)" value="collinearity" />
                                    <el-option label="缺失值注入 (Missing Data)" value="missing" />
                                    <el-option label="离群值注入 (Outliers)" value="outliers" />
                                </el-select>
                            </el-form-item>
                            <el-form-item label="强度 (Severity)">
                                <el-slider v-model="sandboxConfig.severity" :min="0.1" :max="5.0" :step="0.1" show-input />
                            </el-form-item>
                            <el-button type="warning" style="width: 100%" @click="runStressTest" :loading="stressLoading">
                                开始压力测试 (Run Stress Test)
                            </el-button>
                        </el-form>
                    </el-card>
                </el-col>
                <el-col :span="16">
                    <el-card v-if="stressResult">
                        <template #header>
                            <div class="card-header">
                                <span>📋 测试报告 (Report)</span>
                                <el-tag :type="stressResult.result.status === 'SUCCESS' ? 'success' : 'danger'">
                                    {{ stressResult.result.status }}
                                </el-tag>
                            </div>
                        </template>
                        <div class="stress-report">
                            <p><strong>操作 (Action):</strong> {{ stressResult.details.action }}</p>
                            <p><strong>系统反馈 (Message):</strong> {{ stressResult.result.message }}</p>
                            
                            <div v-if="stressResult.result.model_summary">
                                <h4>Model Summary Snippet:</h4>
                                <!-- Simple check for singular matrix warning in summary if accessible, or just show it exists -->
                                <pre style="background: #f4f4f5; padding: 10px; overflow: auto; max-height: 300px">{{ formatSummary(stressResult.result.model_summary) }}</pre>
                            </div>
                            <div v-if="stressResult.result.error">
                                <h4>Error Details:</h4>
                                <el-alert :title="stressResult.result.error" type="error" :closable="false" />
                            </div>
                        </div>
                    </el-card>
                    <el-empty v-else description="请左侧配置并运行测试" />
                </el-col>
            </el-row>
        </div>
    </el-tab-pane>

      <!-- Robustness Tests -->
      <el-tab-pane label="鲁棒性测试 (Robustness)" name="robustness">
         <div v-if="!reportData" class="empty-state">
            <el-empty description="请运行验证以查看详细数据" />
        </div>
        <div v-else>
            <el-table :data="reportData.robustness" border style="width: 100%">
                <el-table-column prop="case" label="测试场景 (Scenario)" width="200" />
                <el-table-column prop="expected" label="预期行为" width="180" />
                <el-table-column prop="actual" label="实际反馈 (System Output)" min-width="250">
                    <template #default="scope">
                        <code>{{ scope.row.actual }}</code>
                    </template>
                </el-table-column>
                <el-table-column prop="message" label="分析说明" />
                 <el-table-column label="状态" width="100">
                    <template #default="scope">
                        <el-tag :type="scope.row.status === 'PASS' ? 'success' : 'danger'">
                            {{ scope.row.status }}
                        </el-tag>
                    </template>
                </el-table-column>
            </el-table>
        </div>
      </el-tab-pane>

    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { VideoPlay, Download } from '@element-plus/icons-vue'
import { runValidation, downloadDataset, generateReport, runStressTest as apiRunStressTest } from '@/api/validation'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const activeTab = ref('scientific')
const reportData = ref(null)
const lastRunTime = ref('')
const validationScenario = ref(false) // false = standard, true = large

// Phase 3: Stress Test State
const sandboxConfig = ref({
    dataset: 'logistic',
    fault: 'collinearity',
    severity: 1.0
})
const stressResult = ref(null)
const stressLoading = ref(false)

const overallStatus = computed(() => {
    return reportData.value?.summary?.status || 'UNKNOWN'
})

const passRate = computed(() => {
    if (!reportData.value) return 0
    const { total_tests, passed } = reportData.value.summary
    if (total_tests === 0) return 0
    return Math.round((passed / total_tests) * 100)
})

const totalTests = computed(() => {
     return reportData.value?.summary?.total_tests || 0
})

const runStressTest = async () => {
    stressLoading.value = true
    stressResult.value = null
    try {
        const res = await apiRunStressTest(sandboxConfig.value)
        stressResult.value = res.data
        if (res.data.result.status === 'SUCCESS') {
             ElMessage.success('压力测试执行完成')
        } else {
             ElMessage.warning('压力测试模型失败 (符合预期)')
        }
    } catch (error) {
        ElMessage.error('服务调用失败')
        console.error(error)
    } finally {
        stressLoading.value = false
    }
}

const formatSummary = (summary) => {
    // Basic formatting for the summary if it's a list of dicts or object
    if (!summary) return ''
    if (Array.isArray(summary)) {
        return summary.map(row => `${row.variable}: ${row.coef.toFixed(4)} (p=${row.p_value})`).join('\n')
    }
    return JSON.stringify(summary, null, 2)
}

const handleRunValidation = async () => {
    loading.value = true
    try {
        const res = await runValidation({ use_large_dataset: validationScenario.value })
        reportData.value = res.data
        lastRunTime.value = new Date().toLocaleString()
        ElMessage.success('验证完成，系统运行正常')
    } catch (error) {
        console.error(error)
        ElMessage.error('验证执行失败，请检查后端服务')
    } finally {
        loading.value = false
    }
}


const handleDownloadData = async (filename) => {
    try {
        const response = await downloadDataset(filename)
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', filename)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        ElMessage.success("下载已开始")
    } catch (error) {
        ElMessage.error("下载失败")
    }
}

const formatNumber = (num) => {
    if (typeof num === 'number') {
        return num.toFixed(4)
    }
    return num
}

const downloadReport = async () => {
    if (!reportData.value) return
    try {
        const response = await generateReport(reportData.value)
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', 'Insight_Validation_Report.pdf')
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        ElMessage.success("报告已生成")
    } catch (e) {
        ElMessage.error("导出失败")
    }
}
</script>

<style scoped>
.validation-center {
    padding: 24px;
    max-width: 1200px;
    margin: 0 auto;
    height: 100%;
    overflow-y: auto;
    box-sizing: border-box;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
}

.title {
    margin: 0;
    font-size: 24px;
    color: #303133;
}

.subtitle {
    margin: 8px 0 0;
    color: #606266;
    font-size: 14px;
}

.dashboard-cards {
    margin-bottom: 24px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.status-content {
    display: flex;
    gap: 40px;
}

.metric .label {
    font-size: 12px;
    color: #909399;
}

.metric .value {
    font-size: 24px;
    font-weight: bold;
    color: #303133;
}

.info-text {
    line-height: 1.6;
    color: #606266;
}

.validation-tabs {
    min-height: 400px;
}

.benchmark-block {
    margin-bottom: 32px;
}

.test-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.test-actions {
    display: flex;
    align-items: center;
}

.test-header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
}

.empty-state {
    padding: 40px 0;
    text-align: center;
}
</style>
