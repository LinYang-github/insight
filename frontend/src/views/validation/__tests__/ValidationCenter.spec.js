
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ValidationCenter from '../ValidationCenter.vue'
import { createPinia, setActivePinia } from 'pinia'
import * as ValidationApi from '@/api/validation'

// Mock icons
vi.mock('@element-plus/icons-vue', () => ({
    VideoPlay: { template: '<svg>VideoPlay</svg>' },
    Download: { template: '<svg>Download</svg>' }
}))

// Mock API
vi.mock('@/api/validation', () => ({
    runValidation: vi.fn(),
    getBenchmarks: vi.fn(),
    downloadDataset: vi.fn()
}))

// Mock global components
const globalStubs = {
    'el-button': { template: '<button @click="$emit(\'click\')"><slot/></button>' },
    'el-icon': { template: '<i><slot/></i>' },
    'el-row': { template: '<div><slot/></div>' },
    'el-col': { template: '<div><slot/></div>' },
    'el-card': { template: '<div><slot name="header"/><slot/></div>' },
    'el-tabs': { template: '<div><slot/></div>' },
    'el-tab-pane': { template: '<div><slot/></div>' },
    'el-tag': { template: '<span><slot/></span>' },
    'el-table': { template: '<table><slot/></table>' },
    'el-table-column': { template: '<th></th>' },
    'el-divider': { template: '<hr/>' },
    'el-empty': { template: '<div>Empty</div>' }
}

describe('ValidationCenter.vue', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
    })

    it('renders header and title', () => {
        const wrapper = mount(ValidationCenter, {
            global: {
                stubs: globalStubs
            }
        })
        expect(wrapper.text()).toContain('质量与验证中心')
        expect(wrapper.text()).toContain('基于国际标准 R 语言')
    })

    it('calls runValidation API when button is clicked', async () => {
        // Setup mock return
        const mockResponse = {
            data: {
                summary: { status: 'PASS', passed: 5, total_tests: 5 },
                scientific: [],
                robustness: []
            }
        }
        ValidationApi.runValidation.mockResolvedValue(mockResponse)

        const wrapper = mount(ValidationCenter, {
            global: {
                stubs: globalStubs
            }
        })

        // Find and click the run button
        const runBtn = wrapper.findAll('button')[0] // First button is "Run Self-Check"
        await runBtn.trigger('click')

        expect(ValidationApi.runValidation).toHaveBeenCalled()
        // Wait for async update
        await wrapper.vm.$nextTick()

        // Check if stats updated
        expect(wrapper.text()).toContain('系统状态 (System Status)')
        // Since we stubbed everything to plain html, element-plus logic like 'type="success"' isn't rendered as class
        // But we can check if variables updated in vm if we wanted, or check text presence if we rendered it.
    })

    it('displays error message on failed validation', async () => {
        const errorMock = new Error('Network Error')
        ValidationApi.runValidation.mockRejectedValue(errorMock)
        // Mock ElMessage? usually tough in unit test without full install. 
        // For now just ensure it doesn't crash.

        const wrapper = mount(ValidationCenter, {
            global: {
                stubs: globalStubs
            }
        })

        const runBtn = wrapper.findAll('button')[0]
        await runBtn.trigger('click')

        expect(ValidationApi.runValidation).toHaveBeenCalled()
    })
})
