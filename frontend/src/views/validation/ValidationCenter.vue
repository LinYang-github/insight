
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
        <el-button @click="downloadReport" disabled>
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
                        <el-button size="small" text bg @click="handleDownloadData('benchmark_logistic_large.csv')" v-if="test.test_name.includes('Large')">
                           <el-icon><Download /></el-icon> 下载测试数据 (Large)
                        </el-button>
                         <el-button size="small" text bg @click="handleDownloadData('benchmark_logistic.csv')" v-else-if="test.test_name.includes('Logistic')">
                           <el-icon><Download /></el-icon> 下载测试数据
                        </el-button>
                         <el-button size="small" text bg @click="handleDownloadData('benchmark_cox.csv')" v-else-if="test.test_name.includes('Cox')">
                           <el-icon><Download /></el-icon> 下载测试数据
                        </el-button>

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
                <el-divider />
            </div>
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
import { runValidation, downloadDataset } from '@/api/validation'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const activeTab = ref('scientific')
const reportData = ref(null)
const lastRunTime = ref('')
const validationScenario = ref(false) // false = standard, true = large

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

const downloadReport = () => {
    ElMessage.info('PDF 导出功能即将上线')
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
