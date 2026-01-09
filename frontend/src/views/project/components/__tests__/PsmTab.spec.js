
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import PsmTab from '../PsmTab.vue'

// Mock API
vi.mock('../../../api/client', () => ({
    default: {
        post: vi.fn(() => Promise.resolve({
            data: {
                stats: { n_matched: 100 },
                balance: []
            }
        }))
    }
}))

// Mock Plotly
vi.mock('plotly.js-dist-min', () => ({
    default: {
        newPlot: vi.fn()
    }
}))

const globalStubs = {
    'el-row': { template: '<div><slot/></div>' },
    'el-col': { template: '<div><slot/></div>' },
    'el-card': { template: '<div><slot/><slot name="header"/></div>' },
    'el-form': { template: '<form><slot/></form>' },
    'el-form-item': { template: '<div><slot/></div>' },
    'el-select': { template: '<select><slot/></select>' },
    'el-option': { template: '<option></option>' },
    'el-button': { template: '<button @click="$emit(\'click\')"><slot/></button>' },
    'el-alert': { template: '<div><slot/></div>' },
    'el-checkbox': { template: '<input type="checkbox"><slot/></input>' },
    'el-result': { template: '<div>Result</div>' },
    'el-table': { template: '<table><slot/></table>' },
    'el-table-column': { template: '<th></th>' },
    'el-tooltip': { template: '<div><slot/></div>' },
    'el-icon': true,
    'el-tag': true,
    'el-empty': true,
    // StepWizard stub? 
    // Actually we want to test interaction with StepWizard, so we probably shouldn't stub it fully
    // But StepWizard uses el-steps which we might want to stub.
    'el-steps': { template: '<div><slot/></div>' },
    'el-step': { template: '<div></div>' }
}

describe('PsmTab.vue', () => {
    it('renders StepWizard', () => {
        const wrapper = mount(PsmTab, {
            global: { stubs: globalStubs },
            props: {
                datasetId: 1,
                metadata: { variables: [{ name: 'age' }, { name: 'treatment' }] }
            }
        })

        expect(wrapper.text()).toContain('选择处理组变量')
        expect(wrapper.findComponent({ name: 'StepWizard' }).exists()).toBe(true)
    })
})
