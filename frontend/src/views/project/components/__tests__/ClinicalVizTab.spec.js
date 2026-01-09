import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ClinicalVizTab from '../ClinicalVizTab.vue'
import api from '../../../../api/client'
import { ElMessage } from 'element-plus'
import Plotly from 'plotly.js-dist-min'

// Mock dependencies
vi.mock('../../../../api/client')
vi.mock('element-plus', () => ({
    ElMessage: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn()
    }
}))
vi.mock('plotly.js-dist-min', () => ({
    default: {
        newPlot: vi.fn()
    }
}))

const mockMetadata = {
    variables: [
        { name: 'Outcome', type: 'binary' },
        { name: 'Age', type: 'continuous' },
        { name: 'Sex', type: 'categorical' },
        { name: 'Event', type: 'binary' }
    ]
}

describe('ClinicalVizTab.vue', () => {
    let wrapper

    beforeEach(() => {
        vi.clearAllMocks()
        wrapper = mount(ClinicalVizTab, {
            props: {
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
                    'el-radio-group': { template: '<div><slot /></div>' },
                    'el-radio': { template: '<button><slot /></button>', props: ['label'] },
                    'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
                    'el-tabs': { template: '<div><slot /></div>' },
                    'el-tab-pane': { template: '<div><slot /></div>' },
                    'el-alert': true,
                    'el-input-number': true,
                    'el-empty': true
                }
            }
        })
    })

    it('renders config panel', () => {
        expect(wrapper.text()).toContain('模型配置')
        expect(wrapper.text()).toContain('Logistic回归')
    })

    it('validates generation input', async () => {
        await wrapper.vm.generateViz()
        expect(ElMessage.warning).toHaveBeenCalledWith('请选择结局变量和至少一个预测因子')
    })

    it('calls API and renders nomogram', async () => {
        // Setup config
        wrapper.vm.config.target = 'Outcome'
        wrapper.vm.config.predictors = ['Age', 'Sex']

        // Mock API
        const mockResponse = {
            model_type: 'logistic',
            variables: [
                { name: 'Age', min: 20, max: 80, points_mapping: [] },
                { name: 'Sex', min: 0, max: 1, points_mapping: [] }
            ],
            risk_table: [{ points: 10, risk: 0.1 }],
            formula: {
                intercept: -5,
                coeffs: { Age: 0.05, Sex: 0.5 },
                model_type: 'logistic'
            }
        }
        api.post.mockResolvedValueOnce({ data: mockResponse })

        await wrapper.vm.generateViz()
        await flushPromises()

        expect(api.post).toHaveBeenCalledWith('/advanced/nomogram', expect.objectContaining({
            dataset_id: 101,
            target: 'Outcome',
            predictors: ['Age', 'Sex'],
            model_type: 'logistic'
        }))

        // Check Plotly call (needs nextTick)
        await wrapper.vm.$nextTick()
        // Wait another tick for nextTick in component?

        // We mocked Plotly as default export
        expect(Plotly.newPlot).toHaveBeenCalled()
        expect(Plotly.newPlot.mock.calls[0][0]).toBe('nomogram-plot')
    })

    it('calculates risk using interactive calculator', async () => {
        // Hydrate data manually or via generate
        wrapper.vm.vizData = {
            variables: [
                { name: 'Age', min: 20, max: 80 },
                { name: 'Sex', min: 0, max: 1 }
            ],
            formula: {
                intercept: -5,
                coeffs: { Age: 0.05, Sex: 0.5 },
                model_type: 'logistic'
            }
        }

        // Input Age=60, Sex=1
        // LP = -5 + 0.05*60 + 0.5*1 = -5 + 3 + 0.5 = -1.5
        // Risk = 1 / (1 + exp(1.5)) = 1 / (1 + 4.48) = 1 / 5.48 approx 0.18

        wrapper.vm.inputs.Age = 60
        wrapper.vm.inputs.Sex = 1

        expect(wrapper.vm.currentRisk).toBeCloseTo(0.182, 3)
    })
})
