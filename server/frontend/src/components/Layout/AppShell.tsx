import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Layout } from 'antd'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useQueryClient } from '@tanstack/react-query'

const { Content } = Layout

export default function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const queryClient = useQueryClient()

  // Global WebSocket for real-time events
  useWebSocket((message) => {
    if (message.type === 'device_status_changed') {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    }
    if (message.type === 'new_alert') {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    }
    if (message.type === 'command_result') {
      queryClient.invalidateQueries({ queryKey: ['commands'] })
    }
  })

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sidebar collapsed={collapsed} onCollapse={setCollapsed} />
      <Layout style={{ marginLeft: collapsed ? 80 : 220, transition: 'margin-left 0.2s' }}>
        <TopBar collapsed={collapsed} onCollapse={setCollapsed} />
        <Content
          style={{
            margin: '16px',
            padding: '24px',
            background: '#fff',
            borderRadius: '8px',
            minHeight: 360,
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
