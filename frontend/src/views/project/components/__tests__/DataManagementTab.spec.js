
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import DataManagementTab from '../DataManagementTab.vue'
import { ElCard, ElTable, ElTableColumn, ElButton, ElButtonGroup, ElTag, ElTree, ElRadioGroup, ElRadioButton, ElIcon } from 'element-plus'

// Stub Element Plus components
const globalStubs = {
    ElCard: true,
    ElTable: true,
    ElTableColumn: true,
    ElButton: true,
    ElButtonGroup: true,
    ElTag: true,
    ElTree: true,
    ElRadioGroup: true,
    ElRadioButton: true,
    ElIcon: true,
    ElEmpty: true,
    ElPopover: true,
    ElDialog: true,
    ElForm: true,
    ElFormItem: true,
    ElInput: true
}

describe('DataManagementTab.vue', () => {
    const mockDatasets = [
        { id: 1, name: 'root.csv', created_at: '2025-01-01', parent_id: null, action_type: null },
        { id: 2, name: 'derived_imputed.csv', created_at: '2025-01-02', parent_id: 1, action_type: 'impute', action_log: '{"age": "mean"}' },
        { id: 3, name: 'derived_psm.csv', created_at: '2025-01-03', parent_id: 1, action_type: 'psm' }
    ]

    it('renders list view by default', () => {
        const wrapper = mount(DataManagementTab, {
            props: { datasets: mockDatasets, activeDatasetId: 1 },
            global: { stubs: globalStubs }
        })

        expect(wrapper.findComponent({ name: 'ElTable' }).exists()).toBe(true)
        expect(wrapper.findComponent({ name: 'ElTree' }).exists()).toBe(false)
    })

    it('switches to tree view', async () => {
        const wrapper = mount(DataManagementTab, {
            props: { datasets: mockDatasets, activeDatasetId: 1 },
            global: { stubs: globalStubs }
        })

        // Find radio group and simulate change (requires understanding how your toggle works, 
        // usually easier to modify internal state if possible or rely on simple v-model stub behavior)
        // Since we stubbed ElRadioGroup, we won't get real v-model updates unless we manually emit or interact carefully.
        // For unit test simplicity in Vue Test Utils, often we test the logic separately or use shallowMount.
        // Let's modify component vm directly for test stability
        wrapper.vm.viewMode = 'tree'
        await wrapper.vm.$nextTick()

        expect(wrapper.findComponent({ name: 'ElTable' }).exists()).toBe(false)
        expect(wrapper.findComponent({ name: 'ElTree' }).exists()).toBe(true)

        // internal tree data structure check
        const treeData = wrapper.vm.lineageTreeData
        expect(treeData.length).toBe(1) // 1 root
        expect(treeData[0].id).toBe(1)
        expect(treeData[0].children.length).toBe(2) // 2 children (impute, psm)
    })

    it('computes lineage tree correctly', () => {
        const wrapper = mount(DataManagementTab, {
            props: { datasets: mockDatasets },
            global: { stubs: globalStubs }
        })

        const tree = wrapper.vm.lineageTreeData
        expect(tree[0].label).toBe('root.csv')
        expect(tree[0].children[0].original.action_type).toBe('impute')
    })
})
