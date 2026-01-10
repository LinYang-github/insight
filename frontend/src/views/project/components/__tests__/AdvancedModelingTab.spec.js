import { vi, describe, it, expect, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AdvancedModelingTab from '../AdvancedModelingTab.vue'
import { ElMessage } from 'element-plus'

// --- Mocks ---

// Mock API
const mockPost = vi.fn()
vi.mock('../../../../api/client', () => ({
    default: {
        post: (...args) => mockPost(...args)
    }
}))

// Mock Plotly
const mockNewPlot = vi.fn()
vi.mock('plotly.js-dist-min', () => ({
    default: {
        newPlot: (...args) => mockNewPlot(...args)
    }
}))

// Mock Element Plus Message
vi.mock('element-plus', () => ({
    ElMessage: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn()
    }
}))

describe('AdvancedModelingTab.vue', () => {
    let wrapper

    const mockProps = {
        datasetId: 101,
        metadata: {
            variables: [
                { name: 'age', type: 'continuous', min: 20, max: 90 },
                { name: 'sex', type: 'category' },
                { name: 'outcome', type: 'binary' },
                { name: 'death', type: 'binary' },
                { name: 'time_months', type: 'continuous' }
            ]
        }
    }

    const mountComponent = () => {
        return mount(AdvancedModelingTab, {
            props: mockProps,
            global: {
                stubs: {
                    'el-tabs': { template: '<div><slot /></div>' },
                    'el-tab-pane': {
                        template: '<div><span class="tab-label">{{ label }}</span><slot /></div>',
                        props: ['label']
                    },
                    'el-row': { template: '<div><slot /></div>' },
                    'el-col': { template: '<div><slot /></div>' },
                    'el-card': { template: '<div><slot name="header" /><slot /></div>' },
                    'el-alert': true,
                    'el-form': { template: '<form><slot /></form>' },
                    'el-form-item': { template: '<div><slot /></div>' },
                    'el-select': { template: '<select><slot /></select>' },
                    'el-option': { template: '<option><slot /></option>' },
                    'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
                    'el-slider': true,
                    'el-input-number': {
                        template: '<div class="stub-input-number"><input type="number" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" /></div>',
                        props: ['modelValue'],
                        emits: ['update:modelValue']
                    },
                    'model-comparison-tab': true
                }
            }
        })
    }

    beforeEach(() => {
        vi.clearAllMocks()
        wrapper = mountComponent()
    })

    // --- TC-FE-01: Nomogram Risk Calculator Logic ---
    it('TC-FE-01: Correctly calculates risk based on Nomogram points', async () => {
        // 1. Setup Mock Nomogram Data
        // Scenario: 
        // Variable 'age': 0-100 linear mapping. Coef such that val=50 -> 50 points.
        // Risk Table: 0 pts -> 0.1 risk, 100 pts -> 0.9 risk.
        const mockNomoData = {
            formula: { intercept: 0 },
            variables: [
                {
                    name: 'age',
                    min: 0,
                    max: 100,
                    points_mapping: [
                        { val: 0, pts: 0 },
                        { val: 100, pts: 100 }
                    ]
                }
            ],
            risk_table: [
                { points: 0, risk: 0.1 },
                { points: 50, risk: 0.5 },
                { points: 100, risk: 0.9 }
            ]
        }

        mockPost.mockResolvedValueOnce({ data: mockNomoData })

        // 2. Trigger Run
        wrapper.vm.nomoParams.target = 'outcome'
        wrapper.vm.nomoParams.predictors = ['age']
        await wrapper.vm.runNomogram()
        await flushPromises()

        expect(wrapper.vm.nomoData).toEqual(mockNomoData)

        // 3. Test Functionality: Set Age = 50
        // Expected Points = 50. Risk should comprise between 0.1 and 0.9.
        // Specifically, if risk table is linear (0->0.1, 100->0.9), 50->0.5.

        // We need to update the reactive dict `calcValues`
        // Note: wrapper.vm.calcValues is a Ref/Proxy
        wrapper.vm.calcValues['age'] = 50

        // Trigger computed re-eval (Vue should handle automatically)
        const risk = wrapper.vm.calculatedRisk
        expect(risk).toBeCloseTo(0.5, 2)

        // 4. Test Interpolation: Age = 25 -> Points = 25
        // Risk between 0 (0.1) and 50 (0.5) => roughly 0.3
        wrapper.vm.calcValues['age'] = 25
        expect(wrapper.vm.calculatedRisk).toBeCloseTo(0.3, 2)
    })

    // --- TC-FE-02: Subgroup Forest Plot Visualization ---
    it('TC-FE-02: Transforms Subgroup data correctly for Plotly Forest Plot', async () => {
        // 1. Mock Subgroup Response
        const mockSubgroupData = {
            forest_data: [
                {
                    variable: 'Sex',
                    p_interaction: 0.04,
                    subgroups: [
                        { level: 'Male', n: 100, est: 1.5, lower: 1.2, upper: 1.8, p: 0.01 },
                        { level: 'Female', n: 100, est: 1.0, lower: 0.8, upper: 1.2, p: 0.5 }
                    ]
                }
            ]
        }
        mockPost.mockResolvedValueOnce({ data: mockSubgroupData })

        // 2. Run
        await wrapper.vm.runSubgroup()
        await flushPromises()

        // 3. Verify Plotly Call
        expect(mockNewPlot).toHaveBeenCalled()

        const callArgs = mockNewPlot.mock.calls[0]
        const divId = callArgs[0]
        const traces = callArgs[1]

        expect(divId).toBe('forest-plot')
        expect(traces.length).toBe(1) // Single trace logic in component

        const trace = traces[0]

        // Verify X values (Effect Sizes)
        expect(trace.x).toEqual([1.5, 1.0])

        // Verify Error Bars
        // error_x.array = upper - est
        // Male: 1.8 - 1.5 = 0.3
        // Female: 1.2 - 1.0 = 0.2
        const errors = trace.error_x.array
        expect(errors[0]).toBeCloseTo(0.3)
        expect(errors[1]).toBeCloseTo(0.2)

        // Verify Annotations (Labels)
        // We can't easily check layout annotations deep inside, 
        // but we can check if data was processed.
    })

    // --- TC-FE-03: API Error Handling ---
    it('TC-FE-03: Handles API Failure Gracefully', async () => {
        // 1. Mock Failure (Singular Matrix)
        const errorMessage = 'Singular Matrix Detected'
        mockPost.mockRejectedValueOnce({
            response: {
                data: { message: errorMessage }
            }
        })

        // 2. Trigger RCS Run
        await wrapper.vm.runRCS()
        await flushPromises()

        // 3. Verify State
        expect(wrapper.vm.rcsLoading).toBe(false)
        expect(wrapper.vm.rcsData).toBeNull()

        // 4. Verify Message
        expect(ElMessage.error).toHaveBeenCalledWith(errorMessage)
    })

    // --- Basic Render Test ---
    it('renders all tabs', () => {
        expect(wrapper.text()).toContain('限制性立方样条 (RCS)')
        expect(wrapper.text()).toContain('亚组分析 (Subgroup)')
        expect(wrapper.text()).toContain('竞争风险 (Competing Risks)')
        expect(wrapper.text()).toContain('列线图 (Nomogram)')
    })
})
