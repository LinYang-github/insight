<template>
  <div v-if="!datasetId">
      <el-empty description="请先上传数据" />
  </div>
  <div v-else>
      <!-- Configuration Panel -->
     <el-card shadow="hover" style="margin-bottom: 20px;">
          <template #header>
               <div style="display: flex; justify-content: space-between; align-items: center;">
                   <span>纵向分析配置 (Longitudinal Config)</span>
                   <el-button 
                        type="primary" 
                        link 
                        :icon="MagicStick" 
                        @click="suggestRoles"
                        :loading="isSuggestingRoles"
                    >
                        AI 智能推荐
                    </el-button>
               </div>
           </template>
          <el-form :inline="true" class="demo-form-inline">
              <el-form-item label="个体 ID (Subject ID)">
                  <el-select v-model="config.id_col" filterable placeholder="选择 ID 变量">
                       <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                  </el-select>
              </el-form-item>
              <el-form-item label="时间变量 (Time)">
                  <el-select v-model="config.time_col" filterable placeholder="选择时间变量">
                       <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                  </el-select>
              </el-form-item>
              <el-form-item label="结局指标 (Outcome)">
                  <el-select v-model="config.outcome_col" filterable placeholder="选择结局变量 (如 eGFR)">
                       <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                  </el-select>
              </el-form-item>
          </el-form>
     </el-card>

     <el-tabs type="border-card" v-model="activeName">
         <!-- 1. Linear Mixed Models -->
         <el-tab-pane label="混合效应模型 (LMM)" name="lmm">
             <div style="margin-bottom: 20px;">
                <el-form :inline="true">
                    <el-form-item label="固定效应 (Fixed Effects)">
                        <el-select v-model="config.fixed_effects" multiple placeholder="选择协变量">
                             <el-option v-for="v in variables" :key="v.name" :label="v.name" :value="v.name" />
                        </el-select>
                    </el-form-item>
                    <el-button type="primary" @click="fitLMM" :loading="loading.lmm">运行 LMM</el-button>
                </el-form>
             </div>
             
             <div v-if="results.lmm">
                 <el-alert title="模型收敛" type="success" :closable="false" v-if="results.lmm.converged" style="margin-bottom: 10px;" />
                 <el-alert title="模型未收敛" type="warning" :closable="false" v-else style="margin-bottom: 10px;" />
                 
                 <el-row :gutter="20">
                     <el-col :span="14">
                          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                              <h4 style="margin: 0;">固定效应 (Population Trends)</h4>
                              <div>
                                  <el-button 
                                      type="primary" 
                                      size="small" 
                                      @click="runAILMM" 
                                      :loading="isInterpreting.lmm" 
                                      :icon="MagicStick" 
                                      class="ai-advanced-btn" 
                                      style="margin-right: 10px;" 
                                  >
                                      AI 深度解读
                                  </el-button>
                                  <el-button v-if="lmmMethodology" size="small" type="primary" link @click="copyText(lmmMethodology)">复制方法学 (Copy Methods)</el-button>
                              </div>
                          </div>
                          <InterpretationPanel 
                                v-if="aiInterpretation.lmm"
                                :interpretation="{ text: aiInterpretation.lmm, is_ai: true, level: 'info' }"
                                style="margin-bottom: 15px;"
                          />
                         <PublicationTable :data="results.lmm.summary">
                             <el-table-column prop="variable" label="变量" />
                             <el-table-column prop="coef" label="系数 (Coef)">
                                <template #default="scope">{{ scope.row.coef.toFixed(4) }}</template>
                             </el-table-column>
                             <el-table-column prop="p_value" label="P值">
                                 <template #default="scope">
                                     <StatValue :value="scope.row.p_value" type="p-value" />
                                 </template>
                             </el-table-column>
                             <el-table-column label="95% CI">
                                 <template #default="scope">
                                     {{ scope.row.ci_lower.toFixed(3) }} - {{ scope.row.ci_upper.toFixed(3) }}
                                 </template>
                             </el-table-column>
                         </PublicationTable>
                     </el-col>
                     <el-col :span="10">
                         <h4>随机效应摘要 (Random Effects)</h4>
                         <p style="font-size: 13px; color: #666;">
                             AIC: {{ results.lmm.aic.toFixed(2) }} | BIC: {{ results.lmm.bic.toFixed(2) }}
                         </p>
                         <InsightChart
                            chartId="hist-slopes"
                            title="个体斜率分布 (Indiv. Slopes Distribution)"
                            :data="charts.slopes.data"
                            :layout="charts.slopes.layout"
                         />
                     </el-col>
                 </el-row>
             </div>
         </el-tab-pane>

         <!-- 2. Trajectory Clustering -->
         <el-tab-pane label="轨迹聚类 (Trajectory Clustering)" name="clustering">
              <div style="margin-bottom: 20px;">
                  <span style="margin-right: 10px;">聚类簇数 (K):</span>
                  <el-input-number v-model="config.n_clusters" :min="2" :max="6" size="small" />
                  <el-button type="primary" @click="runClustering" :loading="loading.clustering" style="margin-left: 20px;">运行聚类</el-button>
              </div>
              
              <div v-if="results.clustering">
                  <div style="margin-bottom: 15px;">
                      <el-button 
                          type="primary" 
                          size="small" 
                          @click="runAIClustering" 
                          :loading="isInterpreting.clustering"
                          :icon="MagicStick"
                          class="ai-advanced-btn"
                      >
                          AI 聚类解读
                      </el-button>
                  </div>
                  
                  <InterpretationPanel 
                        v-if="aiInterpretation.clustering"
                        :interpretation="{ text: aiInterpretation.clustering, is_ai: true, level: 'info' }"
                        style="margin-bottom: 20px;"
                  />

                  <div style="margin-bottom: 15px;">
                      <el-button 
                          type="primary" 
                          size="small" 
                          @click="runAIClustering" 
                          :loading="isInterpreting.clustering"
                          :icon="MagicStick"
                          class="ai-advanced-btn"
                      >
                          AI 聚类解读
                      </el-button>
                  </div>
                  
                  <InterpretationPanel 
                        v-if="aiInterpretation.clustering"
                        :interpretation="{ text: aiInterpretation.clustering, is_ai: true, level: 'info' }"
                        style="margin-bottom: 20px;"
                  />

                  <el-row :gutter="20">
                      <el-col :span="16">
                          <InsightChart
                             chartId="traj-plot"
                             title="按簇划分的轨迹图 (Spaghetti Plot by Cluster)"
                             :data="charts.trajectory.data"
                             :layout="charts.trajectory.layout"
                          />
                      </el-col>
                      <el-col :span="8">
                          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                               <h4>簇中心 (Centroids)</h4>
                               <el-button v-if="trajMethodology" size="small" type="primary" link @click="copyText(trajMethodology)">复制方法学 (Copy Methods)</el-button>
                          </div>
                          <el-table :data="results.clustering.centroids" border size="small">
                              <el-table-column prop="cluster" label="分组 (Cluster)" width="80" />
                              <el-table-column prop="slope" label="平均斜率 (Avg Slope)">
                                  <template #default="scope">{{ scope.row.slope.toFixed(4) }}</template>
                              </el-table-column>
                          </el-table>
                          <div style="margin-top: 20px;">
                               <el-tag v-for="(item, i) in results.clustering.centroids" :key="i" 
                                    :color="clusterColors[i]" effect="dark" style="display: block; margin-bottom: 5px; border: none;">
                                   分组 (Cluster) {{ i }}: 斜率 {{ item.slope.toFixed(3) }}
                               </el-tag>
                          </div>
                      </el-col>
                  </el-row>
              </div>
         </el-tab-pane>

         <!-- 3. Variability -->
         <el-tab-pane label="变异性指标 (Variability)" name="variability">
             <div style="margin-bottom: 20px;">
                 <el-button type="primary" @click="calcVariability" :loading="loading.variability">计算部分指标 (SD, CV, ARV)</el-button>
             </div>
             
             <div v-if="results.variability">
                 <PublicationTable :data="results.variability.slice(0, 10)">
                     <el-table-column prop="id" label="个体 ID" />
                     <el-table-column prop="n_visits" label="随访次数 (Visits)" />
                     <el-table-column prop="mean" label="均值 (Mean)">
                         <template #default="scope">{{ scope.row.mean.toFixed(2) }}</template>
                     </el-table-column>
                     <el-table-column prop="sd" label="标准差 (SD)">
                         <template #default="scope">{{ scope.row.sd.toFixed(2) }}</template>
                     </el-table-column>
                     <el-table-column prop="cv" label="变异系数 (CV %)">
                         <template #default="scope">{{ scope.row.cv.toFixed(2) }}</template>
                     </el-table-column>
                     <el-table-column prop="arv" label="平均相继变异 (ARV)">
                         <template #default="scope">{{ scope.row.arv.toFixed(2) }}</template>
                     </el-table-column>
                 </PublicationTable>
                 <div style="text-align: center; margin-top: 10px; color: #909399;">仅展示前 10 行，请导出查看全部</div>
             </div>
         </el-tab-pane>
     </el-tabs>
  </div>
</template>

<script setup>
/**
 * LongitudinalTab.vue
 * 纵向数据分析 (Longitudinal Analysis) 标签页。
 * 
 * 职责：
 * 1. 拟合线性混合效应模型 (LMM)，分析结局指标随时间变化的总体趋势及个体差异。
 * 2. 执行轨迹聚类 (Trajectory Clustering)，识别具有相似变化斜率的患者亚组。
 * 3. 计算随访间变异性 (Visit-to-Visit Variability) 指标，如 SD, CV, ARV 等。
 * 4. 可视化纵向趋势图 (Spaghetti Plot) 与斜率分布。
 */
import { ref, reactive, computed } from 'vue'
import api from '../../../api/client'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import InterpretationPanel from './InterpretationPanel.vue'
import PublicationTable from '../../../components/PublicationTable.vue'
import StatValue from '../../../components/StatValue.vue'
import InsightChart from './InsightChart.vue'

const props = defineProps({
    datasetId: Number,
    metadata: Object
})

const activeName = ref('lmm')

const config = reactive({
    id_col: null,
    time_col: null,
    outcome_col: null,
    fixed_effects: [],
    n_clusters: 3
})

const loading = reactive({
    lmm: false,
    clustering: false,
    variability: false
}) // 各模块的加载状态

const results = reactive({
    lmm: null,
    clustering: null,
    variability: null
}) // 各模块的分析结果

const charts = reactive({
    slopes: { data: [], layout: {} },
    trajectory: { data: [], layout: {} }
}) // 图表配置与数据
const isSuggestingRoles = ref(false)
const isInterpreting = reactive({ lmm: false, clustering: false })
const aiInterpretation = reactive({ lmm: null, clustering: null })

// Methodology
const lmmMethodology = ref('')
const trajMethodology = ref('')
const varMethodology = ref('')

/**
 * 复制方法学描述到剪贴板。
 */
const copyText = (text) => {
    navigator.clipboard.writeText(text).then(() => {
        ElMessage.success('方法学段落已复制')
    })
}

const variables = computed(() => props.metadata?.variables || [])
const clusterColors = ['#F56C6C', '#E6A23C', '#67C23A', '#409EFF', '#909399']

/**
 * 运行线性混合效应模型 (LMM)。
 */
const fitLMM = async () => {
    if (!config.id_col || !config.time_col || !config.outcome_col) {
        ElMessage.warning('请先完整配置 ID、时间和结局变量')
        return
    }
    loading.lmm = true
    try {
        const { data } = await api.post('/longitudinal/lmm', {
            dataset_id: props.datasetId,
            ...config
        })
        results.lmm = data.results
        lmmMethodology.value = data.results.methodology
        renderSlopesChart(data.results.random_effects)
        ElMessage.success('LMM 运行成功')
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'Failed')
    } finally {
        loading.lmm = false
    }
}

const suggestRoles = async () => {
    isSuggestingRoles.value = true
    try {
        const { data } = await api.post('/longitudinal/ai-suggest-roles', {
            dataset_id: props.datasetId
        })
        
        config.id_col = data.id_col || config.id_col
        config.time_col = data.time_col || config.time_col
        config.outcome_col = data.outcome_col || config.outcome_col
        config.fixed_effects = data.fixed_effects || config.fixed_effects
        
        ElMessage({
            message: `AI 已为您推荐纵向分析的最佳变量角色。\n理由: ${data.reason || '基于重复测量数据特征推荐'}`,
            type: 'success',
            duration: 5000
        })
    } catch (e) {
        console.error("AI Role suggestion failed", e)
        ElMessage.error(e.response?.data?.message || "AI 推荐失败")
    } finally {
        isSuggestingRoles.value = false
    }
}

/**
 * 运行轨迹聚类分析。
 */
const runClustering = async () => {
    if (!config.id_col || !config.time_col || !config.outcome_col) {
        ElMessage.warning('请先完整配置参数')
        return
    }
    loading.clustering = true
    try {
        const { data } = await api.post('/longitudinal/clustering', {
            dataset_id: props.datasetId,
            ...config
        })
        results.clustering = data.results
        trajMethodology.value = data.results.methodology
        renderTrajChart(data.results.clusters)
        ElMessage.success('聚类完成')
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'Failed')
    } finally {
        loading.clustering = false
    }
}

/**
 * 计算变异性指标。
 */
const calcVariability = async () => {
    if (!config.id_col || !config.outcome_col) {
        ElMessage.warning('请先配置 ID 和结局变量')
        return
    }
    loading.variability = true
    try {
        const { data } = await api.post('/longitudinal/variability', {
            dataset_id: props.datasetId,
            id_col: config.id_col,
            outcome_col: config.outcome_col
        })
        results.variability = data.results.variability_data
        varMethodology.value = data.results.methodology
        ElMessage.success('计算成功')
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'Failed')
    } finally {
        loading.variability = false
    }
}

const runAILMM = async () => {
    isInterpreting.lmm = true
    try {
        const { data } = await api.post('/longitudinal/ai-interpret-longitudinal', {
            analysis_type: 'lmm',
            results: results.lmm.summary.map(row => ({
               term: row.variable,
               estimate: row.coef,
               p: row.p_value,
               lower: row.ci_lower,
               upper: row.ci_upper
            })),
            target: config.outcome_col,
            time_col: config.time_col
        })
        aiInterpretation.lmm = data.interpretation
        ElMessage.success("AI LMM 解读完成")
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'AI 解读失败')
    } finally {
        isInterpreting.lmm = false
    }
}

const runAIClustering = async () => {
    isInterpreting.clustering = true
    try {
        // Prepare cluster centers
        // Backend expects dict {cluster_id: {slope: float, intercept: float, n: int}}
        // results.clustering.centroids is array [{cluster, slope, intercept, n}, ...]
        const centers = {}
        results.clustering.centroids.forEach(c => {
            centers[c.cluster] = { slope: c.slope, intercept: c.intercept || 0, n: c.n || 0 }
        })

        const { data } = await api.post('/longitudinal/ai-interpret-longitudinal', {
            analysis_type: 'clustering',
            results: centers,
            target: config.outcome_col,
            time_col: config.time_col
        })
        aiInterpretation.clustering = data.interpretation
        ElMessage.success("AI 聚类解读完成")
    } catch (e) {
        ElMessage.error(e.response?.data?.message || 'AI 解读失败')
    } finally {
        isInterpreting.clustering = false
    }
}


// Chart Helpers
const renderSlopesChart = (re_data) => {
    const slopes = re_data.map(d => d.total_slope)
    charts.slopes.data = [{
        x: slopes,
        type: 'histogram',
        marker: { color: '#3B71CA' }
    }]
    charts.slopes.layout = {
        title: '总斜率分布 (固定+随机效应)',
        xaxis: { title: '斜率值 (Slope Value)' },
        yaxis: { title: '频数 (Count)' }
    }
}

const renderTrajChart = (clusters) => {
    // This assumes we have the raw time/outcome points to draw lines.
    // However, the current API `cluster_trajectories` returns slopes/intercepts in `result.clustering.clusters`.
    // It does NOT return the full longitudinal time points. 
    // To draw spaghetti, we ideally need the original data points joined with cluster ID.
    // For MVP, we can plot the "Estimated Trajectories" (lines) for each patient, 
    // using the regression params (intercept, slope) we have.
    
    // Limit to first 100 lines per cluster to avoid browser crash
    const traces = []
    const clusterGroups = {}
    
    clusters.forEach(c => {
        if (!clusterGroups[c.cluster]) clusterGroups[c.cluster] = []
        clusterGroups[c.cluster].push(c)
    })
    
    Object.keys(clusterGroups).forEach((k, i) => {
        const members = clusterGroups[k].slice(0, 50) // Sample 50 lines per cluster for clarity
        const color = clusterColors[i % clusterColors.length]
        
        // We need a time range to plot the line. Let's assume 0 to 5 (canonical).
        // Or we should ask backend for min/max time.
        // For visual, 0 to 10 is fine.
        const x = [0, 5] 
        
        members.forEach(m => {
            const y = [m.intercept, m.intercept + m.slope * 5]
            traces.push({
                x: x, y: y,
                mode: 'lines',
                line: { color: color, width: 1, opacity: 0.5 },
                showlegend: false,
                hoverinfo: 'none'
            })
        })
        
        // Add a dummy trace for legend
        traces.push({
            x: [null], y: [null],
            name: `Cluster ${k}`,
            line: { color: color, width: 2 },
            mode: 'lines'
        })
    })
    
    charts.trajectory.data = traces
    charts.trajectory.layout = {
        title: '预测轨迹图 (抽样展示)',
        xaxis: { title: '时间 (Time)' },
        yaxis: { title: '结局指标值 (Outcome)' }
    }
}

</script>
