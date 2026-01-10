import { vi, describe, it, expect } from 'vitest'

// Mock axios BEFORE anything else
vi.mock('axios', () => {
    return {
        default: {
            create: vi.fn().mockReturnThis(),
            interceptors: {
                request: { use: vi.fn(), eject: vi.fn() },
                response: { use: vi.fn(), eject: vi.fn() }
            },
            post: vi.fn().mockResolvedValue({
                data: {
                    distribution: {
                        type: 'numeric',
                        bins: { counts: [1, 2, 1], edges: [0, 1, 2, 3] },
                        curve: { x: [0, 1, 2], y: [0.1, 0.5, 0.1] },
                        stats: { n: 4, mean: 1.5, std: 0.5 }
                    }
                }
            })
        }
    }
})

vi.mock('plotly.js-dist-min', () => ({
    default: {
        newPlot: vi.fn(),
        purge: vi.fn()
    }
}))

import { mount } from '@vue/test-utils'
import DistributionDialog from '../DistributionDialog.vue'

describe('DistributionDialog.vue', () => {
    const mountComponent = (props = {}) => {
        return mount(DistributionDialog, {
            props: {
                datasetId: 1,
                variable: 'age',
                modelValue: true,
                ...props
            },
            global: {
                stubs: {
                    'el-dialog': {
                        template: '<div class="stub-dialog" v-if="modelValue"><slot /><p>{{ title }}</p></div>',
                        props: ['modelValue', 'title']
                    },
                    'el-descriptions': true,
                    'el-descriptions-item': true
                },
                directives: {
                    loading: vi.fn()
                }
            }
        })
    }

    it('renders title with variable name', async () => {
        const wrapper = mountComponent()
        expect(wrapper.html()).toContain('变量分布: age')
    })

    it('fetches distribution data when opened', async () => {
        const wrapper = mountComponent({ modelValue: false })
        expect(wrapper.vm.distData).toBeNull()

        await wrapper.setProps({ modelValue: true })

        // Wait for async
        await new Promise(resolve => setTimeout(resolve, 100))
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.distData).not.toBeNull()
        expect(wrapper.vm.distData.type).toBe('numeric')
    })
})
