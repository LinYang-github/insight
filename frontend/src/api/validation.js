
import client from './client'

export const runValidation = (params = {}) => {
    return client.post('/validation/run', params)
}

export const getBenchmarks = () => {
    return client.get('/validation/benchmarks')
}

export const downloadDataset = (filename) => {
    return client.get(`/validation/data/${filename}`, { responseType: 'blob' })
}

export const generateReport = (reportData) => {
    return client.post('/validation/report', reportData, { responseType: 'blob' })
}
