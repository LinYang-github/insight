<template>
  <div v-if="!datasetId">
      <el-empty description="请先上传数据" />
  </div>
  <div v-else>
    <el-row :gutter="20">
       <el-col :span="8">
           <el-card shadow="hover">
               <template #header>
                   <div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-weight: bold; border-left: 4px solid #3b71ca; padding-left: 10px;">模型配置</span><el-button type="primary" size="small" class="ai-suggest-btn" :loading="isSuggesting" @click="autoSuggestRoles" :icon="MagicStick">{{ isSuggesting ? 'AI 正在分析变量...' : 'AI 智能角色推荐' }}</el-button></div>
               </template>
               <el-form label-position="top">
                    <div v-if="isSuggesting" style="margin-bottom: 20px;"><el-alert title="AI 助手正在分析变量..." type="info" show-icon :closable="false" /></div>
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
                                    <span v-if="opt.disabled" style="color: #ccc">{{ opt.label }} (非数值型)</span>
                                    <span v-else>{{ opt.label }}</span>
                               </el-option>
                           </el-select>
                       </template>
                       <template v-else>
                           <el-row :gutter="10">
                               <el-col :span="12">
                                   <el-select v-model="coxTarget.time" placeholder="时间变量 (Time)" filterable @change="syncCoxTarget">
                                       <el-option v-for="opt in timeOptions" :disabled="opt.disabled" :key="opt.value" :label="opt.label" :value="opt.value" />
                                   </el-select>
                               </el-col>
                               <el-col :span="12">
                                   <el-select v-model="coxTarget.event" placeholder="事件变量 (Event)" filterable @change="syncCoxTarget">
                                       <el-option v-for="opt in eventOptions" :disabled="opt.disabled" :key="opt.value" :label="opt.label" :value="opt.value" />
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
                           <el-option v-for="opt in featureOptions" :key="opt.value" :label="opt.label" :value="opt.value" :disabled="opt.disabled">
                               <div style="display: flex; justify-content: space-between; align-items: center;">
                                   <span>{{ opt.label }}<el-tag v-if="aiSuggestedFeatures.includes(opt.value)" size="small" type="success" effect="plain" style="margin-left: 5px; transform: scale(0.7); vertical-align: middle;">AI</el-tag></span>
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
                       
                       <!-- Variable Selection Tool -->
                       <div style="margin-top: 10px; display: flex; justify-content: flex-end;">
                           <el-button 
                               type="primary" 
                               plain 
                               size="small" 
                               :icon="Filter"
                               @click="showSelectionDialog = true"
                               :disabled="!isTargetSet || config.features.length < 2"
                           >
                               变量筛选 (Stepwise/LASSO)
                           </el-button>
                       </div>
                       
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
                                    <span style="font-size: 12px; color: #606266; display: block; margin-bottom: 4px;">{{ v.name }} 基准组:</span>
                                    <el-select v-model="config.ref_levels[v.name]" placeholder="默认 (第一组)" size="small" style="width: 100%">
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
                                     <el-input-number v-model="config.model_params.max_depth" :min="1" :max="50" size="small" placeholder="无限制" style="width: 100%"/>
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
       
       <el-col :span="16">
            <div v-if="results">
                <el-card shadow="hover">
                <template #header>
                    <AnalysisHeader title="分析结果与临床洞察">
                        <template #actions>
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
                             
                             <el-button 
                                 type="primary" 
                                 size="small" 
                                 @click="runAIInterpretation" 
                                 :loading="isInterpreting"
                                 :icon="MagicStick"
                                 class="ai-interpret-btn"
                             >
                                 AI 深度解读
                             </el-button>
                             <el-button type="info" plain size="small" @click="copyMethodology" :icon="CopyDocument">复制方法学</el-button>
                             <el-button v-if="results" type="success" size="small" @click="exportResults">导出 Excel</el-button>
                        </template>
                    </AnalysisHeader>
                </template>

                  <!-- PH Violation Warning -->
                  <el-alert
                    v-if="config.model_type === 'cox' && results.metrics?.ph_global_p !== undefined && results.metrics?.ph_global_p !== null && results.metrics?.ph_global_p < 0.05"
                    title="违反比例风险 (PH) 假定"
                    type="error"
                    show-icon
                    :closable="false"
                    style="margin-bottom: 20px"
                  >
                    <template #default>
                        <div style="font-size: 13px; line-height: 1.6;">
                            当前模型的全局 PH 检验 P 值为 <b>{{ typeof results.metrics.ph_global_p === 'number' ? results.metrics.ph_global_p.toFixed(4) : results.metrics.ph_global_p }}</b>，提示可能违反了 Cox 模型的比例风险假定。
                            建议在下方“假设检验”标签页中检查各变量的具体表现。
                        </div>
                    </template>
                  </el-alert>
                  
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
                                <span>{{ key === 'ph_global_p' ? '全局 PH 检验 P 值' : key }}</span>
                                <el-tooltip v-if="metricTooltips[key]" :content="metricTooltips[key]" placement="top">
                                    <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                </el-tooltip>
                            </div>
                        </template>
                        <span :style="{ color: key === 'ph_global_p' && val < 0.05 ? 'red' : 'inherit', fontWeight: key === 'ph_global_p' && val < 0.05 ? 'bold' : 'normal' }">
                            {{ typeof val === 'number' ? val.toFixed(4) : val }}
                        </span>
                    </el-descriptions-item>
                </el-descriptions>

                <!-- Result Tabs -->
                <el-tabs v-model="activeResultTab" type="border-card">
                    <el-tab-pane label="模型详情 (Details)" name="details">
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
                        <PublicationTable v-else :data="results.summary" style="width: 100%" height="400">
                            <el-table-column prop="variable" label="变量" />
                            <el-table-column prop="coef" label="系数 (Coef)">
                                <template #header>
                                     <span>系数 (Coef)</span>
                                     <el-tooltip content="回归系数 (Regression Coefficient)" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">{{ formatNumber(scope.row.coef, 3) }}</template>
                            </el-table-column>
                            <el-table-column prop="p_value" label="P值">
                                <template #header>
                                     <span>P值</span>
                                     <el-tooltip content="显著性检验 P 值 (Significance Level)" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    <span :style="{ fontWeight: scope.row.p_value < 0.05 ? 'bold' : 'normal', color: scope.row.p_value < 0.05 ? 'red' : 'inherit' }">
                                        {{ formatPValue(scope.row.p_value) }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column v-if="config.model_type === 'logistic'" label="OR (95% CI)">
                                <template #header>
                                     <span>OR (95% CI)</span>
                                     <el-tooltip content="优势比 (Odds Ratio)" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    {{ formatEffectSize(scope.row.or, scope.row.or_ci_lower, scope.row.or_ci_upper) }}
                                </template>
                            </el-table-column>
                            <el-table-column v-if="config.model_type === 'cox'" label="HR (95% CI)">
                                <template #header>
                                     <span>HR (95% CI)</span>
                                     <el-tooltip content="风险比 (Hazard Ratio)" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    {{ formatEffectSize(scope.row.hr, scope.row.hr_ci_lower, scope.row.hr_ci_upper) }}
                                </template>
                            </el-table-column>
                            
                             <!-- 诊断指标 -->
                            <el-table-column v-if="['linear', 'logistic'].includes(config.model_type)" prop="vif" label="VIF" width="80">
                                <template #header>
                                     <span>VIF</span>
                                     <el-tooltip content="方差膨胀因子 (Variance Inflation Factor)" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                            </el-table-column>

                             <el-table-column v-if="config.model_type === 'cox'" prop="ph_test_p" label="PH Test P" width="100">
                                <template #header>
                                     <span>PH Test P</span>
                                     <el-tooltip content="比例风险假定检验 P 值 (Schoenfeld Residuals Test)" placement="top">
                                        <el-icon style="margin-left: 4px"><QuestionFilled /></el-icon>
                                     </el-tooltip>
                                </template>
                                <template #default="scope">
                                    <span :style="{ fontWeight: scope.row.ph_test_p < 0.05 ? 'bold' : 'normal', color: scope.row.ph_test_p < 0.05 ? 'red' : 'inherit' }">
                                         {{ scope.row.ph_test_p }}
                                    </span>
                                </template>
                             </el-table-column>
                        </PublicationTable>
                    </el-tab-pane>

                    <el-tab-pane label="评估图表 (Clinical Eval)" name="clinical" v-if="config.model_type !== 'linear'">
                        
                        <!-- Time Selector for Survivor -->
                        <div v-if="availableTimePoints.length > 0" style="margin-bottom: 20px;">
                            <div style="display: flex; align-items: center; justify-content: flex-end; margin-bottom: 15px;">
                                <span style="font-size: 13px; color: #606266; margin-right: 10px;">预测时间点 (Time Point):</span>
                                <el-radio-group v-model="evaluationTimePoint" size="small">
                                    <el-radio-button v-for="t in availableTimePoints" :key="t" :value="t">
                                        {{ t }} ({{ results.clinical_eval?.time_unit === 'days' ? '天' : '月' }})
                                    </el-radio-button>
                                </el-radio-group>
                            </div>
                            
                            <el-descriptions v-if="currentExtendedMetrics" title="鉴别度与校准度指标 (Discrimination & Calibration)" :column="2" border size="small">
                                <el-descriptions-item>
                                    <template #label>
                                        AUC / C-Index
                                        <el-tooltip content="ROC 曲线下面积。反映模型的整体区分能力 (0.5=随机, 1.0=完美)。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                                    </template>
                                    <template v-if="currentExtendedMetrics.auc !== undefined">
                                        <b>{{ currentExtendedMetrics.auc.toFixed(3) }}</b>
                                        <div style="font-size: 11px; color: gray;">
                                            ({{ currentExtendedMetrics.auc_ci_lower.toFixed(3) }} - {{ currentExtendedMetrics.auc_ci_upper.toFixed(3) }})
                                        </div>
                                    </template>
                                    <span v-else>-</span>
                                </el-descriptions-item>
                                <el-descriptions-item label="Youden Index">
                                    {{ currentExtendedMetrics.youden_index.toFixed(3) }}
                                </el-descriptions-item>
                                <el-descriptions-item>
                                    <template #label>
                                        灵敏度 (Sensitivity)
                                        <el-tooltip content="真阳性率。模型识别出真正患者的能力。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                                    </template>
                                    {{ currentExtendedMetrics.sensitivity.toFixed(3) }}
                                    <div style="font-size: 11px; color: gray;" v-if="currentExtendedMetrics.sensitivity_ci_lower !== undefined">
                                        ({{ currentExtendedMetrics.sensitivity_ci_lower.toFixed(3) }} - {{ currentExtendedMetrics.sensitivity_ci_upper.toFixed(3) }})
                                    </div>
                                </el-descriptions-item>
                                <el-descriptions-item>
                                    <template #label>
                                        特异度 (Specificity)
                                        <el-tooltip content="真阴性率。模型排除非患者的能力。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                                    </template>
                                    {{ currentExtendedMetrics.specificity.toFixed(3) }}
                                    <div style="font-size: 11px; color: gray;" v-if="currentExtendedMetrics.specificity_ci_lower !== undefined">
                                        ({{ currentExtendedMetrics.specificity_ci_lower.toFixed(3) }} - {{ currentExtendedMetrics.specificity_ci_upper.toFixed(3) }})
                                    </div>
                                </el-descriptions-item>
                                <el-descriptions-item>
                                    <template #label>
                                        阳性预测值 (PPV)
                                        <el-tooltip content="预测为阳性中真正为阳性的比例。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                                    </template>
                                    {{ currentExtendedMetrics.ppv.toFixed(3) }}
                                    <div style="font-size: 11px; color: gray;" v-if="currentExtendedMetrics.ppv_ci_lower !== undefined">
                                        ({{ currentExtendedMetrics.ppv_ci_lower.toFixed(3) }} - {{ currentExtendedMetrics.ppv_ci_upper.toFixed(3) }})
                                    </div>
                                </el-descriptions-item>
                                <el-descriptions-item>
                                    <template #label>
                                        阴性预测值 (NPV)
                                        <el-tooltip content="预测为阴性中真正为阴性的比例。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                                    </template>
                                    {{ currentExtendedMetrics.npv.toFixed(3) }}
                                    <div style="font-size: 11px; color: gray;" v-if="currentExtendedMetrics.npv_ci_lower !== undefined">
                                        ({{ currentExtendedMetrics.npv_ci_lower.toFixed(3) }} - {{ currentExtendedMetrics.npv_ci_upper.toFixed(3) }})
                                    </div>
                                </el-descriptions-item>
                                <el-descriptions-item>
                                    <template #label>
                                        Brier 分数 (Brier Score)
                                        <el-tooltip content="预测概率与实际结果的均方误差。越低越好 (< 0.25)。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                                    </template>
                                    {{ currentExtendedMetrics.brier_score.toFixed(3) }}
                                    <el-tag size="small" type="success" v-if="currentExtendedMetrics.brier_score < 0.25">Good</el-tag>
                                </el-descriptions-item>
                                <el-descriptions-item label="最佳截断值 (Optimal Cutoff)">
                                    {{ currentExtendedMetrics.optimal_threshold.toFixed(3) }}
                                </el-descriptions-item>
                                <el-descriptions-item>
                                    <template #label>
                                        有效样本量 (Events)
                                        <el-tooltip content="参与评估的有效样本数（已排除此处删失者）及其中发生的终点事件数。" placement="top"><el-icon><QuestionFilled /></el-icon></el-tooltip>
                                    </template>
                                    <template v-if="currentExtendedMetrics.n_eval && currentExtendedMetrics.n_events !== undefined">
                                        {{ currentExtendedMetrics.n_eval }} 
                                        <span style="margin-left:5px; color: #E6A23C; font-weight: 500">(事件数: {{ currentExtendedMetrics.n_events }})</span>
                                    </template>
                                    <span v-else>-</span>
                                </el-descriptions-item>
                            </el-descriptions>
                        </div>
                        
                        <el-row :gutter="20">
                            <!-- ROC -->
                            <el-col :span="12" v-if="activePlots.roc" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="roc-plot"
                                    :title="config.model_type === 'cox' ? `ROC 曲线 (t=${evaluationTimePoint})` : 'ROC 曲线 (ROC Curve)'"
                                    :data="chartData.roc.data"
                                    :layout="chartData.roc.layout"
                                    :publicationReady="uiStore.isAcademicMode"
                                />
                            </el-col>
                            
                            <!-- Calibration -->
                            <el-col :span="12" v-if="activePlots.calibration" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="calibration-plot"
                                    :title="config.model_type === 'cox' ? `校准曲线 (Calibration) (t=${evaluationTimePoint})` : '校准曲线 (Calibration)'"
                                    :data="chartData.calibration.data"
                                    :layout="chartData.calibration.layout"
                                    :publicationReady="uiStore.isAcademicMode"
                                />
                            </el-col>
                            
                            <!-- DCA -->
                             <el-col :span="12" v-if="activePlots.dca" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="dca-plot"
                                    :title="config.model_type === 'cox' ? `临床决策曲线 (DCA) (t=${evaluationTimePoint})` : '临床决策曲线 (DCA)'"
                                    :data="chartData.dca.data"
                                    :layout="chartData.dca.layout"
                                    :publicationReady="uiStore.isAcademicMode"
                                />
                            </el-col>
                        </el-row>
                    </el-tab-pane>

                    <el-tab-pane label="列线图 (Nomogram)" name="nomogram" v-if="nomogramData">
                         <el-alert title="简易列线图评分表 (Scorekeeper)" type="info" :closable="false" style="margin-bottom: 15px">
                             <div>
                                 列线图的本质是基于回归系数的线性加权求和。此处提供变量系数表，可用于构建个体化评分工具。
                                 <br/>
                                 <b>预测公式:</b> P = 1 / (1 + exp(-TotalScore)) [Logistic] 或 S(t) = S0(t)^exp(TotalScore) [Cox]
                             </div>
                         </el-alert>
                         
                         <!-- New Interactive Nomogram (Cox) -->
                         <div v-if="nomogramData.axes">
                              <NomogramVisualizer :spec="nomogramData" @view-calibration="activeResultTab = 'clinical'" />
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

                    <el-tab-pane label="假设检验 (Assumptions)" name="assumptions">
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
                                :publicationReady="uiStore.isAcademicMode"
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
            </div>
            <div v-else>
                <el-card shadow="never" style="height: 100%; min-height: 640px; display: flex; align-items: center; justify-content: center; background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px;">
                    <el-empty :image-size="240" description=" ">
                        <template #extra>
                            <div style="text-align: center; color: #64748b; font-size: 14px; max-width: 480px; transform: translateY(-20px);">
                                <h2 style="color: #3b71ca; margin-bottom: 24px; font-weight: 700; display: flex; align-items: center; justify-content: center;">
                                    <MagicStick style="width: 24px; height: 24px; margin-right: 10px;" /> 准备就绪，开启智能发现
                                </h2>
                                <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); text-align: left; border: 1px solid #e2e8f0;">
                                    <p style="margin-top: 0; font-weight: 600; color: #1e293b; margin-bottom: 16px;">快速开始三部曲：</p>
                                    <div style="display: flex; flex-direction: column; gap: 12px;">
                                        <div style="display: flex; gap: 12px;">
                                            <span style="background: #eff6ff; color: #3b71ca; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">1</span>
                                            <span>在左侧面板选定<b>模型类型</b>（如 Cox 或 Logistic）</span>
                                        </div>
                                        <div style="display: flex; gap: 12px;">
                                            <span style="background: #eff6ff; color: #3b71ca; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">2</span>
                                            <span>指定<b>结局变量</b>，并点击右上角 <b>AI 智能角色推荐</b></span>
                                        </div>
                                        <div style="display: flex; gap: 12px;">
                                            <span style="background: #f0fdf4; color: #2e7d32; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">3</span>
                                            <span>点击底部 <b style="color: #2e7d32;">运行模型</b> 实时获取统计洞察</span>
                                        </div>
                                    </div>
                                </div>
                                <p style="margin-top: 24px; color: #94a3b8; font-size: 13px; line-height: 1.5;">
                                    Insight 将为您自动计算 HR/OR 系数、P 值、生存曲线，<br/>并生成基于 LLM 的医学解读报告。
                                </p>
                            </div>
                        </template>
                    </el-empty>
                </el-card>
            </div>
        </el-col>
    </el-row>

    <!-- Comparison Dialog -->
    <el-dialog v-model="showComparisonDialog" title="模型对比分析 (Model Comparison Report)" width="70%">
        <div v-if="comparisonMetrics">
            <h3>1. 基本拟合指标对比 (Model Fit Statistics)</h3>
            <el-table :data="[comparisonMetrics.basic.c_index, comparisonMetrics.basic.aic, comparisonMetrics.basic.bic, comparisonMetrics.basic.ll]" border size="small" stripe>
                <el-table-column label="指标 (Metric)">
                    <template #default="scope">
                        <span v-if="scope.$index === 0"><b>C-index</b> (越高越好)</span>
                        <span v-if="scope.$index === 1"><b>AIC</b> (越低越好)</span>
                        <span v-if="scope.$index === 2"><b>BIC</b> (越低越好)</span>
                        <span v-if="scope.$index === 3"><b>Log-Likelihood</b> (越高越好)</span>
                    </template>
                </el-table-column>
                <el-table-column :label="'基线模型 (Model 1)'" prop="m1">
                    <template #default="scope">{{ scope.row.m1.toFixed(3) }}</template>
                </el-table-column>
                <el-table-column :label="'当前模型 (Model 2)'" prop="m2">
                    <template #default="scope">{{ scope.row.m2.toFixed(3) }}</template>
                </el-table-column>
                <el-table-column label="差异 (Difference)" prop="diff">
                    <template #default="scope">
                        <span :style="{ fontWeight: 'bold', color: scope.row.diff > 0 ? (scope.$index === 1 || scope.$index === 2 ? 'red' : 'green') : (scope.$index === 1 || scope.$index === 2 ? 'green' : 'red') }">
                            {{ scope.row.diff > 0 ? '+' : '' }}{{ scope.row.diff.toFixed(3) }}
                        </span>
                        
                        <!-- 自动解读标签 -->
                        <el-tag size="small" type="success" style="margin-left: 10px" v-if="scope.$index === 0 && scope.row.diff > 0.01">性能提升</el-tag>
                        <el-tag size="small" type="success" style="margin-left: 10px" v-if="(scope.$index === 1 || scope.$index === 2) && scope.row.diff < -2">性能提升</el-tag>
                    </template>
                </el-table-column>
            </el-table>
            
            <h3 style="margin-top: 20px">2. 改善与增量价值 (Reclassification & Incremental Value)</h3>
            <div v-if="comparisonMetrics.reclassification">
                <el-alert type="info" :closable="false" style="margin-bottom: 10px">
                    基于预测时间点 T = {{ comparisonMetrics.reclassification.time_point }} (月) 计算。
                    反映了加入新变量后，模型对个体风险分类的改善程度。
                </el-alert>
                <el-descriptions :column="2" border>
                    <el-descriptions-item label="NRI (连续净重分类改善指数)">
                        <span style="font-size: 16px; font-weight: bold">{{ comparisonMetrics.reclassification.nri.toFixed(4) }}</span>
                        <div style="font-size: 12px; color: gray; margin-top: 4px">
                            解读：NRI > 0 意味着模型正确地将发生事件者归为更高风险，或将未发生者归为更低风险。
                        </div>
                    </el-descriptions-item>
                    <el-descriptions-item label="IDI (综合判别改善指数)">
                        <span style="font-size: 16px; font-weight: bold">{{ comparisonMetrics.reclassification.idi.toFixed(4) }}</span>
                        <div style="font-size: 12px; color: gray; margin-top: 4px">
                            解读：IDI > 0 意味着新模型提高了平均预测概率的区分度。
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

    <!-- Variable Selection Dialog -->
    <el-dialog v-model="showSelectionDialog" title="自动变量筛选 (Automated Variable Selection)" width="600px" destroy-on-close>
        <div class="selection-config">
            <el-form label-position="top" size="small">
                <el-form-item label="筛选方法 (Selection Method)">
                    <el-radio-group v-model="selectionParams.method">
                        <el-radio label="stepwise">逐步回归 (Stepwise)</el-radio>
                        <el-radio label="lasso">LASSO 压缩</el-radio>
                    </el-radio-group>
                </el-form-item>
                
                <el-row :gutter="20" v-if="selectionParams.method === 'stepwise'">
                    <el-col :span="12">
                        <el-form-item label="筛选方向">
                            <el-select v-model="selectionParams.direction" style="width: 100%">
                                <el-option label="双向 (Both)" value="both" />
                                <el-option label="向前 (Forward)" value="forward" />
                                <el-option label="向后 (Backward)" value="backward" />
                            </el-select>
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="筛选准则">
                            <el-select v-model="selectionParams.criterion" style="width: 100%">
                                <el-option label="AIC (赤池信息准则)" value="aic" />
                                <el-option label="BIC (贝叶斯信息准则)" value="bic" />
                            </el-select>
                        </el-form-item>
                    </el-col>
                </el-row>
                
                <el-alert v-if="selectionParams.method === 'lasso'" title="LASSO 说明" type="info" :closable="false" style="margin-bottom: 20px">
                    LASSO 通过 L1 正则化将不重要的变量系数压缩至零，从而实现自动变量选择和降维。
                </el-alert>
                
                <div style="text-align: right; margin-top: 10px;">
                    <el-button type="primary" @click="runVariableSelection" :loading="selectionLoading">开始筛选</el-button>
                </div>
            </el-form>
        </div>
        
        <el-divider v-if="selectionResults" />
        
        <div v-if="selectionResults" class="selection-results">
            <div style="margin-bottom: 15px;">
                <span style="font-weight: bold; color: #606266;">筛选结果：</span>
                <el-tag 
                    v-for="feat in selectionResults.selected_features" 
                    :key="feat" 
                    type="success" 
                    size="small" 
                    style="margin-right: 5px; margin-top: 5px;"
                >
                    {{ feat }}
                </el-tag>
                <el-empty v-if="selectionResults.selected_features.length === 0" description="未筛选出显著特征" :image-size="60" />
            </div>
            
            <div v-if="selectionResults.eliminated_features.length > 0" style="margin-bottom: 15px;">
                <span style="font-size: 13px; color: #909399;">已剔除：</span>
                <el-tag 
                    v-for="feat in selectionResults.eliminated_features" 
                    :key="feat" 
                    type="info" 
                    size="small" 
                    style="margin-right: 5px; margin-top: 5px; text-decoration: line-through;"
                >
                    {{ feat }}
                </el-tag>
            </div>

            <div v-if="selectionResults.steps" style="max-height: 150px; overflow-y: auto; background: #f8f9fb; padding: 10px; font-size: 12px; color: #606266; border-radius: 4px;">
                <div v-for="(step, idx) in selectionResults.steps" :key="idx">Step {{ idx+1 }}: {{ step }}</div>
            </div>

            <div style="margin-top: 20px; text-align: center;">
                <el-button type="success" :disabled="selectionResults.selected_features.length === 0" @click="applySelection">应用筛选结果至模型</el-button>
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
import { computed } from 'vue'
import InterpretationPanel from './InterpretationPanel.vue'
import InsightChart from './InsightChart.vue'
import NomogramVisualizer from './NomogramVisualizer.vue'
import PublicationTable from '../../../components/PublicationTable.vue'
import AnalysisHeader from '../../../components/AnalysisHeader.vue'
import { MagicStick, QuestionFilled, Setting, CopyDocument, Filter, Search, ArrowDown } from '@element-plus/icons-vue'
import { useUiStore } from '../../../stores/ui'
import { useModeling } from '../../../composables/useModeling'
import { formatPValue, formatNumber, formatEffectSize } from '../../../utils/formatters'
import { METRIC_TOOLTIPS, MODEL_OPTIONS } from '../../../constants/modeling'

const props = defineProps({
    projectId: { type: String, required: true },
    datasetId: { type: Number, default: null },
    metadata: { type: Object, default: null }
})

const uiStore = useUiStore()

// 使用建模逻辑 Composable
const {
    // 状态
    config, coxTarget, results, loading, activeResultTab,
    showSelectionDialog, selectionLoading, selectionResults, selectionParams,
    isSuggesting, isInterpreting, aiSuggestedFeatures,
    collinearityWarning, checkingCollinearity,
    evaluationTimePoint, baselineResult, showComparisonDialog, comparisonMetrics,
    chartData,
    
    // 计算属性
    variableOptions, isTargetSet, maxImportance, targetOptions, featureOptions,
    timeOptions, eventOptions, selectedCategoricalVars,
    availableTimePoints, currentExtendedMetrics, activePlots, nomogramData,
    topResult,
    
    // 函数
    syncCoxTarget, runVariableSelection, applySelection, autoSuggestRoles,
    runAIInterpretation, runModel, exportResults, copyMethodology,
    setAsBaseline, compareWithBaseline
} = useModeling(
    computed(() => props.projectId), 
    computed(() => props.datasetId), 
    computed(() => props.metadata)
)

const metricTooltips = METRIC_TOOLTIPS
const modelOptions = MODEL_OPTIONS
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
.ai-suggest-btn {
    background: linear-gradient(45deg, #3b71ca, #a8c0ff);
    border: none;
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.ai-suggest-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(59, 113, 202, 0.4);
    background: linear-gradient(45deg, #4b81da, #b8d0ff);
}
.ai-interpret-btn {
    background: linear-gradient(45deg, #6366f1, #a855f7);
    border: none;
    transition: all 0.3s ease;
}
.ai-interpret-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
}
</style>
