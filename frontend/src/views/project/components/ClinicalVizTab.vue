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
                <el-radio label="logistic">Logistic回归</el-radio>
                <el-radio label="cox">Cox生存分析</el-radio>
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
                                <el-input-number 
                                    v-model="inputs[v.name]" 
                                    :min="v.min" 
                                    :max="v.max" 
                                    :step="(v.max - v.min) / 100"
                                    style="width: 100%"
                                />
                                <div class="help-text">{{ v.min }} - {{ v.max }}</div>
                            </el-form-item>
                          </el-form>
                      </el-col>
                      
                      <el-col :span="12" class="result-display">
                          <h3>预测结果</h3>
                          <div class="risk-circle" :style="{ backgroundColor: riskColor }">
                              <span class="risk-value">{{ (currentRisk * 100).toFixed(1) }}%</span>
                              <span class="risk-label">Predicted Probability</span>
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
import { ref, reactive, computed, watch, nextTick } from "vue";
import { ElMessage } from "element-plus";
import api from "../../../api/client";
import Plotly from "plotly.js-dist-min";

const props = defineProps({
  datasetId: Number,
  metadata: Object,
});

const loading = ref(false);
const vizData = ref(null);
const activeTab = ref("calculator");
const inputs = reactive({});

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
    
    // Initialize inputs to min value
    data.variables.forEach(v => {
        inputs[v.name] = v.min;
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

// --- Calculator Logic ---
const currentRisk = computed(() => {
    if (!vizData.value || !vizData.value.formula) return 0;
    
    const f = vizData.value.formula;
    let lp = f.intercept;
    
    // Sum Betas * X
    for (const [varName, coef] of Object.entries(f.coeffs)) {
        const val = inputs[varName] || 0;
        lp += val * coef;
    }
    
    if (f.model_type === 'logistic') {
        return 1 / (1 + Math.exp(-lp));
    } else if (f.model_type === 'cox') {
        // Cox: 1 - S0^exp(lp)
        // Note: intercept in params usually is 0 for Cox in python libs unless specifically handled.
        // We rely on baseline_survival.
        if (f.baseline_survival) {
            // lp here should be centered if fit was centered? 
            // Simplified: Assume straightforward application. 
            // In lifelines, predict_survival_function(X) uses X*beta.
            return 1 - Math.pow(f.baseline_survival, Math.exp(lp));
        }
        return 0;
    }
    return 0;
});

const riskColor = computed(() => {
    const p = currentRisk.value;
    if (p < 0.1) return '#67C23A'; // Green
    if (p < 0.5) return '#E6A23C'; // Orange
    return '#F56C6C'; // Red
});

// --- Nomogram Plotting ---
const renderNomogram = (data) => {
    const traces = [];
    let yOffset = 0;
    const yTickVals = [];
    const yTickText = [];
    
    // 1. Plot Variables
    data.variables.forEach((v, idx) => {
        const yPos = idx * 2; 
        yTickVals.push(yPos);
        yTickText.push(v.name);
        
        // Line spanning range
        const pts = v.points_mapping.map(m => m.pts);
        const vals = v.points_mapping.map(m => m.val);
        const minPt = Math.min(...pts);
        const maxPt = Math.max(...pts);
        
        // Main Line
        traces.push({
            x: [minPt, maxPt],
            y: [yPos, yPos],
            mode: 'lines',
            line: { color: 'black', width: 2 },
            showlegend: false,
            hoverinfo: 'none'
        });
        
        // Ticks
        traces.push({
            x: pts,
            y: Array(pts.length).fill(yPos),
            mode: 'markers+text',
            text: vals.map(val => Number(val).toFixed(1)), // Value labels
            textposition: 'top center',
            marker: { symbol: 'line-ns-open', color: 'black', size: 10, line: {width: 2} },
            showlegend: false,
            hoverinfo: 'text',
            hovertext: vals.map((val, i) => `${v.name}=${val} -> ${pts[i].toFixed(1)} pts`)
        });
    });
    
    // 2. Plot Total Points Scale
    const totalPointsY = data.variables.length * 2 + 1;
    yTickVals.push(totalPointsY);
    yTickText.push("Total Points");
    
    // Find absolute max points possible (sum of all max points)
    // data.risk_table covers the range.
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
    
    // Ticks for Total Points (every 10 or so)
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
    
    // 3. Risk Scale
    const riskY = totalPointsY + 1;
    yTickVals.push(riskY);
    yTickText.push("Risk / Prob");
    
    // Map Risk back to Points for plotting
    // risk_table has {points, risk}.
    // We want to show ticks for Risk = 0.1, 0.2 ... 0.9.
    const riskTicks = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99];
    const riskTickPts = [];
    const riskTickLabels = [];
    
    // Interpolate Points for these Risks
    // risk_table is monotonic
    const table_sorted = [...data.risk_table].sort((a,b) => a.points - b.points);
    
    riskTicks.forEach(r => {
        // Find closest point or linear interp
        // For simplicity: Find nearest
        const nearest = table_sorted.reduce((prev, curr) => Math.abs(curr.risk - r) < Math.abs(prev.risk - r) ? curr : prev);
        if (Math.abs(nearest.risk - r) < 0.05) { // Threshold
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
        xaxis: { title: 'Points', zeroline: false },
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
