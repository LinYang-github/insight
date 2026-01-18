import axios from 'axios'
import router from '../router'

const api = axios.create({
    baseURL: '/api', // Proxy or relative path for production
    timeout: 120000 // Increased to 120s to allow AI requests more time
})

// Request Interceptor
api.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
}, error => {
    return Promise.reject(error)
})

// Response Interceptor
api.interceptors.response.use(response => {
    return response
}, error => {
    if (error.response && error.response.status === 401) {
        localStorage.removeItem('token')
        router.push('/login')
    }
    return Promise.reject(error)
})

export default api
