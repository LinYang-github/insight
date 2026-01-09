
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import InterpretationPanel from '../InterpretationPanel.vue'

describe('InterpretationPanel.vue', () => {
    it('renders nothing if pValue is missing', () => {
        const wrapper = mount(InterpretationPanel, {
            props: { pValue: null }
        })
        expect(wrapper.find('.interpretation-panel').exists()).toBe(false)
    })

    it('renders significant result correctly', () => {
        const wrapper = mount(InterpretationPanel, {
            props: {
                pValue: 0.001,
                testName: 'T-test',
                selectionReason: 'Reason'
            }
        })

        expect(wrapper.text()).toContain('智能分析结论')
        expect(wrapper.text()).toContain('差异显著 (P < 0.05)')
        expect(wrapper.text()).toContain('分析方法:T-test')

        // Check if red style class is applied (by checking html or class existence if possible, 
        // but here we just check text content mostly)
        const html = wrapper.find('.summary-text').html()
        expect(html).toContain('class="significant"')
    })

    it('renders non-significant result correctly', () => {
        const wrapper = mount(InterpretationPanel, {
            props: {
                pValue: 0.5
            }
        })

        expect(wrapper.text()).toContain('无显著差异 (P > 0.05)')
        const html = wrapper.find('.summary-text').html()
        expect(html).toContain('class="non-significant"')
    })

    it('handles string input like <0.001', () => {
        const wrapper = mount(InterpretationPanel, {
            props: {
                pValue: '<0.001'
            }
        })

        expect(wrapper.text()).toContain('差异显著')
    })

    it('interprets Effect Size > 1 (Risk Increased)', () => {
        const wrapper = mount(InterpretationPanel, {
            props: {
                pValue: 0.01,
                effectSize: 2.5
            }
        })
        const html = wrapper.find('.summary-text').html()
        expect(html).toContain('风险增加 2.50 倍')
        expect(html).toContain('class="risk-inc"')
    })

    it('interprets Effect Size < 1 (Risk Reduced)', () => {
        const wrapper = mount(InterpretationPanel, {
            props: {
                pValue: 0.01,
                effectSize: 0.6
            }
        })
        const html = wrapper.find('.summary-text').html()
        expect(html).toContain('风险降低 40.0%')
        expect(html).toContain('class="risk-dec"')
    })
})
