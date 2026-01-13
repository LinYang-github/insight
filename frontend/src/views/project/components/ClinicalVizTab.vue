<template>
  <div class="clinical-viz-container">
    <el-row :gutter="20">
      <!-- Config Panel -->
      <el-col :span="6">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>模型配置 (Model Config)</span>
            </div>
          </template>
          <el-form label-position="top">
            <el-form-item label="模型类型 (Model Type)">
              <el-radio-group v-model="config.model_type">
                <el-radio value="logistic">Logistic回归</el-radio>
                <el-radio value="cox">Cox生存分析</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="结局变量 (Target)">
              <el-select v-model="config.target" placeholder="Select Outcome" filterable>
                <el-option
                  v-for="opt in variableOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="config.model_type === 'cox'" label="事件状态 (Event Status)">
              <el-select v-model="config.event_col" placeholder="Select Event (0/1)" filterable>
                <el-option
                  v-for="opt in variableOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="预测因子 (Predictors)">
              <el-select
                v-model="config.predictors"
                multiple
                placeholder="Select Predictors"
                filterable
              >
                <el-option
                  v-for="opt in variableOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>

            <el-button
              type="primary"
              style="width: 100%"
              @click="generateViz"
              :loading="loading"
            >
              生成工具 (Generate)
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- Results Panel -->
      <el-col :span="18">
        <el-card class="box-card" v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>临床应用工具 (Clinical Tools)</span>
            </div>
          </template>

          <div v-if="vizData">
            <el-tabs v-model="activeTab" type="border-card">
              <!-- Tab 1: Web Calculator -->
              <el-tab-pane label="在线计算器 (Web Calculator)" name="calculator">
                <div class="calculator-container">
                  <el-alert
                    title="交互式风险预测 (Interactive Calculator)"
                    type="success"
                    :closable="false"
                    show-icon
                    style="margin-bottom: 20px"
                  >
                        <div>
                            输入患者临床指标，实时计算预测概率。
                            <br/>
                            <span style="color:#67C23A">• 绿色 (Low Risk &lt; 10%)</span> | 
                            <span style="color:#E6A23C">• 橙色 (Moderate)</span> | 
                            <span style="color:#F56C6C">• 红色 (High Risk &gt; 50%)</span>
                        </div>
                  </el-alert>
                  
                  <el-row :gutter="40">
                      <el-col :span="12">
                          <h3>患者特征输入</h3>
                          <el-form label-position="right" label-width="150px">
                            <el-form-item v-for="v in vizData.variables" :key="v.name" :label="v.name">
                                <!-- Numeric Input -->
                                <div v-if="v.type === 'numeric'">
                                    <el-input-number 
                                        v-model="inputs[v.name]" 
                                        :min="v.min" 
                                        :max="v.max" 
                                        :step="(v.max - v.min) / 100"
                                        style="width: 100%"
                                    />
                                    <div class="help-text">{{ v.min }} - {{ v.max }}</div>
                                </div>
                                <!-- Categorical Input -->
                                <div v-else>
                                    <el-select v-model="inputs[v.name]" placeholder="Select Level" style="width: 100%">
                                        <el-option 
                                            v-for="m in v.points_mapping" 
                                            :key="m.val" 
                                            :label="m.val" 
                                            :value="m.val" 
                                        />
                                    </el-select>
                                </div>
                            </el-form-item>
                          </el-form>
                      </el-col>
                      
                      <el-col :span="12" class="result-display">
                          <h3>预测结果</h3>
                          <div class="risk-circle" :style="{ backgroundColor: riskColor }">
                              <span class="risk-value">{{ (currentRisk * 100).toFixed(1) }}%</span>
                              <span class="risk-label">预测概率 (Predicted Probability)</span>
                          </div>
                      </el-col>
                  </el-row>
                </div>
              </el-tab-pane>

              <!-- Tab 2: Nomogram Plot -->
              <el-tab-pane label="列线图 (Nomogram)" name="nomogram">
                 <el-alert
                    title="如何阅读列线图?"
                    type="info"
                    :closable="false"
                    show-icon
                    style="margin-bottom: 10px"
                  >
                    <div>
                        1. 在每个变量轴上找到患者的数值，向上投射到 <b>Points (分值)</b> 轴。
                        <br/>
                        2. 将所有变量的分值相加得到 <b>Total Points</b>。
                        <br/>
                        3. 在 Total Points 轴找到对应值，向下投射到 <b>Risk</b> 轴读取概率。
                    </div>
                  </el-alert>
                 <div id="nomogram-plot" style="width: 100%; height: 600px;"></div>
              </el-tab-pane>
            </el-tabs>
          </div>
          <el-empty v-else description="请配置模型以生成临床工具" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * ClinicalVizTab.vue
 * 临床预测工具可视化标签页。
 * 
 * 职责：
 * 1. 提供交互式在线风险计算器 (Web Calculator)。
 * 2. 生成静态或交互式的列线图 (Nomogram)。
 * 3. 支持 Logistic 回归和 Cox 生存分析两种模型。
 */
import { ref, reactive, computed, watch, nextTick } from "vue";
import { ElMessage } from "element-plus";
import api from "../../../api/client";
import Plotly from "plotly.js-dist-min";

const props = defineProps({
  datasetId: Number,
  metadata: Object,
});

const loading = ref(false); // 加载状态
const vizData = ref(null);   // 模型计算结果数据
const activeTab = ref("calculator"); // 当前选中的标签页
const inputs = reactive({}); // 患者指标输入值

const config = reactive({
  model_type: "logistic",
  target: "",
  event_col: "", // For Cox
  predictors: [],
});

const variableOptions = computed(() => {
  if (!props.metadata || !props.metadata.variables) return [];
  return props.metadata.variables.map((v) => ({
    label: v.name,
    value: v.name,
  }));
});

/**
 * 向后端请求生成列线图数据。
 */
const generateViz = async () => {
  if (!config.target || config.predictors.length === 0) {
    ElMessage.warning("请选择结局变量和至少一个预测因子");
    return;
  }

  loading.value = true;
  vizData.value = null;

  try {
    const { data } = await api.post("/advanced/nomogram", {
      dataset_id: props.datasetId,
      ...config,
    });
    vizData.value = data;
    
    // 初始化输入框，数值型选最小值，分类型选第一项
    data.variables.forEach(v => {
        if (v.type === 'numeric') {
            inputs[v.name] = v.min;
        } else {
            // Categorical: pick first level
            if (v.points_mapping && v.points_mapping.length > 0) {
                inputs[v.name] = v.points_mapping[0].val;
            }
        }
    });

    nextTick(() => {
        renderNomogram(data);
    });

  } catch (error) {
    ElMessage.error(error.response?.data?.message || "生成失败");
  } finally {
    loading.value = false;
  }
};

// --- 计算器逻辑 (基于后端返回的公式) ---
/**
 * 根据当前输入的指标值计算实时预测风险。
 */
const currentRisk = computed(() => {
    if (!vizData.value || !vizData.value.formula) return 0;
    
    const f = vizData.value.formula;
    let lp = f.intercept; // 线性预测值 (Linear Predictor)
    
    // 累加系数：Sum(Beta_i * X_i)
    for (const [varName, coef_or_map] of Object.entries(f.coeffs)) {
        const val = inputs[varName];
        
        // 判断是连续变量还是分类变量
        if (typeof coef_or_map === 'number') {
            // 数值型：变量值 * 系数
            lp += (Number(val) || 0) * coef_or_map;
        } else if (typeof coef_or_map === 'object') {
            // 分类型：根据 Level 查找对应的系数偏移
            const levelCoef = coef_or_map[val] || 0;
            lp += levelCoef;
        }
    }
    
    if (f.model_type === 'logistic') {
        // Logistic 模型：1 / (1 + exp(-LP))
        return 1 / (1 + Math.exp(-lp));
    } else if (f.model_type === 'cox') {
        if (f.baseline_survival) {
            // Cox 模型：1 - S0 ^ exp(LP)
            // 注意：此处 LP 通常不包含截距，后端已处理。
            return 1 - Math.pow(f.baseline_survival, Math.exp(lp));
        }
        return 0;
    }
    return 0;
});

/**
 * 风险颜色反馈：低风险绿色，中风险橙色，高风险红色。
 */
const riskColor = computed(() => {
    const p = currentRisk.value;
    if (p < 0.1) return '#67C23A'; // 绿色 (低)
    if (p < 0.5) return '#E6A23C'; // 橙色 (中)
    return '#F56C6C'; // 红色 (高)
});

// --- 列线图绘制逻辑 (基于 Plotly) ---
/**
 * 渲染列线图。
 * 通过将每个变量映射到 0-100 的 Score 轴，实现可视化的风险评估。
 */
const renderNomogram = (data) => {
    const traces = [];
    const yTickVals = [];
    const yTickText = [];
    
    // 1. 绘制各预测因子的坐标轴
    data.variables.forEach((v, idx) => {
        const yPos = idx * 2; 
        yTickVals.push(yPos);
        yTickText.push(v.name);
        
        // 坐标轴线条
        const pts = v.points_mapping.map(m => m.pts);
        const vals = v.points_mapping.map(m => m.val);
        const minPt = Math.min(...pts);
        const maxPt = Math.max(...pts);
        
        // 主干线
        traces.push({
            x: [minPt, maxPt],
            y: [yPos, yPos],
            mode: 'lines',
            line: { color: 'black', width: 2 },
            showlegend: false,
            hoverinfo: 'none'
        });
        
        // 刻度线与数值
        traces.push({
            x: pts,
            y: Array(pts.length).fill(yPos),
            mode: 'markers+text',
            text: vals.map(val => v.type === 'numeric' ? Number(val).toFixed(1) : val), 
            textposition: 'top center',
            marker: { symbol: 'line-ns-open', color: 'black', size: 10, line: {width: 2} },
            showlegend: false,
            hoverinfo: 'text',
            hovertext: vals.map((val, i) => `${v.name}=${val} -> ${pts[i].toFixed(1)} 分`)
        });
    });
    
    // 2. 绘制总分 (Total Points) 轴
    const totalPointsY = data.variables.length * 2 + 1;
    yTickVals.push(totalPointsY);
    yTickText.push("总分 (Total Points)");
    
    const riskPts = data.risk_table.map(r => r.points);
    const minRPt = Math.min(...riskPts);
    const maxRPt = Math.max(...riskPts);
    
    traces.push({
        x: [minRPt, maxRPt],
        y: [totalPointsY, totalPointsY],
        mode: 'lines',
        line: { color: 'black', width: 2 },
        showlegend: false
    });
    
    // 总分轴刻度
    const tpTicks = [];
    for(let i=Math.ceil(minRPt/10)*10; i<=maxRPt; i+=10) tpTicks.push(i);
    
    traces.push({
        x: tpTicks,
        y: Array(tpTicks.length).fill(totalPointsY),
        mode: 'markers+text',
        text: tpTicks.map(t => t.toString()),
        textposition: 'top center',
        marker: { symbol: 'line-ns-open', color: 'black', size: 10 },
        showlegend: false
    });
    
    // 3. 绘制概率 (Risk/Prob) 轴
    const riskY = totalPointsY + 1;
    yTickVals.push(riskY);
    yTickText.push("风险概率 (Risk / Prob)");
    
    // 概率刻度：通常展示关键的概率点 (0.1, 0.2 ... 0.9)
    const riskTicks = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99];
    const riskTickPts = [];
    const riskTickLabels = [];
    
    // 根据概率反推对应的总分，用于在轴上定位
    const table_sorted = [...data.risk_table].sort((a,b) => a.points - b.points);
    
    riskTicks.forEach(r => {
        const nearest = table_sorted.reduce((prev, curr) => Math.abs(curr.risk - r) < Math.abs(prev.risk - r) ? curr : prev);
        if (Math.abs(nearest.risk - r) < 0.05) { 
            riskTickPts.push(nearest.points);
            riskTickLabels.push(r.toString());
        }
    });

    traces.push({
        x: [minRPt, maxRPt],
        y: [riskY, riskY],
        mode: 'lines',
        line: { color: 'black', width: 2 },
        showlegend: false
    });
    
    traces.push({
        x: riskTickPts,
        y: Array(riskTickPts.length).fill(riskY),
        mode: 'markers+text',
        text: riskTickLabels,
        textposition: 'bottom center',
        marker: { symbol: 'line-ns-open', color: 'red', size: 10 },
        textfont: {color: 'red'},
        showlegend: false
    });

    const layout = {
        title: 'Nomogram',
        xaxis: { title: '分值 (Points)', zeroline: false },
        yaxis: { 
            tickvals: yTickVals,
            ticktext: yTickText,
            range: [-1, riskY + 1]
        },
        margin: { l: 150, r: 50, t: 50, b: 50 }
    };
    
    Plotly.newPlot("nomogram-plot", traces, layout);
};

</script>

<style scoped>
.clinical-viz-container {
  padding: 20px;
}
.help-text {
    font-size: 12px;
    color: #909399;
    margin-top: -5px;
}
.result-display {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.risk-circle {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    transition: background-color 0.5s;
}
.risk-value {
    font-size: 40px;
    font-weight: bold;
}
.risk-label {
    font-size: 14px;
    opacity: 0.9;
}
</style>
