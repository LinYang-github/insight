import { defineStore } from 'pinia'
import api from '../api/client'

export const useUserStore = defineStore('user', {
    state: () => ({
        user: JSON.parse(localStorage.getItem('user')) || null,
        token: localStorage.getItem('token') || null
    }),
    getters: {
        isAuthenticated: (state) => !!state.token
    },
    actions: {
        async login(username, password) {
            const response = await api.post('/auth/login', { username, password })
            this.token = response.data.token
            this.user = { username: response.data.username }
            localStorage.setItem('token', this.token)
            localStorage.setItem('user', JSON.stringify(this.user))
            // Apply theme if saved in user settings? User settings are fetched in Settings, 
            // maybe we should fetch them here too. For now KISS.
            this.applyTheme(response.data.settings?.theme || 'light')
        },
        async register(username, email, password) {
            await api.post('/auth/register', { username, email, password })
        },
        logout() {
            this.token = null
            this.user = null
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            location.reload()
        },
        applyTheme(theme) {
            if (theme === 'dark') {
                document.documentElement.classList.add('dark')
            } else {
                document.documentElement.classList.remove('dark')
            }
        }
    }
})
