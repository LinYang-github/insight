/**
 * 通用医学统计格式化工具 (Medical Statistics Formatters)
 */

/**
 * 格式化 P 值
 * 
 * 符合 SCI 发表规范：
 * - 极小值显示 < 0.001
 * - 大部分 P 值保留 3 位小数
 * - P > 0.05 建议保留 2 位
 * 
 * @param {number|string} p - 原始 P 值
 * @returns {string} 格式化后的字符串
 */
export function formatPValue(p) {
  const val = parseFloat(p)
  if (isNaN(val)) return '-'
  if (val < 0.001) return '< 0.001'
  if (val < 0.01) return val.toFixed(3)
  return val.toFixed(3) // 统一 3 位以保持对齐美观
}

/**
 * 格式化效应值及其置信区间 (HR/OR/RR)
 * 
 * 示例输出: 1.50 (1.20 - 1.80)
 * 
 * @param {number} val - 效应值 (如 OR/HR)
 * @param {number} lower - 置信区间下限
 * @param {number} upper - 置信区间上限
 * @param {number} precision - 保留位数
 * @returns {string} 格式化后的字符串
 */
export function formatEffectSize(val, lower, upper, precision = 2) {
  const v = parseFloat(val)
  const l = parseFloat(lower)
  const u = parseFloat(upper)
  
  if (isNaN(v) || isNaN(l) || isNaN(u)) return '-'
  
  return `${v.toFixed(precision)} (${l.toFixed(precision)} - ${u.toFixed(precision)})`
}

/**
 * 格式化普通数值
 * 
 * @param {number|string} val 
 * @param {number} precision 
 * @returns {string}
 */
export function formatNumber(val, precision = 2) {
  const v = parseFloat(val)
  if (isNaN(v)) return '-'
  return v.toFixed(precision)
}

/**
 * 格式化百分比
 * 
 * @param {number} val - 0 到 1 之间的数值
 * @returns {string} 
 */
export function formatPercent(val, precision = 1) {
    const v = parseFloat(val)
    if (isNaN(v)) return '-'
    return `${(v * 100).toFixed(precision)}%`
}
