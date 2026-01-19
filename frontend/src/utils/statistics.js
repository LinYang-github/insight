/**
 * 医学统计常用工具函数
 */

/**
 * 手动计算轻量级的 NRI 和 IDI（前端预览用）。
 * 严谨的 NRI/IDI 计算通常建议在后端通过 bootstrap 获取置信区间。
 * 
 * @param {Array} y_true - 真实结局 (0/1)
 * @param {Array} p_old - 旧模型的预测概率
 * @param {Array} p_new - 新模型的预测概率
 * @returns {Object} { nri, idi }
 */
export function calculateNRI_IDI(y_true, p_old, p_new) {
    let up_event = 0, down_event = 0, n_event = 0;
    let up_nonevent = 0, down_nonevent = 0, n_nonevent = 0;
    let idi_event_sum = 0, idi_nonevent_sum = 0;

    for (let i = 0; i < y_true.length; i++) {
        const diff = p_new[i] - p_old[i];
        if (y_true[i] === 1) {
            n_event++;
            if (p_new[i] > p_old[i]) up_event++;
            if (p_new[i] < p_old[i]) down_event++;
            idi_event_sum += diff;
        } else {
            n_nonevent++;
            if (p_new[i] < p_old[i]) down_nonevent++; // Better for non-event
            if (p_new[i] > p_old[i]) up_nonevent++;   // Worse
            idi_nonevent_sum += diff;
        }
    }

    if (n_event === 0 || n_nonevent === 0) return { nri: 0, idi: 0 };

    const nri_event = (up_event - down_event) / n_event;
    const nri_nonevent = (down_nonevent - up_nonevent) / n_nonevent;
    const nri = nri_event + nri_nonevent;

    const idi = (idi_event_sum / n_event) - (idi_nonevent_sum / n_nonevent);
    
    return { nri, idi };
}
