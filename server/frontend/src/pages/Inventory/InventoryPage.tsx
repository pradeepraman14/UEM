import { useQuery } from '@tanstack/react-query'
import { Typography, Card, Empty } from 'antd'
import { apiClient } from '@/api/client'

const { Title } = Typography

export default function InventoryPage() {
  return (
    <div>
      <div className="page-header">
        <Title level={4} style={{ margin: 0 }}>Inventory</Title>
      </div>
      <Card>
        <Empty description="Loading Inventory data..." />
      </Card>
    </div>
  )
}
