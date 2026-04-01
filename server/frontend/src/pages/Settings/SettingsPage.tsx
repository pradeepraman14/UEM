import { useQuery } from '@tanstack/react-query'
import { Typography, Card, Empty } from 'antd'
import { apiClient } from '@/api/client'

const { Title } = Typography

export default function SettingsPage() {
  return (
    <div>
      <div className="page-header">
        <Title level={4} style={{ margin: 0 }}>Settings</Title>
      </div>
      <Card>
        <Empty description="Loading Settings data..." />
      </Card>
    </div>
  )
}
