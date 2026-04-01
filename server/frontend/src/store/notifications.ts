import { create } from 'zustand'
import type { Alert } from '@/types'

interface NotificationState {
  alerts: Alert[]
  unreadCount: number
  addAlert: (alert: Alert) => void
  markAllRead: () => void
  removeAlert: (id: string) => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
  alerts: [],
  unreadCount: 0,
  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 100),
      unreadCount: state.unreadCount + 1,
    })),
  markAllRead: () => set({ unreadCount: 0 }),
  removeAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.filter((a) => a.id !== id),
    })),
}))
