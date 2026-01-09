import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ClinicalTab from '../ClinicalTab.vue'
import api from '../../../../api/client'
import { ElMessage } from 'element-plus'

// Mock dependencies
vi.mock('../../../../api/client')
vi.mock('element-plus', () => ({
    ElMessage: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn()
    }
}))

const mockDataset = { dataset_id: 101, name: 'Test Dataset' }
const mockMetadata = {
    variables: [
        { name: 'Scr', type: 'continuous' },
        { name: 'Age', type: 'continuous' },
        { name: 'Height', type: 'continuous' },
        { name: 'Sex', type: 'categorical' },
        { name: 'Race', type: 'categorical' }
    ]
}

describe('ClinicalTab.vue', () => {
    let wrapper

    beforeEach(() => {
        vi.clearAllMocks()
        wrapper = mount(ClinicalTab, {
            props: {
                dataset: mockDataset,
                metadata: mockMetadata
            },
            global: {
                stubs: {
                    'el-row': { template: '<div><slot /></div>' },
                    'el-col': { template: '<div><slot /></div>' },
                    'el-card': { template: '<div><slot name="header" /><slot /></div>' },
                    'el-collapse': { template: '<div><slot /></div>' },
                    'el-collapse-item': { template: '<div>{{ title }}<slot /></div>', props: ['title'] },
                    'el-radio-group': { template: '<div><slot /></div>' },
                    'el-radio': { template: '<button><slot /></button>', props: ['label'] },
                    'el-alert': true,
                    'el-icon': true,
                    'el-form': { template: '<form><slot /></form>' },
                    'el-form-item': { template: '<div><slot /></div>' },
                    'el-select': { template: '<select><slot /></select>', props: ['modelValue'], emits: ['update:modelValue'] },
                    'el-option': { template: '<option :value="value">{{ label }}</option>', props: ['label', 'value'] },
                    'el-popover': { template: '<div><slot name="reference" /><slot /></div>' },
                    'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>', props: ['disabled', 'loading'] },
                    'el-tabs': { template: '<div><slot /></div>' },
                    'el-tab-pane': { template: '<div><slot /></div>' },
                    'el-input': { template: '<input />' },
                }
            }
        })
    })

    it('renders the toolbox correctly', () => {
        expect(wrapper.text()).toContain('临床工具箱')
        expect(wrapper.text()).toContain('eGFR 自动计算器')
    })

    it('validates input for calculation', async () => {
        await wrapper.vm.$nextTick()
        expect(wrapper.vm.canCalculate).toBeFalsy()

        wrapper.vm.params.scr = 'Scr'
        wrapper.vm.params.age = 'Age'
        wrapper.vm.params.sex = 'Sex'

        expect(wrapper.vm.canCalculate).toBeTruthy()
    })

    it('calls API correctly for eGFR derivation', async () => {
        wrapper.vm.params.scr = 'Scr'
        wrapper.vm.params.age = 'Age'
        wrapper.vm.params.sex = 'Sex'

        api.post.mockResolvedValueOnce({
            data: { new_dataset: { id: 102, name: 'Derived DS' } }
        })

        await wrapper.vm.handleDerive()

        expect(api.post).toHaveBeenCalledWith('/clinical/derive-egfr', expect.objectContaining({
            dataset_id: 101,
            type: 'egfr_ckdepi2021',
            params: {
                scr: 'Scr',
                age: 'Age',
                sex: 'Sex',
                race: '',
                height: ''
            }
        }))

        await flushPromises()
        expect(ElMessage.success).toHaveBeenCalled()
        expect(wrapper.emitted()['dataset-updated']).toBeTruthy()
        expect(wrapper.emitted()['dataset-updated'][0][0]).toEqual({ id: 102, name: 'Derived DS' })
    })
})
