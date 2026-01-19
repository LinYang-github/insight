import { ref, computed, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/client'
import { calculateNRI_IDI } from '../utils/statistics'
import { useVariableOptions } from './useVariableOptions'

/**
 * useModeling Composable
 * 抽离 ModelingTab.vue 的庞大状态机与核心逻辑
 */
export function useModeling(projectId, datasetId, metadata) {
    const varHealthMap = ref({})
    const loading = ref(false)
    const results = ref(null)
    const activeResultTab = ref('details')
    
    // --- 核心配置状态 ---
    const config = reactive({
        model_type: 'logistic',
        target: null,
        features: [],
        ref_levels: {},
        model_params: {
            n_estimators: 100,
            max_depth: null,
            learning_rate: 0.1
        }
    })

    const coxTarget = reactive({
        time: null,
        event: null
    })

    const syncCoxTarget = () => {
        config.target = { ...coxTarget }
    }

    // --- 变量选项 (利用已有 Composable) ---
    const { allOptions: variableOptions } = useVariableOptions(metadata, varHealthMap)

    // --- 计算属性 ---
    const isTargetSet = computed(() => {
        if (config.model_type === 'cox') {
            return config.target && config.target.time && config.target.event
        }
        return !!config.target
    })

    const maxImportance = computed(() => {
        if (!results.value || !results.value.importance) return 1
        return Math.max(...results.value.importance.map(i => i.importance))
    })

    const targetOptions = computed(() => {
        return variableOptions.value.map(v => {
            let disabled = false
            if (config.features.includes(v.value)) disabled = true
            if (config.model_type === 'linear') {
                if (!['continuous', 'float', 'int'].includes(v.type)) disabled = true
            }
            return { ...v, disabled }
        })
    })

    const featureOptions = computed(() => {
        return variableOptions.value.map(v => {
            let disabled = false
            if (config.model_type !== 'cox') {
                if (config.target === v.value) disabled = true
            } else {
                if (coxTarget.time === v.value || coxTarget.event === v.value) disabled = true
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

    const selectedCategoricalVars = computed(() => {
        if (!metadata.value || !config.features || config.features.length === 0) return []
        return metadata.value.variables.filter(v => 
            config.features.includes(v.name) && 
            v.type === 'categorical' && 
            v.categories && v.categories.length > 0
        )
    })

    // --- 变量筛选与 AI 建议 ---
    const showSelectionDialog = ref(false)
    const selectionLoading = ref(false)
    const selectionResults = ref(null)
    const selectionParams = reactive({
        method: 'stepwise',
        direction: 'both',
        criterion: 'aic'
    })

    const isSuggesting = ref(false)
    const isInterpreting = ref(false)
    const aiSuggestedFeatures = ref([])

    const runVariableSelection = async () => {
        selectionLoading.value = true
        selectionResults.value = null
        try {
            const { data } = await api.post('/modeling/select-variables', {
                dataset_id: datasetId.value,
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

    const applySelection = (runImmediately = true) => {
        if (selectionResults.value && selectionResults.value.selected_features) {
            config.features = [...selectionResults.value.selected_features]
            showSelectionDialog.value = false
            ElMessage.success(`已应用 ${config.features.length} 个筛选后的特征。`)
            if (runImmediately) runModel()
        }
    }

    const autoSuggestRoles = async () => {
        if (!datasetId.value) return
        isSuggesting.value = true
        aiSuggestedFeatures.value = []
        try {
            const { data } = await api.post('/modeling/ai-suggest-roles', {
                model_type: config.model_type,
                variables: metadata.value.variables
            })
            const rec = data.recommendation
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
                     ElMessage.info({ message: rec.reason, duration: 5000, showClose: true })
                }, 500)
            }
        } catch (e) {
            ElMessage.error(e.response?.data?.message || 'AI 推荐失败')
        } finally {
            isSuggesting.value = false
        }
    }

    const runAIInterpretation = async () => {
        if (!results.value) return ElMessage.warning('请先运行模型以生成结果')
        isInterpreting.value = true
        try {
            const { data } = await api.post('/modeling/ai-interpret', {
                model_type: config.model_type,
                summary: results.value.summary,
                metrics: results.value.metrics
            })
            results.value.interpretation = { text: data.interpretation, is_ai: true, level: 'info' }
            ElMessage.success('AI 深度解读完成')
        } catch (e) {
            ElMessage.error(e.response?.data?.message || 'AI 解读失败')
        } finally {
            isInterpreting.value = false
        }
    }

    // --- 共线性检查 ---
    let collinearityTimer = null
    const checkingCollinearity = ref(false)
    const collinearityWarning = ref(null)

    const checkCollinearity = async () => {
        collinearityWarning.value = null
        if (config.features.length < 2) return
        checkingCollinearity.value = true
        try {
            const { data } = await api.post('/statistics/check-collinearity', {
                dataset_id: datasetId.value,
                features: config.features
            })
            if (data.status !== 'ok') {
                const first = data.report[0]
                collinearityWarning.value = `检测到共线性风险: ${first.message} (VIF=${first.vif.toFixed(1)})。建议移除该变量。`
            }
        } finally {
            checkingCollinearity.value = false
        }
    }

    watch(() => config.features, () => {
        collinearityWarning.value = null
        if (collinearityTimer) clearTimeout(collinearityTimer)
        collinearityTimer = setTimeout(checkCollinearity, 1000)
    })

    // --- 模型运行与导出 ---
    const runModel = async () => {
        if (!datasetId.value) return
        loading.value = true
        try {
            const { data } = await api.post('/modeling/run', {
                project_id: projectId.value,
                dataset_id: datasetId.value,
                ...config
            })
            if (data.results.status === 'failed') {
                results.value = null
                ElMessage({ message: data.results.message, type: 'error', duration: 10000, showClose: true })
                return 
            }
            results.value = data.results
            ElMessage.success('模型运行成功')
        } catch (error) {
            ElMessage.error(error.response?.data?.message || '模型运行失败')
        } finally {
            loading.value = false
        }
    }

    const exportResults = async () => {
        try {
            const { data } = await api.post('/modeling/export', {
                project_id: projectId.value,
                dataset_id: datasetId.value,
                ...config
            })
            window.open(data.download_url, '_blank')
            ElMessage.success('导出成功')
        } catch (error) {
            ElMessage.error('导出失败')
        }
    }

    const copyMethodology = () => {
        if (!results.value || !results.value.methodology) return ElMessage.info('暂无方法学内容')
        navigator.clipboard.writeText(results.value.methodology).then(() => {
            ElMessage.success('方法学段落已复制到剪贴板')
        })
    }

    // --- 临床效能评估 ---
    const evaluationTimePoint = ref(null)
    const availableTimePoints = computed(() => {
        if (!results.value || !results.value.clinical_eval || !results.value.clinical_eval.dca) return []
        return Object.keys(results.value.clinical_eval.dca).map(Number).sort((a,b) => a-b)
    })

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
        if (config.model_type === 'cox' && results.value.clinical_eval) {
            const t = evaluationTimePoint.value
            if (!t) return {}
            return {
                roc: results.value.clinical_eval.roc[t],
                dca: results.value.clinical_eval.dca[t],
                calibration: results.value.clinical_eval.calibration || {},
                is_cox: true,
                current_t: t
            }
        }
        return results.value.plots || {}
    })

    const nomogramData = computed(() => {
        if (!results.value) return null
        if (config.model_type === 'logistic' && results.value.plots?.nomogram) return results.value.plots.nomogram
        if (config.model_type === 'cox' && results.value.clinical_eval?.nomogram) return results.value.clinical_eval.nomogram
        return null
    })

    // --- 图表渲染数据 ---
    const chartData = reactive({
        roc: { data: [], layout: {} },
        calibration: { data: [], layout: {} },
        dca: { data: [], layout: {} },
        vif: { data: [], layout: {} }
    })

    const renderEvaluationPlots = (plots) => {
        if (plots.roc) {
            chartData.roc.data = [
                { x: plots.roc.fpr, y: plots.roc.tpr, mode: 'lines', name: `AUC = ${plots.roc.auc.toFixed(3)}`, line: { color: 'blue' } },
                { x: [0, 1], y: [0, 1], mode: 'lines', name: 'Random', line: { dash: 'dash', color: 'gray' } }
            ]
            chartData.roc.layout = { xaxis: { title: '假阳性率 (FPR)' }, yaxis: { title: '真阳性率 (TPR)' } }
        }
        if (plots.calibration) {
            const calData = []
            const colors = ['#3B71CA', '#D32F2F', '#2E7D32', '#E6A23C', '#9C27B0']
            if (plots.is_cox) {
                const timePoints = Object.keys(plots.calibration).map(Number).sort((a,b) => a-b)
                timePoints.forEach((t, idx) => {
                    const cal = plots.calibration[t]
                    if (cal?.prob_pred) {
                        calData.push({
                            x: cal.prob_pred, y: cal.prob_true, mode: 'lines+markers', name: `${t}`,
                            line: { color: colors[idx % colors.length], width: t === plots.current_t ? 3 : 2 },
                            marker: { size: t === plots.current_t ? 8 : 6 },
                            opacity: t === plots.current_t ? 1 : 0.6
                        })
                    }
                })
            } else {
                calData.push({ x: plots.calibration.prob_pred, y: plots.calibration.prob_true, mode: 'lines+markers', name: 'Model', line: { color: '#D32F2F' } })
            }
            calData.push({ x: [0, 1], y: [0, 1], mode: 'lines', name: 'Ideal', line: { dash: 'dash', color: 'gray' } })
            chartData.calibration.data = calData
            chartData.calibration.layout = { xaxis: { title: '预测概率', range: [0, 1] }, yaxis: { title: '实际率', range: [0, 1] }, legend: { orientation: 'h', y: -0.2 } }
        }
        if (plots.dca) {
            const maxY = Math.max(...plots.dca.net_benefit_model, ...plots.dca.net_benefit_all)
            chartData.dca.data = [
                { x: plots.dca.thresholds, y: plots.dca.net_benefit_model, mode: 'lines', name: 'Model', line: { color: 'red', width: 2 } },
                { x: plots.dca.thresholds, y: plots.dca.net_benefit_all, mode: 'lines', name: 'Treat All', line: { color: 'gray', dash: 'dash' } },
                { x: plots.dca.thresholds, y: plots.dca.net_benefit_none, mode: 'lines', name: 'Treat None', line: { color: 'black' } }
            ]
            chartData.dca.layout = { xaxis: { title: '阈值概率', range: [0, 1] }, yaxis: { title: '净获益', range: [-0.05, maxY + 0.05] } }
        }
        if (plots.vif) {
            chartData.vif.data = [{ x: plots.vif.variables, y: plots.vif.vif_values, type: 'bar', marker: { color: plots.vif.vif_values.map(v => v > 5 ? 'red' : '#409EFF') } }]
            chartData.vif.layout = { title: 'VIF Values', shapes: [{ type: 'line', x0: -0.5, x1: plots.vif.variables.length - 0.5, y0: 5, y1: 5, line: { color: 'red', width: 2, dash: 'dash' } }] }
        }
    }

    watch(activePlots, (plots) => {
        if (plots) renderEvaluationPlots(plots)
    }, { deep: true })

    // --- 模型对比 ---
    const baselineResult = ref(null)
    const showComparisonDialog = ref(false)
    const comparisonMetrics = ref(null)

    const setAsBaseline = () => {
        if (!results.value) return
        baselineResult.value = JSON.parse(JSON.stringify(results.value))
        ElMessage.success('当前模型已设为基线 (Model 1)')
    }

    const compareWithBaseline = () => {
        if (!baselineResult.value || !results.value) return
        const m1 = baselineResult.value.metrics
        const m2 = results.value.metrics
        const getVal = (m, k) => m && m[k] !== undefined ? parseFloat(m[k]) : 0
        const cmp = {
            models: { m1_name: 'Model 1', m2_name: 'Model 2' },
            basic: {
                c_index: { m1: getVal(m1, 'c_index'), m2: getVal(m2, 'c_index'), diff: getVal(m2, 'c_index') - getVal(m1, 'c_index') },
                aic: { m1: getVal(m1, 'aic'), m2: getVal(m2, 'aic'), diff: getVal(m2, 'aic') - getVal(m1, 'aic') },
                bic: { m1: getVal(m1, 'bic'), m2: getVal(m2, 'bic'), diff: getVal(m2, 'bic') - getVal(m1, 'bic') },
                ll: { m1: getVal(m1, 'log_likelihood'), m2: getVal(m2, 'log_likelihood'), diff: getVal(m2, 'log_likelihood') - getVal(m1, 'log_likelihood') }
            },
            reclassification: null
        }
        const t = evaluationTimePoint.value
        if (t && baselineResult.value.clinical_eval && results.value.clinical_eval) {
             const pred1 = baselineResult.value.clinical_eval.predictions?.[t]
             const pred2 = results.value.clinical_eval.predictions?.[t]
             if (pred1 && pred2 && pred1.y_true.length === pred2.y_true.length) {
                 const res = calculateNRI_IDI(pred1.y_true, pred1.y_pred, pred2.y_pred)
                 cmp.reclassification = { time_point: t, nri: res.nri, idi: res.idi }
             }
        }
        comparisonMetrics.value = cmp
        showComparisonDialog.value = true
    }

    // --- 健康状况 ---
    const fetchHealthStatus = async () => {
        if (!metadata.value || !datasetId.value) return
        try {
            const { data } = await api.post('/statistics/check-health', {
                dataset_id: datasetId.value,
                variables: metadata.value.variables.map(v => v.name)
            })
            const map = {}
            data.report.forEach(item => { map[item.variable] = item })
            varHealthMap.value = map
        } catch (e) { console.error("Health fetch failed", e) }
    }

    watch(metadata, (newVal) => { if (newVal) fetchHealthStatus() }, { immediate: true })

    // --- 模型切换逻辑 ---
    watch(() => config.model_type, (newType) => {
        if (newType === 'cox') {
            if (typeof config.target !== 'object' || config.target === null) {
                config.target = { time: coxTarget.time, event: coxTarget.event }
            } else {
                coxTarget.time = config.target.time || null
                coxTarget.event = config.target.event || null
            }
        } else if (typeof config.target === 'object') {
            config.target = null
        }
        results.value = null
    })

    const topResult = computed(() => {
        if (!results.value || !results.value.summary) return null
        const sigVars = results.value.summary.filter(v => v.p_value < 0.05)
        if (sigVars.length === 0) return null
        let top = null
        const type = config.model_type
        if (type === 'logistic') top = sigVars.reduce((prev, curr) => curr.or > prev.or ? curr : prev, sigVars[0])
        else if (type === 'cox') top = sigVars.reduce((prev, curr) => curr.hr > prev.hr ? curr : prev, sigVars[0])
        else top = sigVars.reduce((prev, curr) => Math.abs(curr.coef) > Math.abs(prev.coef) ? curr : prev, sigVars[0])
        if (!top) return null
        return {
            p_value: top.p_value,
            effectSize: type === 'logistic' ? top.or : (type === 'cox' ? top.hr : top.coef),
            desc: `变量 **${top.variable}** 对结果影响最为显著。`
        }
    })

    return {
        // State
        config, coxTarget, results, loading, activeResultTab, varHealthMap,
        showSelectionDialog, selectionLoading, selectionResults, selectionParams,
        isSuggesting, isInterpreting, aiSuggestedFeatures,
        collinearityWarning, checkingCollinearity,
        evaluationTimePoint, baselineResult, showComparisonDialog, comparisonMetrics,
        chartData,
        
        // Computed
        variableOptions, isTargetSet, maxImportance, targetOptions, featureOptions,
        timeOptions, eventOptions, selectedCategoricalVars,
        availableTimePoints, currentExtendedMetrics, activePlots, nomogramData,
        topResult,
        
        // Actions
        syncCoxTarget, runVariableSelection, applySelection, autoSuggestRoles,
        runAIInterpretation, runModel, exportResults, copyMethodology,
        setAsBaseline, compareWithBaseline, fetchHealthStatus
    }
}
