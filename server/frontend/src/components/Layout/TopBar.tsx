import { useNavigate } from 'react-router-dom'
import { Layout, Button, Dropdown, Avatar, Space, Badge, Typography } from 'antd'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/store/auth'
import { useNotificationStore } from '@/store/notifications'
import { authApi } from '@/api/auth'
import toast from 'react-hot-toast'

const { Header } = Layout

interface TopBarProps {
  collapsed: boolean
  onCollapse: (v: boolean) => void
}

export default function TopBar({ collapsed, onCollapse }: TopBarProps) {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  const unreadCount = useNotificationStore((s) => s.unreadCount)
  const markAllRead = useNotificationStore((s) => s.markAllRead)

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore
    }
    clearAuth()
    navigate('/login')
    toast.success('Logged out')
  }

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: user?.full_name || 'Profile',
      disabled: true,
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
      onClick: () => navigate('/settings'),
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      danger: true,
      onClick: handleLogout,
    },
  ]

  return (
    <Header
      style={{
        background: '#fff',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #f0f0f0',
        position: 'sticky',
        top: 0,
        zIndex: 99,
        height: 56,
      }}
    >
      <Space size={12}>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => onCollapse(!collapsed)}
          style={{ fontSize: 16 }}
        />
        {collapsed && (
          <img src="/logo.png" alt="Applaude" style={{ height: 24, width: 'auto', objectFit: 'contain' }} />
        )}
      </Space>

      <Space size={8}>
        <Badge count={unreadCount} size="small">
          <Button
            type="text"
            icon={<BellOutlined />}
            onClick={() => {
              markAllRead()
              navigate('/alerts')
            }}
            style={{ fontSize: 16 }}
          />
        </Badge>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" trigger={['click']}>
          <Space style={{ cursor: 'pointer' }}>
            <Avatar
              size={32}
              style={{ backgroundColor: '#1677ff' }}
              icon={<UserOutlined />}
            />
            <Typography.Text strong style={{ fontSize: 13 }}>
              {user?.full_name?.split(' ')[0] || 'Admin'}
            </Typography.Text>
          </Space>
        </Dropdown>
      </Space>
    </Header>
  )
}
