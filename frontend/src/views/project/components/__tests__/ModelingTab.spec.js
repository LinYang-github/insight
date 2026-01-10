import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ModelingTab from '../ModelingTab.vue'
import api from '../../../../api/client'
import { ElMessage } from 'element-plus'
import Plotly from 'plotly.js-dist-min'

vi.mock('../../../../api/client')
vi.mock('plotly.js-dist-min', () => ({
    default: {
        newPlot: vi.fn(),
        downloadImage: vi.fn()
    }
}))
vi.mock('element-plus', () => ({
    ElMessage: {
        success: vi.fn(),
        error: vi.fn()
    }
}))

const mockMetadata = {
    variables: [
        { name: 'Y', type: 'binary' },
        { name: 'X1', type: 'continuous' },
        { name: 'X2', type: 'categorical' }
    ]
}

describe('ModelingTab.vue', () => {
    let wrapper

    beforeEach(() => {
        vi.clearAllMocks()
        wrapper = mount(ModelingTab, {
            props: {
                projectId: 'p1',
                datasetId: 101,
                metadata: mockMetadata
            },
            global: {
                stubs: {
                    'el-row': { template: '<div><slot /></div>' },
                    'el-col': { template: '<div><slot /></div>' },
                    'el-card': { template: '<div><slot name="header" /><slot /></div>' },
                    'el-form': { template: '<form><slot /></form>' },
                    'el-form-item': { template: '<div><slot /></div>' },
                    'el-select': { template: '<select><slot /></select>', props: ['modelValue'], emits: ['update:modelValue'] },
                    'el-option': { template: '<option :value="value">{{ label }}</option>', props: ['label', 'value'] },
                    'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
                    'el-alert': { template: '<div><slot /></div>' },
                    'el-descriptions': { template: '<div><slot /></div>' },
                    'el-descriptions-item': { template: '<div><slot /></div>' },
                    'el-tabs': { template: '<div><slot /></div>' },
                    'el-tab-pane': { template: '<div><slot /></div>' },
                    'el-table': { template: '<div><slot /></div>' },
                    'el-table-column': true,
                    'el-input-number': true,
                    'el-tooltip': true,
                    'el-icon': true,
                    'el-dropdown': true,
                    'InterpretationPanel': {
                        template: '<div class="interpretation-panel-stub">{{ pValue }} | {{ effectSize }}</div>',
                        props: ['pValue', 'effectSize']
                    }
                }
            }
        })
    })

    it('renders config panel', () => {
        expect(wrapper.text()).toContain('模型配置')
        expect(wrapper.text()).toContain('逻辑回归')
    })

    it('displays InterpretationPanel when significant result exists', async () => {
        // Setup config
        wrapper.vm.config.target = 'Y'
        wrapper.vm.config.features = ['X1', 'X2']

        // Mock API response with significant result
        const mockRes = {
            model_type: 'logistic',
            summary: [
                { variable: 'X1', p_value: 0.001, or: 2.5, coef: 0.9 },
                { variable: 'X2', p_value: 0.6, or: 1.1, coef: 0.1 }
            ],
            metrics: { auc: 0.85 }
        }

        api.post.mockResolvedValueOnce({ data: { results: mockRes } })

        await wrapper.vm.runModel()
        await flushPromises()

        // Check API call
        expect(api.post).toHaveBeenCalled()

        // Check InterpretationPanel Rendering
        const panel = wrapper.find('.interpretation-panel-stub')
        expect(panel.exists()).toBe(true)
        expect(panel.text()).toContain('0.001') // pValue
        expect(panel.text()).toContain('2.5')   // effectSize

        // Check topResult computation
        expect(wrapper.vm.topResult.desc).toContain('变量 **X1** 对结果影响最为显著')
    })

    it('renders reference level settings for categorical variables', async () => {
        // Mock categorical var with categories
        const metadataWithCat = {
            variables: [
                { name: 'Sex', type: 'categorical', categories: ['Male', 'Female'] },
                { name: 'Age', type: 'continuous' }
            ]
        }

        const w = mount(ModelingTab, {
            props: {
                projectId: 'p1',
                datasetId: 101,
                metadata: metadataWithCat
            },
            global: {
                // Same stubs ...
                stubs: {
                    'el-row': { template: '<div><slot /></div>' },
                    'el-col': { template: '<div><slot /></div>' },
                    'el-card': { template: '<div><slot name="header" /><slot /></div>' },
                    'el-form': { template: '<form><slot /></form>' },
                    'el-form-item': { template: '<div><slot /></div>' },
                    'el-select': { template: '<select><slot /></select>', props: ['modelValue'], emits: ['update:modelValue'] },
                    'el-option': { template: '<option :value="value">{{ label }}</option>', props: ['label', 'value'] },
                    'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
                    'el-alert': { template: '<div><slot /></div>' },
                    'el-descriptions': { template: '<div><slot /></div>' },
                    'el-descriptions-item': { template: '<div><slot /></div>' },
                    'el-tabs': { template: '<div><slot /></div>' },
                    'el-tab-pane': { template: '<div><slot /></div>' },
                    'el-table': { template: '<div><slot /></div>' },
                    'el-collapse': { template: '<div><slot /></div>' },
                    'el-collapse-item': { template: '<div><slot /></div>' },
                    'el-table-column': true,
                    'el-input-number': true,
                    'el-tooltip': true,
                    'el-icon': true,
                    'el-dropdown': true,
                    'InterpretationPanel': true
                }
            }
        })

        // Select 'Sex'
        w.vm.config.features = ['Sex']
        await flushPromises()
        await w.vm.$nextTick()

        expect(w.text()).toContain('Sex Reference:')
        expect(w.text()).toContain('设置为基准的类别')
    })

    it('automatically suggests variable roles based on names', async () => {
        const metadataSmart = {
            variables: [
                { name: 'PatientID', type: 'string', unique_count: 100 },
                { name: 'Age', type: 'continuous', unique_count: 50 },
                { name: 'Sex', type: 'binary', unique_count: 2 },
                { name: 'OS_Time', type: 'continuous', unique_count: 90 }, // Should be Time
                { name: 'OS_Status', type: 'binary', unique_count: 2 },     // Should be Event
                { name: 'TumorSize', type: 'continuous', unique_count: 40 }
            ]
        }

        const w = mount(ModelingTab, {
            props: { projectId: 'p1', datasetId: 101, metadata: metadataSmart },
            global: {
                stubs: {
                    'el-row': true, 'el-col': true, 'el-card': true, 'el-form': true, 'el-form-item': true,
                    'el-select': true, 'el-option': true, 'el-button': true, 'el-alert': true,
                    'el-descriptions': true, 'el-descriptions-item': true, 'el-tabs': true, 'el-tab-pane': true,
                    'el-table': true, 'el-collapse': true, 'el-collapse-item': true, 'el-table-column': true,
                    'el-input-number': true, 'el-tooltip': true, 'el-icon': true, 'el-dropdown': true,
                    'InterpretationPanel': true, 'el-tag': true
                }
            }
        })

        // Wait for immediate watch
        await wrapper.vm.$nextTick()

        // Check heuristics
        // Default is Logistic, so 'OS_Status' should be target
        expect(w.vm.config.target).toBe('OS_Status')
        // Features should contain Age, Sex, TumorSize, OS_Time (OS_Time is feature if not Cox)
        expect(w.vm.config.features).toContain('Age')
        expect(w.vm.config.features).toContain('Sex')
        expect(w.vm.config.features).not.toContain('PatientID')
    })

    it('renders Assumptions tab and VIF plot container', async () => {
        const mockResVIF = {
            model_type: 'logistic',
            summary: [
                { variable: 'Age', p_value: 0.01, vif: '1.2', or: 1.1, coef: 0.1 },
                { variable: 'X', p_value: 0.6, vif: '6.0', or: 1.0, coef: 0.0 }
            ],
            plots: {}
        }

        // Force results
        wrapper.vm.results = mockResVIF
        await wrapper.vm.$nextTick()

        expect(wrapper.text()).toContain('假设检验 (Assumptions)')
        // Check VIF div exists
        expect(wrapper.find('#vif-plot').exists()).toBe(true)
    })

    it('does not display InterpretationPanel when no significant variables', async () => {
        const mockRes = {
            model_type: 'logistic',
            summary: [
                { variable: 'X1', p_value: 0.1, or: 1.2 },
                { variable: 'X2', p_value: 0.6, or: 1.1 }
            ],
            metrics: { auc: 0.6 }
        }

        api.post.mockResolvedValueOnce({ data: { results: mockRes } })

        await wrapper.vm.runModel()
        await flushPromises()

        const panel = wrapper.find('.interpretation-panel-stub')
        expect(panel.exists()).toBe(false)

        // Should show fallback alert for diag/perf info
        // (Note: finding el-alert stub by checking if text contains something from smartSummary)
        expect(wrapper.vm.smartSummary).toContain('Variables: 未发现统计学显著')
    })
})
