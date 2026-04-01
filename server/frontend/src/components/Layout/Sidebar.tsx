import { useLocation, useNavigate } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  LaptopOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  SafetyOutlined,
  FileProtectOutlined,
  LockOutlined,
  DesktopOutlined,
  BellOutlined,
  BarChartOutlined,
  TeamOutlined,
  GroupOutlined,
  SettingOutlined,
  CloudSyncOutlined,
} from '@ant-design/icons'
import { useNotificationStore } from '@/store/notifications'
import { Badge } from 'antd'

const { Sider } = Layout

interface SidebarProps {
  collapsed: boolean
  onCollapse: (v: boolean) => void
}

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/devices', icon: <LaptopOutlined />, label: 'Devices' },
  { key: '/inventory', icon: <DatabaseOutlined />, label: 'Inventory' },
  { key: '/software', icon: <AppstoreOutlined />, label: 'Software' },
  { key: '/patches', icon: <CloudSyncOutlined />, label: 'Patches' },
  { key: '/policies', icon: <FileProtectOutlined />, label: 'Policies' },
  { key: '/compliance', icon: <SafetyOutlined />, label: 'Compliance' },
  { key: '/bitlocker', icon: <LockOutlined />, label: 'BitLocker' },
  { key: '/remote-tools', icon: <DesktopOutlined />, label: 'Remote Tools' },
  { key: '/alerts', icon: <BellOutlined />, label: 'Alerts' },
  { key: '/reports', icon: <BarChartOutlined />, label: 'Reports' },
  { type: 'divider' as const },
  { key: '/users', icon: <TeamOutlined />, label: 'Users' },
  { key: '/groups', icon: <GroupOutlined />, label: 'Groups' },
  { key: '/settings', icon: <SettingOutlined />, label: 'Settings' },
]

export default function Sidebar({ collapsed, onCollapse }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const unreadCount = useNotificationStore((s) => s.unreadCount)

  const activeKey = '/' + location.pathname.split('/')[1]

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      width={220}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 100,
      }}
    >
      {/* Logo */}
      <div
        style={{
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 16px',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          cursor: 'pointer',
        }}
        onClick={() => navigate('/dashboard')}
      >
        <span style={{ fontSize: 20 }}>🖥️</span>
        {!collapsed && (
          <span style={{ color: '#fff', marginLeft: 8, fontWeight: 700, fontSize: 15, letterSpacing: 0.5 }}>
            UEM Console
          </span>
        )}
      </div>

      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[activeKey]}
        onClick={({ key }) => navigate(key)}
        style={{ borderRight: 0, marginTop: 8 }}
        items={menuItems.map((item) => {
          if (item.type === 'divider') {
            return { type: 'divider', style: { borderColor: 'rgba(255,255,255,0.1)' } }
          }
          return {
            key: item.key,
            icon: item.key === '/alerts' ? (
              <Badge count={unreadCount} size="small" offset={[6, 0]}>
                {item.icon}
              </Badge>
            ) : item.icon,
            label: item.label,
          }
        })}
      />
    </Sider>
  )
}
