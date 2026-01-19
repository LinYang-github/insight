import { computed } from 'vue'

/**
 * useVariableOptions
 * 
 * 这是一个公共 Composables，用于统一管理和转换数据集变量列表。
 * 
 * @param {Ref|Computed} metadata - 包含变量定义的元数据对象
 * @param {Ref} varHealthMap - 可选，包含变量健康状态检查的结果
 */
export function useVariableOptions(metadata, varHealthMap = null) {
  
  const allOptions = computed(() => {
    if (!metadata.value || !metadata.value.variables) return []
    
    return metadata.value.variables.map(v => {
      const option = {
        label: v.name,
        value: v.name,
        type: v.type,
        // 原始属性保留供高级用途
        raw: v
      }
      
      // 如果提供了健康检查数据，则注入状态
      if (varHealthMap && varHealthMap.value && varHealthMap.value[v.name]) {
        const h = varHealthMap.value[v.name]
        option.status = h.status
        option.msg = h.message
      } else {
        option.status = 'unknown'
        option.msg = ''
      }
      
      return option
    })
  })

  // 数值型变量 (Continuous/Float/Int)
  const numericOptions = computed(() => {
    return allOptions.value.filter(opt => 
      ['continuous', 'float', 'int'].includes(opt.type)
    )
  })

  // 类别型变量 (Categorical/String/Category)
  const categoricalOptions = computed(() => {
    return allOptions.value.filter(opt => 
      ['categorical', 'category', 'string', 'boolean'].includes(opt.type)
    )
  })

  return {
    allOptions,
    numericOptions,
    categoricalOptions
  }
}
