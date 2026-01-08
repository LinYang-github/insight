import { defineStore } from 'pinia'
import api from '../api/client'

export const useUserStore = defineStore('user', {
    state: () => ({
        user: null,
        token: localStorage.getItem('token') || null
    }),
    getters: {
        isAuthenticated: (state) => !!state.token
    },
    actions: {
        async login(username, password) {
            const response = await api.post('/auth/login', { username, password })
            this.token = response.data.token
            localStorage.setItem('token', this.token)
            // fetch user info if needed, or just store username
            this.user = { username: response.data.username }
        },
        async register(username, email, password) {
            await api.post('/auth/register', { username, email, password })
        },
        logout() {
            this.token = null
            this.user = null
            localStorage.removeItem('token')
            location.reload()
        }
    }
})
