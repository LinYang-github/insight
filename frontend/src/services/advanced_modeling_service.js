import api from '@/api/client'

export default {
    /**
     * Run model comparison (AUC, NRI, IDI)
     * @param {Object} payload 
     * @returns {Promise<Array>} comparison_data
     */
    async compareModels(payload) {
        try {
            const { data } = await api.post('/advanced/compare-models', payload)
            // Backend returns List of Model Results directly
            return data
        } catch (error) {
            throw error.response?.data || error
        }
    }
}
