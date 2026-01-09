
import client from './client'

export const runValidation = () => {
    return client.post('/validation/run')
}

export const getBenchmarks = () => {
    return client.get('/validation/benchmarks')
}
