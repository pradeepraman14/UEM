import axios from 'axios'
import { apiClient } from './client'
import type { User } from '@/types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

export const authApi = {
  login: async (email: string, password: string) => {
    const { data } = await axios.post(
      `${BASE_URL}/api/v1/auth/login`,
      { email, password },
      { withCredentials: true }
    )
    return data as { access_token: string; expires_in: number }
  },

  logout: () =>
    apiClient.post('/auth/logout', {}, { withCredentials: true }),

  getMe: () =>
    apiClient.get<User>('/users/me').then((r) => r.data),

  changePassword: (current_password: string, new_password: string) =>
    apiClient.post('/auth/change-password', { current_password, new_password }),
}
