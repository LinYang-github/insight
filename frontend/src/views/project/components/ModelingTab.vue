<template>
  <div v-if="!datasetId">
      <el-empty description="请先上传数据" />
  </div>
  <div v-else>
    <el-row :gutter="20">
       <el-col :span="10">
           <el-card shadow="hover">
               <template #header>
                   <span>模型配置</span>
               </template>
               <el-form label-position="top">
                   <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                       <span style="font-size: 14px; color: #606266; font-weight: 500;">变量配置 (Configuration)</span>
                       <el-tooltip content="智能推荐变量角色 (Auto-Suggest Roles)" placement="top">
                           <el-button type="primary" link @click="autoSuggestRoles" :icon="MagicStick">自动推荐</el-button>
                       </el-tooltip>
                   </div>
                   <el-form-item label="模型类型">
                       <el-select v-model="config.model_type" placeholder="选择模型" style="width: 100%">
                           <el-option v-for="opt in modelOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                       </el-select>
                   </el-form-item>
                   
                   <el-form-item label="目标变量 / 结局 (Target / Outcome)">
                       <template #label>
                            <span>目标变量 / 结局 (Target / Outcome)</span>
                            <el-tooltip content="您希望预测或研究的主要结果，例如“是否患病”、“生存时间”等。" placement="top">
                                <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                            </el-tooltip>
                       </template>
                       <template v-if="config.model_type !== 'cox'">
                           <el-select v-model="config.target" placeholder="选择目标变量" filterable style="width: 100%">
                               <el-option v-for="opt in targetOptions" :key="opt.value" :label="opt.label" :value="opt.value" :disabled="opt.disabled">
                                    <span v-if="opt.disabled" style="color: #ccc">{{ opt.label }} (Non-numeric)</span>
                                    <span v-else>{{ opt.label }}</span>
                               </el-option>
                           </el-select>
                       </template>
                       <template v-else>
                           <el-row :gutter="10">
                               <el-col :span="12">
                                   <el-select v-model="config.target.time" placeholder="时间变量 (Time)" filterable>
                                       <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                                   </el-select>
                               </el-col>
                               <el-col :span="12">
                                   <el-select v-model="config.target.event" placeholder="事件变量 (Event)" filterable>
                                       <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                                   </el-select>
                               </el-col>
                           </el-row>
                       </template>
                   </el-form-item>
                   
                   <el-form-item label="特征变量 (Covariates)">
                        <template #label>
                            <span>特征变量 (Covariates)</span>
                            <el-tooltip content="可能会影响结局的变量，包括您主要关心的变量和需要校正的混杂因素。" placement="top">
                                <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                            </el-tooltip>
                       </template>
                       <el-select v-model="config.features" multiple placeholder="选择特征变量" filterable style="width: 100%">
                           <el-option v-for="opt in variableOptions" :key="opt.value" :label="opt.label" :value="opt.value">
                               <div style="display: flex; justify-content: space-between; align-items: center;">
                                   <span>{{ opt.label }}</span>
                                   <el-tooltip v-if="opt.status !== 'unknown'" :content="opt.msg" placement="right">
                                       <span :style="{
                                           display: 'inline-block',
                                           width: '8px',
                                           height: '8px',
                                           borderRadius: '50%',
                                           backgroundColor: opt.status === 'healthy' ? '#67C23A' : '#E6A23C',
                                           marginLeft: '8px'
                                       }"></span>
                                   </el-tooltip>
                               </div>
                           </el-option>
                       </el-select>
                       
                       <!-- VIF Alert -->
                        <el-alert
                            v-if="collinearityWarning"
                            :title="collinearityWarning"
                            type="warning"
                            show-icon
                            style="margin-top: 10px"
                            :closable="false"
                        />
                   </el-form-item>
                   
                   <!-- Reference Levels (Advanced) -->
                   <el-collapse v-if="selectedCategoricalVars.length > 0" style="margin-bottom: 20px; border: 1px solid #EBEEF5;">
                        <el-collapse-item title="基准组设置 (Reference Levels)" name="1">
                            <template #title>
                                <el-icon style="margin-right: 5px"><Setting /></el-icon> 基准组设置 (Reference Levels)
                            </template>
                            <div style="padding: 10px;">
                                <div v-for="v in selectedCategoricalVars" :key="v.name" style="margin-bottom: 10px;">
                                    <span style="font-size: 12px; color: #606266; display: block; margin-bottom: 4px;">{{ v.name }} Reference:</span>
                                    <el-select v-model="config.ref_levels[v.name]" placeholder="Default (First)" size="small" style="width: 100%">
                                        <el-option v-for="cat in v.categories" :key="cat" :label="cat" :value="cat" />
                                    </el-select>
                                </div>
                                <div style="font-size: 12px; color: #909399; margin-top: 5px;">
                                    * 设置为基准的类别将在回归结果中作为对比参照（Intercept）。
                                </div>
                            </div>
                        </el-collapse-item>
                   </el-collapse>

                   <!-- Model Hyperparameters -->
                   <div v-if="['random_forest', 'xgboost'].includes(config.model_type)" style="background: #f5f7fa; padding: 10px; border-radius: 4px; margin-bottom: 18px;">
                        <span style="font-size: 12px; font-weight: bold; color: #606266; display: block; margin-bottom: 10px;">高级参数 (Advanced Params)</span>
                        <el-row :gutter="10">
                            <el-col :span="12">
                                <el-form-item label="树数量 (Trees)">
                                    <el-input-number v-model="config.model_params.n_estimators" :min="10" :max="1000" :step="10" size="small" style="width: 100%"/>
                                </el-form-item>
                            </el-col>
                            <el-col :span="12">
                                <el-form-item label="最大深度 (Depth)">
                                     <el-input-number v-model="config.model_params.max_depth" :min="1" :max="50" size="small" placeholder="Unlimited" style="width: 100%"/>
                                </el-form-item>
                            </el-col>
                             <el-col :span="12" v-if="config.model_type === 'xgboost'">
                                <el-form-item label="学习率 (Rate)">
                                     <el-input-number v-model="config.model_params.learning_rate" :min="0.001" :max="1.0" :step="0.01" size="small" style="width: 100%"/>
                                </el-form-item>
                            </el-col>
                        </el-row>
                   </div>
                   
                   <el-button type="primary" style="width: 100%" @click="runModel" :loading="loading">运行模型</el-button>
               </el-form>
           </el-card>
       </el-col>
       
       <el-col :span="14">
           <el-card shadow="hover" v-if="results">
                <template #header>
                    <div class="result-header">
                        <span>运行结果</span>
                        <div>
                             <el-button 
                                 v-if="!baselineResult" 
                                 size="small" 
                                 @click="setAsBaseline"
                                 title="设为基线模型 (Model 1)"
                             >
                                设为基线
                             </el-button>
                             <el-button 
                                 v-else 
                                 type="warning" 
                                 plain 
                                 size="small" 
                                 @click="compareWithBaseline"
                                 title="与基线模型对比 (Model 2 vs Model 1)"
                             >
                                 对比基线
                             </el-button>
                             
                             <el-button type="info" plain size="small" @click="copyMethodology" :icon="CopyDocument">复制方法学</el-button>
                             <el-button type="success" size="small" @click="exportResults">导出 Excel</el-button>
                        </div>
                    </div>
                </template>

                 <!-- Smart Interpretation Component -->
                 <InterpretationPanel
                    v-if="results.interpretation"
                    :interpretation="results.interpretation"
                 />
                 
                 <!-- Fallback or Additional Diagnostics -->


                <!-- Metrics -->
                <el-descriptions title="模型指标" :column="2" border size="small" style="margin-bottom: 20px">
                    <el-descriptions-item v-for="(val, key) in results.metrics" :key="key">
                        <template #label>
                            <div style="display: flex; align-items: center;">
                                <span>{{ key }}</span>
                                <el-tooltip v-if="metricTooltips[key]" :content="metricTooltips[key]" placement="top">
                                    <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </div>
                        </template>
                        {{ typeof val === 'number' ? val.toFixed(4) : val }}
                    </el-descriptions-item>
                </el-descriptions>

                <!-- Result Tabs -->
                <el-tabs type="border-card">
                    <el-tab-pane label="模型详情 (Details)">
                        <!-- ML Results (Importance) -->
                        <div v-if="results.importance">
                             <h3>特征重要性 (Feature Importance - SHAP)</h3>
                             <el-table :data="results.importance" style="width: 100%" height="400" stripe border size="small">
                                <el-table-column prop="feature" label="变量名" />
                                <el-table-column prop="importance" label="重要性 (SHAP mean)">
                                    <template #default="scope">
                                        <el-progress :percentage="Math.min(scope.row.importance * 100 / maxImportance, 100)" :show-text="false" />
                                        {{ scope.row.importance.toFixed(5) }}
                                    </template>
                                </el-table-column>
                             </el-table>
                        </div>

                        <!-- Statistical Summary Table -->
                        <el-table v-else :data="results.summary" style="width: 100%" height="400" stripe border size="small">
                            <el-table-column prop="variable" label="变量" />
                            <el-table-column prop="coef" label="系数 (Coef)">
                                <template #header>
                                     <span>系数 (Coef)</span>
                                     <el-tooltip content="正值代表正相关（风险增加），负值代表负相关（风险降低）" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">{{ scope.row.coef.toFixed(4) }}</template>
                            </el-table-column>
                            <el-table-column prop="p_value" label="P值">
                                <template #header>
                                     <span>P值</span>
                                     <el-tooltip content="P < 0.05 通常认为具有统计学显著意义" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    <span :style="{ fontWeight: scope.row.p_value < 0.05 ? 'bold' : 'normal', color: scope.row.p_value < 0.05 ? 'red' : 'inherit' }">
                                        {{ scope.row.p_value < 0.001 ? '<0.001' : typeof scope.row.p_value === 'number' ? scope.row.p_value.toFixed(4) : scope.row.p_value }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column v-if="config.model_type === 'logistic'" label="OR (95% CI)">
                                <template #header>
                                     <span>OR (95% CI)</span>
                                     <el-tooltip content="优势比 (Odds Ratio)。OR > 1 代表风险增加，CI 不包含 1 代表显著。" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    {{ scope.row.or.toFixed(2) }} ({{ scope.row.or_ci_lower.toFixed(2) }}-{{ scope.row.or_ci_upper.toFixed(2) }})
                                </template>
                            </el-table-column>
                            <el-table-column v-if="config.model_type === 'cox'" label="HR (95% CI)">
                                <template #header>
                                     <span>HR (95% CI)</span>
                                     <el-tooltip content="风险比 (Hazard Ratio)。HR > 1 代表风险增加，CI 不包含 1 代表显著。" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    {{ scope.row.hr.toFixed(2) }} ({{ scope.row.hr_ci_lower.toFixed(2) }}-{{ scope.row.hr_ci_upper.toFixed(2) }})
                                </template>
                            </el-table-column>
                            
                             <!-- Diagnostics -->
                            <el-table-column v-if="['linear', 'logistic'].includes(config.model_type)" prop="vif" label="VIF" width="80">
                                <template #header>
                                     <span>VIF</span>
                                     <el-tooltip content="方差膨胀因子。VIF > 5 提示可能存在多重共线性。" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                            </el-table-column>

                             <el-table-column v-if="config.model_type === 'cox'" prop="ph_test_p" label="PH Test P" width="100">
                                <template #header>
                                     <span>PH Test P</span>
                                     <el-tooltip content="PH 假设检验 P 值。P < 0.05 提示违反比例风险假设" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    <span :style="{ fontWeight: scope.row.ph_test_p < 0.05 ? 'bold' : 'normal', color: scope.row.ph_test_p < 0.05 ? 'red' : 'inherit' }">
                                         {{ scope.row.ph_test_p }}
                                    </span>
                                </template>
                             </el-table-column>
                        </el-table>
                    </el-tab-pane>

                    <el-tab-pane label="评估图表 (Clinical Eval)" v-if="config.model_type !== 'linear'">
                        
                        <!-- Time Selector for Survivor -->
                        <div v-if="availableTimePoints.length > 0" style="margin-bottom: 20px;">
                            <div style="display: flex; align-items: center; justify-content: flex-end; margin-bottom: 15px;">
                                <span style="font-size: 13px; color: #606266; margin-right: 10px;">预测时间点 (Time Point):</span>
                                <el-radio-group v-model="evaluationTimePoint" size="small">
                                    <el-radio-button v-for="t in availableTimePoints" :key="t" :value="t">{{ t }} (Months)</el-radio-button>
                                </el-radio-group>
                            </div>
                            
                            <!-- Extended Metrics Table -->
                            <el-descriptions v-if="currentExtendedMetrics" title="Discrimination & Calibration Metrics" :column="3" border size="small">
                                <el-descriptions-item label="Sensitivity (Recall)">
                                    {{ currentExtendedMetrics.sensitivity.toFixed(3) }}
                                    <span style="font-size: 10px; color: gray;">(at optimal cutoff)</span>
                                </el-descriptions-item>
                                <el-descriptions-item label="Specificity">
                                    {{ currentExtendedMetrics.specificity.toFixed(3) }}
                                </el-descriptions-item>
                                <el-descriptions-item label="Youden Index">
                                    {{ currentExtendedMetrics.youden_index.toFixed(3) }}
                                </el-descriptions-item>
                                <el-descriptions-item label="PPV (+Pred Val)">
                                    {{ currentExtendedMetrics.ppv.toFixed(3) }}
                                </el-descriptions-item>
                                <el-descriptions-item label="NPV (-Pred Val)">
                                    {{ currentExtendedMetrics.npv.toFixed(3) }}
                                </el-descriptions-item>
                                <el-descriptions-item label="Brier Score">
                                    {{ currentExtendedMetrics.brier_score.toFixed(3) }}
                                    <el-tag size="small" type="success" v-if="currentExtendedMetrics.brier_score < 0.25">Good</el-tag>
                                </el-descriptions-item>
                                <el-descriptions-item label="Optimal Cutoff">
                                    {{ currentExtendedMetrics.optimal_threshold.toFixed(3) }}
                                </el-descriptions-item>
                            </el-descriptions>
                        </div>
                        
                        <el-row :gutter="20">
                            <!-- ROC -->
                            <el-col :span="12" v-if="activePlots.roc" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="roc-plot"
                                    :title="config.model_type === 'cox' ? `Time-Dependent ROC (t=${evaluationTimePoint})` : 'ROC Curve'"
                                    :data="chartData.roc.data"
                                    :layout="chartData.roc.layout"
                                />
                            </el-col>
                            
                            <!-- Calibration -->
                            <el-col :span="12" v-if="activePlots.calibration" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="calibration-plot"
                                    :title="config.model_type === 'cox' ? `Calibration Plot (t=${evaluationTimePoint})` : 'Calibration Plot'"
                                    :data="chartData.calibration.data"
                                    :layout="chartData.calibration.layout"
                                />
                            </el-col>
                            
                            <!-- DCA -->
                             <el-col :span="12" v-if="activePlots.dca" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="dca-plot"
                                    :title="config.model_type === 'cox' ? `Decision Curve (DCA) (t=${evaluationTimePoint})` : 'Decision Curve (DCA)'"
                                    :data="chartData.dca.data"
                                    :layout="chartData.dca.layout"
                                />
                            </el-col>
                        </el-row>
                    </el-tab-pane>

                    <el-tab-pane label="列线图 (Nomogram)" v-if="nomogramData">
                         <el-alert title="简易列线图评分表 (Scorekeeper)" type="info" :closable="false" style="margin-bottom: 15px">
                             <div>
                                 列线图的本质是基于回归系数的线性加权求和。此处提供变量系数表，可用于构建个体化评分工具。
                                 <br/>
                                 <b>预测公式:</b> P = 1 / (1 + exp(-TotalScore)) [Logistic] 或 S(t) = S0(t)^exp(TotalScore) [Cox]
                             </div>
                         </el-alert>
                         
                         <!-- New Interactive Nomogram (Cox) -->
                         <div v-if="nomogramData.axes">
                              <NomogramVisualizer :spec="nomogramData" />
                         </div>
                         
                         <!-- Legacy/Simple Table (Logistic & Fallback) -->
                         <div v-else>
                             <!-- Intercept / Baseline (Cox) -->
                             <div v-if="nomogramData.intercept" style="margin-bottom: 10px;">
                                 <b>截距 (Intercept / Base Score):</b> {{ nomogramData.intercept.toFixed(4) }}
                             </div>
                             <div v-if="nomogramData.baseline_survival" style="margin-bottom: 10px;">
                                 <b>基线生存概率 (Baseline Survival S0(t)):</b>
                                 <span v-for="bs in nomogramData.baseline_survival.filter(x => availableTimePoints.includes(x[0]))" :key="bs[0]" style="margin-right: 15px">
                                     t={{ bs[0] }}: {{ bs[1].toFixed(4) }}
                                 </span>
                             </div>
                             
                             <el-table :data="nomogramData.vars" style="width: 100%" stripe border size="small">
                                 <el-table-column prop="name" label="变量 (Variable)" />
                                 <el-table-column prop="coef" label="系数/得分权重 (Coef)">
                                    <template #default="scope">
                                        {{ scope.row.coef.toFixed(4) }}
                                    </template>
                                 </el-table-column>
                                 <el-table-column :label="config.model_type === 'logistic' ? 'OR' : 'HR'">
                                    <template #default="scope">
                                        {{ scope.row.or ? scope.row.or.toFixed(3) : (scope.row.hr ? scope.row.hr.toFixed(3) : '-') }}
                                    </template>
                                 </el-table-column>
                             </el-table>
                         </div>
                    </el-tab-pane>

                    <el-tab-pane label="假设检验 (Assumptions)">
                         <!-- Multicollinearity (Linear/Logistic) -->
                         <div v-if="['linear', 'logistic'].includes(config.model_type)">
                            <h3>多重共线性 (Multicollinearity) - VIF</h3>
                            <p style="font-size: 13px; color: #666; margin-bottom: 15px;">
                                <strong>标准:</strong> VIF < 5 为理想，VIF > 10 提示严重共线性。
                            </p>
                            <InsightChart
                                chartId="vif-plot"
                                title="Multicollinearity (VIF)"
                                :data="chartData.vif.data"
                                :layout="chartData.vif.layout"
                            />
                         </div>
                         
                         <!-- PH Assumption (Cox) -->
                         <div v-if="config.model_type === 'cox'">
                             <h3>PH 等比例风险假设 (Proportional Hazards Assumption)</h3>
                             <p style="font-size: 13px; color: #666; margin-bottom: 15px;">
                                <strong>标准:</strong> P > 0.05 代表满足假设 (好)。P < 0.05 代表违反假设 (需注意)。
                            </p>
                            <el-table :data="results.summary" style="width: 100%" stripe border size="small">
                                <el-table-column prop="variable" label="变量" />
                                <el-table-column prop="ph_test_p" label="PH Test P-value">
                                    <template #default="scope">
                                        <el-tag :type="scope.row.ph_test_p >= 0.05 ? 'success' : 'danger'">
                                            {{ scope.row.ph_test_p }}
                                        </el-tag>
                                    </template>
                                </el-table-column>
                                <el-table-column label="结论">
                                    <template #default="scope">
                                        <span v-if="scope.row.ph_test_p >= 0.05" style="color: #67C23A">• 满足假设</span>
                                        <span v-else style="color: #F56C6C">• 违反假设 (可能随时变)</span>
                                    </template>
                                </el-table-column>
                            </el-table>
                         </div>
                    </el-tab-pane>
                </el-tabs>
           </el-card>
       </el-col>
    </el-row>

    <!-- Comparison Dialog -->
    <el-dialog v-model="showComparisonDialog" title="模型对比分析 (Model Comparison Report)" width="70%">
        <div v-if="comparisonMetrics">
            <h3>1. 基本拟合指标对比 (Model Fit Statistics)</h3>
            <el-table :data="[comparisonMetrics.basic.c_index, comparisonMetrics.basic.aic, comparisonMetrics.basic.bic, comparisonMetrics.basic.ll]" border size="small" stripe>
                <el-table-column label="指标 (Metric)">
                    <template #default="scope">
                        <span v-if="scope.$index === 0"><b>C-index</b> (Higher is better)</span>
                        <span v-if="scope.$index === 1"><b>AIC</b> (Lower is better)</span>
                        <span v-if="scope.$index === 2"><b>BIC</b> (Lower is better)</span>
                        <span v-if="scope.$index === 3"><b>Log-Likelihood</b> (Higher is better)</span>
                    </template>
                </el-table-column>
                <el-table-column :label="'Baseline (Model 1)'" prop="m1">
                    <template #default="scope">{{ scope.row.m1.toFixed(3) }}</template>
                </el-table-column>
                <el-table-column :label="'Current (Model 2)'" prop="m2">
                    <template #default="scope">{{ scope.row.m2.toFixed(3) }}</template>
                </el-table-column>
                <el-table-column label="差异 (Difference)" prop="diff">
                    <template #default="scope">
                        <span :style="{ fontWeight: 'bold', color: scope.row.diff > 0 ? (scope.$index === 1 || scope.$index === 2 ? 'red' : 'green') : (scope.$index === 1 || scope.$index === 2 ? 'green' : 'red') }">
                            {{ scope.row.diff > 0 ? '+' : '' }}{{ scope.row.diff.toFixed(3) }}
                        </span>
                        
                        <!-- Auto Interpretation Tags -->
                        <el-tag size="small" type="success" style="margin-left: 10px" v-if="scope.$index === 0 && scope.row.diff > 0.01">Improved</el-tag>
                        <el-tag size="small" type="success" style="margin-left: 10px" v-if="(scope.$index === 1 || scope.$index === 2) && scope.row.diff < -2">Improved</el-tag>
                    </template>
                </el-table-column>
            </el-table>
            
            <h3 style="margin-top: 20px">2. 改善与增量价值 (Reclassification & Incremental Value)</h3>
            <div v-if="comparisonMetrics.reclassification">
                <el-alert type="info" :closable="false" style="margin-bottom: 10px">
                    基于预测时间点 T = {{ comparisonMetrics.reclassification.time_point }} (Months) 计算。
                    反映了加入新变量后，模型对个体风险分类的改善程度。
                </el-alert>
                <el-descriptions :column="2" border>
                    <el-descriptions-item label="NRI (连续净重分类改善指数)">
                        <span style="font-size: 16px; font-weight: bold">{{ comparisonMetrics.reclassification.nri.toFixed(4) }}</span>
                        <div style="font-size: 12px; color: gray; margin-top: 4px">
                            Interpretation: NRI > 0 意味着模型正确地将发生事件者归为更高风险，或将未发生者归为更低风险。
                        </div>
                    </el-descriptions-item>
                    <el-descriptions-item label="IDI (综合判别改善指数)">
                        <span style="font-size: 16px; font-weight: bold">{{ comparisonMetrics.reclassification.idi.toFixed(4) }}</span>
                        <div style="font-size: 12px; color: gray; margin-top: 4px">
                            Interpretation: IDI > 0 意味着新模型提高了平均预测概率的区分度。
                        </div>
                    </el-descriptions-item>
                </el-descriptions>
            </div>
            <div v-else>
                <el-alert type="warning" :closable="false" title="无法计算 NRI/IDI">
                     可能是因为两个模型选择的评估时间点不一致，或未能匹配到相同的样本。请确保在相同的筛选条件下运行模型。
                </el-alert>
            </div>
        </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * ModelingTab.vue
 * 核心建模与评估主组件。
 * 
 * 职责：
 * 1. 提供多种统计/机器学习模型的配置界面（线性、逻辑、Cox、随机森林、XGBoost）。
 * 2. 调度后端建模服务并展示详细的模型参数（Coef, P-value, OR, HR）。
 * 3. 实现“智能解读”逻辑，将数值指标转化为医学研究可理解的文字结论。
 * 4. 渲染并集成 Plotly 图表进行模型评估（ROC, 校准曲线, DCA等）。
 */
import { ref, computed, watch, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'
import InterpretationPanel from './InterpretationPanel.vue'


import InsightChart from './InsightChart.vue'
import NomogramVisualizer from './NomogramVisualizer.vue'

import { QuestionFilled, ArrowDown, Setting, CopyDocument, MagicStick } from '@element-plus/icons-vue'

const props = defineProps({
    projectId: { type: String, required: true },
    datasetId: { type: Number, default: null },
    metadata: { type: Object, default: null }
})

const loading = ref(false)
const results = ref(null)



const maxImportance = computed(() => {
    if (!results.value || !results.value.importance) return 1
    return Math.max(...results.value.importance.map(i => i.importance))
})

const metricTooltips = {
    'accuracy': '准确率：模型预测正确的样本占总样本的比例。',
    'auc': 'ROC曲线下面积：衡量二分类模型好坏，越接近1越好。0.5代表随机猜测。',
    'recall': '召回率：所有正例中被正确预测为正例的比例。',
    'f1': 'F1分数：精确率和召回率的调和平均数，综合衡量指标。',
    'r2': 'R平方：决定系数，表示模型解释了因变量方差的百分比。越接近1拟合越好。',
    'rmse': '均方根误差：预测值与真实值偏差的样本标准差。越小越好。',
    'cv_auc_mean': '5折交叉验证平均AUC：模型在未见数据上的平均表现，评估泛化能力。',
    'cv_auc_std': '5折交叉验证AUC标准差：评估模型表现的稳定性，值越小越稳定。',
    'aic': '赤池信息量：衡量模型拟合优度与参数复杂度的平衡，越小代表模型越精简有效。',
    'bic': '贝叶斯信息量：类似AIC，但对参数数量惩罚更重，常用于模型筛选，越小越好。',
    'c_index': '一致性指数：生存分析核心指标，衡量模型预测风险等级的准确性，越接近1越好。',
    'log_likelihood': 'Log-Likelihood (对数似然): 越高越好，表示模型对数据的解释程度。',
    'n_events': 'Event Count (事件数): 分析中观察到的终点事件总数。'
}

const modelOptions = [
    { label: '线性回归 (Linear Regression, OLS)', value: 'linear' },
    { label: '逻辑回归 (Logistic Regression)', value: 'logistic' },
    { label: 'Cox 比例风险回归 (Cox Proportional Hazards)', value: 'cox' },
    { label: '随机森林 (Random Forest)', value: 'random_forest' },
    { label: 'XGBoost', value: 'xgboost' }
]

const config = reactive({
    model_type: 'logistic',
    target: null, 
    features: [],
    ref_levels: {}, // { 'Sex': 'Female' }
    model_params: {
        n_estimators: 100,
        max_depth: null,
        learning_rate: 0.1
    }
})



const autoSuggestRoles = async () => {
    if (!props.datasetId) return
    
    // Check if configuration is already set by user? 
    // Usually we only auto-suggest if empty or explicitly requested.
    // But here we just overwrite or fill.
    
    try {
        const { data } = await api.post('/statistics/recommend-model', {
            dataset_id: props.datasetId
        })
        const rec = data.recommendation
        
        // Apply Recommendation
        config.model_type = rec.model_type
        
        if (rec.model_type === 'cox') {
            config.target = {
                time: rec.target.time,
                event: rec.target.event
            }
        } else {
            config.target = rec.target
        }
        
        config.features = rec.features
        
        ElMessage.success(`智能推荐: 检测到适合 ${rec.model_type} 模型`)
        if (rec.reason) {
            // Optional: nice notification
            setTimeout(() => {
                 ElMessage.info({
                    message: rec.reason,
                    duration: 5000,
                    showClose: true
                 })
            }, 500)
        }
        
    } catch (e) {
        console.error("Recommendation failed", e)
        // Fallback to simple default if backend fails?
        // Or just do nothing.
    }
}

// Collinearity Check Logic
let collinearityTimer = null
const checkingCollinearity = ref(false)
const collinearityWarning = ref(null)

const checkCollinearity = async () => {
    collinearityWarning.value = null
    if (config.features.length < 2) return
    
    checkingCollinearity.value = true
    try {
        const { data } = await api.post('/statistics/check-collinearity', {
            dataset_id: props.datasetId,
            features: config.features
        })
        
        if (data.status !== 'ok') {
            // Show persistent warning
            const first = data.report[0]
            collinearityWarning.value = `检测到共线性风险: ${first.message} (VIF=${first.vif.toFixed(1)})。建议移除该变量。`
        }
    } catch (e) {
        console.error("Collinearity check failed", e)
    } finally {
        checkingCollinearity.value = false
    }
}

watch(() => config.features, (newVal) => {
    collinearityWarning.value = null
    if (collinearityTimer) clearTimeout(collinearityTimer)
    collinearityTimer = setTimeout(() => {
        checkCollinearity()
    }, 1000) // Debounce 1s
})

const variableOptions = computed(() => {
    if (!props.metadata) return []
    return props.metadata.variables.map(v => {
        // Find health status
        const h = varHealthMap.value[v.name]
        return { 
            label: v.name, 
            value: v.name,
            type: v.type, // Added type for filtering
            status: h ? h.status : 'unknown',
            msg: h ? h.message : ''
        }
    })
})

const targetOptions = computed(() => {
    // For Linear Regression, Target must be numeric (continuous)
    if (config.model_type === 'linear') {
        return variableOptions.value.map(v => ({
            ...v,
            disabled: !['continuous', 'float', 'int'].includes(v.type)
        }))
    }
    return variableOptions.value
})

const varHealthMap = ref({})

const fetchHealthStatus = async () => {
    if (!props.metadata || !props.datasetId) return
    const allVars = props.metadata.variables.map(v => v.name)
    try {
        const { data } = await api.post('/statistics/check-health', {
            dataset_id: props.datasetId,
            variables: allVars
        })
        // Map to object
        const map = {}
        data.report.forEach(item => {
            map[item.variable] = item
        })
        varHealthMap.value = map
    } catch (e) {
        console.error("Health fetch failed", e)
    }
}

// Auto-trigger when metadata loads for the first time
watch(() => props.metadata, (newVal) => {
    if (newVal) {
        fetchHealthStatus()
        
        if (!config.target || !config.target.time) {
            // Only run if empty
            autoSuggestRoles()
        }
    }
}, { immediate: true })

const topResult = computed(() => {
    if (!results.value || !results.value.summary) return null
    
    // Find most significant variable
    const sigVars = results.value.summary.filter(v => v.p_value < 0.05)
    if (sigVars.length === 0) return null
    
    let top = null
    const type = config.model_type
    
    // Logic to pick "best" one
    if (type === 'logistic') {
        top = sigVars.reduce((prev, curr) => curr.or > prev.or ? curr : prev, sigVars[0])
    } else if (type === 'cox') {
         top = sigVars.reduce((prev, curr) => curr.hr > prev.hr ? curr : prev, sigVars[0])
    } else {
         top = sigVars.reduce((prev, curr) => Math.abs(curr.coef) > Math.abs(prev.coef) ? curr : prev, sigVars[0])
    }
    
    if (!top) return null
    
    let effect = null
    if (type === 'logistic') effect = top.or
    else if (type === 'cox') effect = top.hr
    
    return {
        p_value: top.p_value,
        effectSize: effect,
        desc: `变量 **${top.variable}** 对结果影响最为显著。`
    }
})



const runModel = async () => {
    if (!props.datasetId) return
    loading.value = true
    try {
        const { data } = await api.post('/modeling/run', {
            project_id: props.projectId,
            dataset_id: props.datasetId,
            ...config
        })
        if (data.results.status === 'failed') {
            results.value = null // Clear previous good results
            // Show diagnositic error
            ElMessage({
                message: data.results.message,
                type: 'error',
                duration: 10000,
                showClose: true,
                grouping: true
            })
            // Optionally, we could set a reactive 'errorState' to show a persistent alert in UI
            // But for now, a long duration Toast is consistent with user request "Give me a hint".
            return 
        }
        
        results.value = data.results
        ElMessage.success('模型运行成功')
        
        // Charts are rendered reactively via activePlots watcher
    } catch (error) {
        ElMessage.error(error.response?.data?.message || '模型运行失败')
    } finally {
        loading.value = false
    }
}

// --- Clinical Evaluation Logic ---
const evaluationTimePoint = ref(null)

const availableTimePoints = computed(() => {
    if (!results.value || !results.value.clinical_eval || !results.value.clinical_eval.dca) return []
    // Get keys (time points)
    const keys = Object.keys(results.value.clinical_eval.dca).map(Number).sort((a,b) => a-b)
    return keys
})

// Set default time point when results change
watch(() => results.value, (val) => {
    if (val && val.clinical_eval && val.clinical_eval.dca) {
        const keys = Object.keys(val.clinical_eval.dca).map(Number).sort((a,b) => a-b)
        if (keys.length > 0) evaluationTimePoint.value = keys[0]
    }
})

const currentExtendedMetrics = computed(() => {
    if (!results.value || !results.value.clinical_eval || !results.value.clinical_eval.extended_metrics) return null
    if (evaluationTimePoint.value === null) return null
    return results.value.clinical_eval.extended_metrics[evaluationTimePoint.value]
})

const activePlots = computed(() => {
    if (!results.value) return {}
    
    // 1. Cox Time-Dependent
    if (config.model_type === 'cox' && results.value.clinical_eval) {
        const t = evaluationTimePoint.value
        if (!t) return {}
        return {
            roc: results.value.clinical_eval.roc[t],
            dca: results.value.clinical_eval.dca[t],
            calibration: results.value.clinical_eval.calibration[t]
        }
    }
    
    // 2. Logistic / Standard
    if (results.value.plots) {
        return results.value.plots
    }
    
    return {}
})

// Auto-render when plots change (Time switch or New Model)
watch(activePlots, (plots) => {
    if (plots) renderEvaluationPlots(plots)
}, { deep: true })

const nomogramData = computed(() => {
    if (!results.value) return null
    // Logistic
    if (config.model_type === 'logistic' && results.value.plots && results.value.plots.nomogram) {
        return results.value.plots.nomogram
    }
    // Cox
    if (config.model_type === 'cox' && results.value.clinical_eval && results.value.clinical_eval.nomogram) {
        return results.value.clinical_eval.nomogram
    }
    return null
})

const selectedCategoricalVars = computed(() => {
    if (!props.metadata || !config.features || config.features.length === 0) return []
    return props.metadata.variables.filter(v => 
        config.features.includes(v.name) && 
        v.type === 'categorical' && 
        v.categories && v.categories.length > 0
    )
})

const copyMethodology = () => {
    // Generate text from backend
    if (!results.value || !results.value.methodology) {
         ElMessage.info('暂无方法学内容')
         return
    }
    const text = results.value.methodology
    navigator.clipboard.writeText(text).then(() => {
        ElMessage.success('方法学段落已复制到剪贴板')
    }).catch(err => {
        ElMessage.error('复制失败')
    })
}

const chartData = reactive({
    roc: { data: [], layout: {} },
    calibration: { data: [], layout: {} },
    dca: { data: [], layout: {} },
    vif: { data: [], layout: {} }
})

const renderEvaluationPlots = (plots) => {
    // ROC Curve
    if (plots.roc) {
        chartData.roc.data = [
            {
                x: plots.roc.fpr,
                y: plots.roc.tpr,
                mode: 'lines',
                name: `AUC = ${plots.roc.auc.toFixed(3)}`,
                line: { color: 'blue' }
            },
            {
                x: [0, 1], y: [0, 1],
                mode: 'lines',
                name: 'Random',
                line: { dash: 'dash', color: 'gray' }
            }
        ]
        chartData.roc.layout = {
            xaxis: { title: 'False Positive Rate' },
            yaxis: { title: 'True Positive Rate' }
        }
    }

    // Calibration Curve
    if (plots.calibration) {
        chartData.calibration.data = [
            {
                x: plots.calibration.prob_pred,
                y: plots.calibration.prob_true,
                mode: 'lines+markers',
                name: 'Model',
                line: { color: 'red' }
            },
            {
                x: [0, 1], y: [0, 1],
                mode: 'lines',
                name: 'Perfectly Calibrated',
                line: { dash: 'dash', color: 'gray' }
            }
        ]
        chartData.calibration.layout = {
            xaxis: { title: 'Mean Predicted Probability', range: [0, 1] },
            yaxis: { title: 'Fraction of Positives', range: [0, 1] }
        }
    }

    // DCA Plot
    if (plots.dca) {
        const maxY = Math.max(...plots.dca.net_benefit_model, ...plots.dca.net_benefit_all)
        chartData.dca.data = [
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_model,
                mode: 'lines',
                name: 'Model',
                line: { color: 'red', width: 2 }
            },
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_all,
                mode: 'lines',
                name: 'Treat All',
                line: { color: 'gray', dash: 'dash' }
            },
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_none,
                mode: 'lines',
                name: 'Treat None',
                line: { color: 'black' }
            }
        ]
        chartData.dca.layout = {
            xaxis: { title: 'Threshold Probability', range: [0, 1] },
            yaxis: { title: 'Net Benefit', range: [-0.05, maxY + 0.05] }
        }
    }

    // VIF Plot
    if (plots.vif) {
        chartData.vif.data = [{
            x: plots.vif.variables,
            y: plots.vif.vif_values,
            type: 'bar',
            marker: {
                color: plots.vif.vif_values.map(v => v > 5 ? 'red' : '#409EFF')
            }
        }]
        chartData.vif.layout = {
             title: 'VIF Values',
             shapes: [{
                type: 'line',
                x0: -0.5, x1: plots.vif.variables.length - 0.5,
                y0: 5, y1: 5,
                line: { color: 'red', width: 2, dash: 'dash' }
             }]
        }
    }
}

const exportResults = async () => {
     try {
        const { data } = await api.post('/modeling/export', {
            project_id: props.projectId,
            dataset_id: props.datasetId,
            ...config
        })
        window.open(data.download_url, '_blank')
        ElMessage.success('导出成功')
    } catch (error) {
        ElMessage.error('导出失败')
    }
}

// Removed downloadPlot function as it is now handled by InsightChart component
// const downloadPlot = async (divId, filename, format = 'png') => { ... }

// --- Model Comparison Logic ---
const baselineResult = ref(null)
const showComparisonDialog = ref(false)
const comparisonMetrics = ref(null)

const setAsBaseline = () => {
    if (!results.value) return
    baselineResult.value = JSON.parse(JSON.stringify(results.value))
    ElMessage.success('当前模型已设为基线 (Model 1)')
}

const calculateNRI_IDI = (y_true, p_old, p_new) => {
    let up_event = 0, down_event = 0, n_event = 0;
    let up_nonevent = 0, down_nonevent = 0, n_nonevent = 0;
    let idi_event_sum = 0, idi_nonevent_sum = 0;

    for (let i = 0; i < y_true.length; i++) {
        const diff = p_new[i] - p_old[i];
        if (y_true[i] === 1) {
            n_event++;
            if (p_new[i] > p_old[i]) up_event++;
            if (p_new[i] < p_old[i]) down_event++;
            idi_event_sum += diff;
        } else {
            n_nonevent++;
            if (p_new[i] < p_old[i]) down_nonevent++; // Better for non-event
            if (p_new[i] > p_old[i]) up_nonevent++;   // Worse
            idi_nonevent_sum += diff;
        }
    }

    if (n_event === 0 || n_nonevent === 0) return { nri: 0, idi: 0 };

    const nri_event = (up_event - down_event) / n_event;
    const nri_nonevent = (down_nonevent - up_nonevent) / n_nonevent;
    const nri = nri_event + nri_nonevent;

    const idi = (idi_event_sum / n_event) - (idi_nonevent_sum / n_nonevent);
    
    return { nri, idi };
}

const compareWithBaseline = () => {
    if (!baselineResult.value || !results.value) return;

    const m1 = baselineResult.value.metrics;
    const m2 = results.value.metrics;
    
    // Safety check for keys
    const getVal = (m, k) => m && m[k] !== undefined ? parseFloat(m[k]) : 0;

    const cmp = {
        models: {
            m1_name: 'Baseline (Model 1)',
            m2_name: 'Current (Model 2)'
        },
        basic: {
            c_index: { m1: getVal(m1, 'c_index'), m2: getVal(m2, 'c_index'), diff: getVal(m2, 'c_index') - getVal(m1, 'c_index') },
            aic: { m1: getVal(m1, 'aic'), m2: getVal(m2, 'aic'), diff: getVal(m2, 'aic') - getVal(m1, 'aic') },
            bic: { m1: getVal(m1, 'bic'), m2: getVal(m2, 'bic'), diff: getVal(m2, 'bic') - getVal(m1, 'bic') },
            ll: { m1: getVal(m1, 'log_likelihood'), m2: getVal(m2, 'log_likelihood'), diff: getVal(m2, 'log_likelihood') - getVal(m1, 'log_likelihood') }
        },
        reclassification: null
    }
    
    // NRI / IDI
    const t = evaluationTimePoint.value;
    if (t && baselineResult.value.clinical_eval && results.value.clinical_eval) {
         const pred1 = baselineResult.value.clinical_eval.predictions?.[t];
         const pred2 = results.value.clinical_eval.predictions?.[t];
         
         if (pred1 && pred2) {
             // Validate lengths
             if (pred1.y_true.length === pred2.y_true.length) {
                 const res = calculateNRI_IDI(pred1.y_true, pred1.y_pred, pred2.y_pred);
                 cmp.reclassification = {
                     time_point: t,
                     nri: res.nri,
                     idi: res.idi
                 };
             }
         }
    }
    
    comparisonMetrics.value = cmp;
    showComparisonDialog.value = true;
}
</script>



<style scoped>
.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    font-weight: bold;
    color: #606266;
}
</style>
