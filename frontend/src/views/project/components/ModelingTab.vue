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
                             <el-button type="success" size="small" @click="exportResults">导出 Excel</el-button>
                             <el-switch
                                v-model="isGlobalPublicationReady"
                                inline-prompt
                                active-text="学术绘图级"
                                inactive-text="普通预览"
                                style="margin-left: 15px; --el-switch-on-color: #67C23A"
                                title="一键切换所有图表为学术发表样式 (Times New Roman, 无网格, 高粗度)"
                             />
                        </div>
                    </div>
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
                        <el-table v-else :data="results.summary" style="width: 100%" height="400" stripe border size="small">
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
                        </el-table>
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
                                    :publicationReady="isGlobalPublicationReady"
                                />
                            </el-col>
                            
                            <!-- Calibration -->
                            <el-col :span="12" v-if="activePlots.calibration" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="calibration-plot"
                                    :title="config.model_type === 'cox' ? `校准曲线 (Calibration) (t=${evaluationTimePoint})` : '校准曲线 (Calibration)'"
                                    :data="chartData.calibration.data"
                                    :layout="chartData.calibration.layout"
                                    :publicationReady="isGlobalPublicationReady"
                                />
                            </el-col>
                            
                            <!-- DCA -->
                             <el-col :span="12" v-if="activePlots.dca" style="margin-bottom: 20px;">
                                <InsightChart
                                    chartId="dca-plot"
                                    :title="config.model_type === 'cox' ? `临床决策曲线 (DCA) (t=${evaluationTimePoint})` : '临床决策曲线 (DCA)'"
                                    :data="chartData.dca.data"
                                    :layout="chartData.dca.layout"
                                    :publicationReady="isGlobalPublicationReady"
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
                                :publicationReady="isGlobalPublicationReady"
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
import { ref, computed, watch, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../../api/client'
import Plotly from 'plotly.js-dist-min'
import InterpretationPanel from './InterpretationPanel.vue'
import InsightChart from './InsightChart.vue'
import NomogramVisualizer from './NomogramVisualizer.vue'
import { MagicStick, QuestionFilled, Setting, CopyDocument, Filter, Search, ArrowDown } from '@element-plus/icons-vue'
import { useVariableOptions } from '../../../composables/useVariableOptions'
import { formatPValue, formatNumber, formatEffectSize } from '../../../utils/formatters'

const props = defineProps({
    projectId: { type: String, required: true },
    datasetId: { type: Number, default: null },
    metadata: { type: Object, default: null }
})

const isGlobalPublicationReady = ref(false)

const varHealthMap = ref({})

// 使用公共 Composable 提取变量选项
const { 
    allOptions: variableOptions
} = useVariableOptions(computed(() => props.metadata), varHealthMap)



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
    'bic': '贝叶斯信息量：类似 AIC，但对参数数量惩罚更重，常用于模型筛选，越小越好。',
    'c_index': '一致性指数：生存分析核心指标，衡量模型预测风险等级的准确性，越接近 1 越好。',
    'log_likelihood': '对数似然 (Log-Likelihood)：越高越好，表示模型对数据的解释程度。',
    'n_events': '事件数 (Events)：分析中观察到的终点事件总数。',
    'ph_global_p': '全局等比例风险检验 P 值：用于评估整个模型是否满足 Cox 模型的比例风险假定。P < 0.05 提示违反假定。'
}

const modelOptions = [
    { label: '线性回归 (Linear Regression, OLS)', value: 'linear' },
    { label: '逻辑回归 (Logistic Regression)', value: 'logistic' },
    { label: 'Cox 比例风险回归 (Cox Proportional Hazards)', value: 'cox' },
    { label: '随机森林 (Random Forest)', value: 'random_forest' },
    { label: 'XGBoost', value: 'xgboost' }
]

const config = reactive({
    model_type: 'logistic', // 当前选中的模型类型
    target: null,          // 结局变量 (Y/结局指标)
    features: [],          // 纳入模型的特征变量列表
    ref_levels: {},        // 分类变量的对照组设置，例如 { 'Sex': 'Female' }
    model_params: {
        n_estimators: 100,
        max_depth: null,
        learning_rate: 0.1
    }
})

// 用于 Cox 模型时间/事件的临时状态，避免直接操作 config.target 导致的 null 访问异常
const coxTarget = reactive({
    time: null,
    event: null
})

const isTargetSet = computed(() => {
    if (config.model_type === 'cox') {
        return config.target && config.target.time && config.target.event
    }
    return !!config.target
})

const syncCoxTarget = () => {
    config.target = { ...coxTarget }
}

// 监听模型类型切换，确保 target 数据结构正确
watch(() => config.model_type, (newType) => {
    if (newType === 'cox') {
        // 如果是从非 Cox 切换过来，初始化为对象
        if (typeof config.target !== 'object' || config.target === null) {
            config.target = { time: coxTarget.time, event: coxTarget.event }
        } else {
            // 如果已经是对象（可能来自自动推荐），读取其值同步到 coxTarget UI
            coxTarget.time = config.target.time || null
            coxTarget.event = config.target.event || null
        }
    } else {
        // 如果是从 Cox 切换到其他，如果是对象则重置为 null
        if (typeof config.target === 'object') {
            config.target = null
        }
    }
    // 切换模型通常需要重置结果，防止显示旧的统计图表
    results.value = null
})

// --- 变量筛选 (Variable Selection) ---
const showSelectionDialog = ref(false)
const selectionLoading = ref(false)
const selectionResults = ref(null)
const selectionParams = reactive({
    method: 'stepwise',
    direction: 'both',
    criterion: 'aic'
})

const runVariableSelection = async () => {
    selectionLoading.value = true
    selectionResults.value = null
    try {
        const { data } = await api.post('/modeling/select-variables', {
            dataset_id: props.datasetId,
            model_type: config.model_type,
            target: config.target,
            features: config.features,
            method: selectionParams.method,
            params: {
                direction: selectionParams.direction,
                criterion: selectionParams.criterion
            }
        })
        selectionResults.value = data
        ElMessage.success('筛选完成')
    } catch (e) {
        ElMessage.error(e.response?.data?.message || '筛选失败')
    } finally {
        selectionLoading.value = false
    }
}

const applySelection = () => {
    if (selectionResults.value && selectionResults.value.selected_features) {
        config.features = [...selectionResults.value.selected_features]
        showSelectionDialog.value = false
        ElMessage({
            message: `已应用 ${config.features.length} 个筛选后的特征。`,
            type: 'success'
        })
        // 自动运行一次模型
        runModel()
    }
}
// ------------------------------------



const isSuggesting = ref(false)
const isInterpreting = ref(false)
const aiSuggestedFeatures = ref([])

const runAIInterpretation = async () => {
    if (!results.value) {
        ElMessage.warning('请先运行模型以生成结果')
        return
    }
    
    isInterpreting.value = true
    try {
        const { data } = await api.post('/modeling/ai-interpret', {
            model_type: config.model_type,
            summary: results.value.summary,
            metrics: results.value.metrics
        })
        
        // Update results with AI interpretation
        // We use a new structure that InterpretationPanel.vue recognizes
        results.value.interpretation = {
            text: data.interpretation,
            is_ai: true,
            level: 'info'
        }
        ElMessage.success('AI 深度解读完成')
    } catch (e) {
        console.error("AI Interpretation failed", e)
        ElMessage.error(e.response?.data?.message || 'AI 解读失败')
    } finally {
        isInterpreting.value = false
    }
}

const autoSuggestRoles = async () => {
    if (!props.datasetId) return
    
    isSuggesting.value = true
    aiSuggestedFeatures.value = []
    
    try {
        const { data } = await api.post('/modeling/ai-suggest-roles', {
            model_type: config.model_type,
            variables: props.metadata.variables
        })
        const rec = data.recommendation
        
        // Apply AI Recommendation
        if (config.model_type === 'cox') {
            coxTarget.time = rec.time
            coxTarget.event = rec.event
            syncCoxTarget()
        } else {
            config.target = rec.target
        }
        
        config.features = rec.features
        aiSuggestedFeatures.value = rec.features || []
        
        ElMessage.success(`AI 推荐完成`)
        if (rec.reason) {
            setTimeout(() => {
                 ElMessage.info({
                    message: rec.reason,
                    duration: 5000,
                    showClose: true
                 })
            }, 500)
        }
        
    } catch (e) {
        console.error("AI Recommendation failed", e)
        ElMessage.error(e.response?.data?.message || 'AI 推荐失败')
    } finally {
        isSuggesting.value = false
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

const loading = ref(false)
const results = ref(null)
const activeResultTab = ref('details')

const targetOptions = computed(() => {
    return variableOptions.value.map(v => {
        let disabled = false
        // 1. 如果变量已被作为特征，禁用之
        if (config.features.includes(v.value)) disabled = true
        
        // 2. 对于线性回归，目标必须是连续型/数值型
        if (config.model_type === 'linear') {
            if (!['continuous', 'float', 'int'].includes(v.type)) disabled = true
        }
        
        return { ...v, disabled }
    })
})

const timeOptions = computed(() => {
    return variableOptions.value.map(v => ({
        ...v,
        disabled: config.features.includes(v.value) || coxTarget.event === v.value
    }))
})

const eventOptions = computed(() => {
    return variableOptions.value.map(v => ({
        ...v,
        disabled: config.features.includes(v.value) || coxTarget.time === v.value
    }))
})

const featureOptions = computed(() => {
    return variableOptions.value.map(v => {
        let disabled = false
        // 1. 如果是普通结局变量，禁用之
        if (config.model_type !== 'cox') {
            if (config.target === v.value) disabled = true
        } else {
            // 2. 如果是 Cox 的时间或事件，禁用之
            if (coxTarget.time === v.value || coxTarget.event === v.value) disabled = true
        }
        return { ...v, disabled }
    })
})

// 已移至顶部并使用 useVariableOptions

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
        // Removed autoSuggestRoles() on load per user request
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

// --- 临床效能评估逻辑 (Clinical Evaluation) ---
const evaluationTimePoint = ref(null) // 当前选中的预测评估时间点 (Cox 模型专用)

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
        
        // 校准曲线展示所有可用的时间点，以便于对比
        const allCalibrations = results.value.clinical_eval.calibration || {}
        
        return {
            roc: results.value.clinical_eval.roc[t],
            dca: results.value.clinical_eval.dca[t],
            calibration: allCalibrations, // 传递全量校准数据
            is_cox: true,
            current_t: t
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
    // ROC 曲线 (ROC Curve)
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
            xaxis: { title: '假阳性率 (False Positive Rate)' },
            yaxis: { title: '真阳性率 (True Positive Rate)' }
        }
    }

    // Calibration Curve
    if (plots.calibration) {
        const calData = []
        const colors = ['#3B71CA', '#D32F2F', '#2E7D32', '#E6A23C', '#9C27B0']
        const unit = results.value?.clinical_eval?.time_unit === 'days' ? '天' : '月'

        if (plots.is_cox) {
            // Cox 模型：绘制多个时间点的曲线
            const timePoints = Object.keys(plots.calibration).map(Number).sort((a, b) => a - b)
            timePoints.forEach((t, idx) => {
                const cal = plots.calibration[t]
                if (cal && cal.prob_pred) {
                    calData.push({
                        x: cal.prob_pred,
                        y: cal.prob_true,
                        mode: 'lines+markers',
                        name: `${t}${unit}`,
                        line: { color: colors[idx % colors.length], width: t === plots.current_t ? 3 : 2 },
                        marker: { size: t === plots.current_t ? 8 : 6 },
                        opacity: t === plots.current_t ? 1 : 0.6
                    })
                }
            })
        } else {
            // 普通二分类模型
            calData.push({
                x: plots.calibration.prob_pred,
                y: plots.calibration.prob_true,
                mode: 'lines+markers',
                name: '模型 (Model)',
                line: { color: '#D32F2F' }
            })
        }

        // 添加完美校准参考线
        calData.push({
            x: [0, 1], y: [0, 1],
            mode: 'lines',
            name: '完美校准 (Ideal)',
            line: { dash: 'dash', color: 'gray' },
            showlegend: true
        })

        chartData.calibration.data = calData
        chartData.calibration.layout = {
            xaxis: { title: '预测概率均值 (Mean Predicted Probability)', range: [0, 1] },
            yaxis: { title: '实际事件发生率 (Fraction of Events)', range: [0, 1] },
            legend: { orientation: 'h', y: -0.2 }
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
                name: '模型 (Model)',
                line: { color: 'red', width: 2 }
            },
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_all,
                mode: 'lines',
                name: '全干预 (Treat All)',
                line: { color: 'gray', dash: 'dash' }
            },
            {
                x: plots.dca.thresholds,
                y: plots.dca.net_benefit_none,
                mode: 'lines',
                name: '全不干预 (Treat None)',
                line: { color: 'black' }
            }
        ]
        chartData.dca.layout = {
            xaxis: { title: '阈值概率 (Threshold Probability)', range: [0, 1] },
            yaxis: { title: '净获益 (Net Benefit)', range: [-0.05, maxY + 0.05] }
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
             title: 'VIF 指标 (VIF Values)',
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

// --- 模型对比逻辑 (Model Comparison) ---
const baselineResult = ref(null) // 基线模型对象 (Model 1)
const showComparisonDialog = ref(false) // 是否显示对比对话框
const comparisonMetrics = ref(null) // 对比指标计算结果

const setAsBaseline = () => {
    if (!results.value) return
    baselineResult.value = JSON.parse(JSON.stringify(results.value))
    ElMessage.success('当前模型已设为基线 (Model 1)')
}

/**
 * 手动计算轻量级的 NRI 和 IDI（前端预览用）。
 * 严谨的 NRI/IDI 计算通常建议在后端通过 bootrstrap 获取置信区间。
 */
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

/**
 * 对比当前模型 (Model 2) 与已保存的基线模型 (Model 1)。
 */
const compareWithBaseline = () => {
    if (!baselineResult.value || !results.value) return;

    const m1 = baselineResult.value.metrics;
    const m2 = results.value.metrics;
    
    // Safety check for keys
    const getVal = (m, k) => m && m[k] !== undefined ? parseFloat(m[k]) : 0;

    const cmp = {
        models: {
            m1_name: '基线模型 (Model 1)',
            m2_name: '当前模型 (Model 2)'
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
