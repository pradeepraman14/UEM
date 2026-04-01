import { useQuery } from '@tanstack/react-query'
import { Row, Col, Card, Statistic, Table, Tag, Badge, Typography, Space, Spin } from 'antd'
import {
  LaptopOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  BellOutlined,
  SafetyOutlined,
  CloudSyncOutlined,
  WifiOutlined,
} from '@ant-design/icons'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { apiClient } from '@/api/client'
import { devicesApi } from '@/api/devices'
import type { Alert } from '@/types'

const { Title, Text } = Typography

const COLORS = ['#52c41a', '#ff4d4f', '#faad14', '#1677ff']

export default function DashboardPage() {
  const { data: deviceReport, isLoading: loadingDevices } = useQuery({
    queryKey: ['reports', 'device-summary'],
    queryFn: () => apiClient.get('/reports/device-summary').then((r) => r.data),
    refetchInterval: 30_000,
  })

  const { data: patchReport } = useQuery({
    queryKey: ['reports', 'patch-compliance'],
    queryFn: () => apiClient.get('/reports/patch-compliance').then((r) => r.data),
    refetchInterval: 60_000,
  })

  const { data: alertSummary } = useQuery({
    queryKey: ['alerts', 'summary'],
    queryFn: () => apiClient.get('/alerts/summary').then((r) => r.data),
    refetchInterval: 30_000,
  })

  const { data: wsStats } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => apiClient.get('/dashboard/stats').then((r) => r.data),
    refetchInterval: 15_000,
  })

  const { data: recentAlerts } = useQuery({
    queryKey: ['alerts', 'recent'],
    queryFn: () =>
      apiClient.get('/alerts', { params: { status: 'open', limit: 5 } }).then((r) => r.data.items),
    refetchInterval: 30_000,
  })

  const { data: deviceList } = useQuery({
    queryKey: ['devices', 'recent'],
    queryFn: () => devicesApi.list({ page_size: 10 }),
    refetchInterval: 30_000,
  })

  if (loadingDevices) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    )
  }

  const totalDevices = deviceReport?.total_devices || 0
  const onlineDevices = deviceReport?.online_devices || 0
  const compliant = deviceReport?.summary?.compliant || 0
  const nonCompliant = deviceReport?.summary?.non_compliant || 0

  const complianceData = [
    { name: 'Compliant', value: compliant },
    { name: 'Non-Compliant', value: nonCompliant },
    { name: 'Unknown', value: totalDevices - compliant - nonCompliant },
  ]

  const osData = (deviceReport?.top_os_versions || []).slice(0, 5).map((o: { os: string; count: number }) => ({
    name: (o.os || 'Unknown').replace('Microsoft ', '').substring(0, 20),
    count: o.count,
  }))

  return (
    <div>
      <div className="page-header">
        <Title level={4} style={{ margin: 0 }}>Dashboard</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Last updated: {new Date().toLocaleTimeString()}
        </Text>
      </div>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Devices"
              value={totalDevices}
              prefix={<LaptopOutlined style={{ color: '#1677ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Online Now"
              value={wsStats?.agents_online || onlineDevices}
              prefix={<Badge status="processing" />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Compliant"
              value={compliant}
              suffix={`/ ${totalDevices}`}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Open Alerts"
              value={alertSummary?.open_alerts || 0}
              prefix={<BellOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: alertSummary?.critical ? '#ff4d4f' : '#faad14' }}
            />
            {alertSummary?.critical > 0 && (
              <Text type="danger" style={{ fontSize: 12 }}>
                {alertSummary.critical} critical
              </Text>
            )}
          </Card>
        </Col>
      </Row>

      {/* Row 2 KPIs */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Missing Patches"
              value={patchReport?.patch_status_breakdown?.missing || 0}
              prefix={<CloudSyncOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: '#faad14' }}
            />
            {patchReport?.critical_missing > 0 && (
              <Text type="danger" style={{ fontSize: 12 }}>
                {patchReport.critical_missing} critical
              </Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Non-Compliant"
              value={nonCompliant}
              prefix={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: nonCompliant > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Patches Installed"
              value={patchReport?.patch_status_breakdown?.installed || 0}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Console Sessions"
              value={wsStats?.console_connections || 0}
              prefix={<WifiOutlined style={{ color: '#1677ff' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="Compliance Overview" size="small">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={complianceData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {complianceData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="OS Distribution" size="small">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={osData} margin={{ top: 5, right: 20, bottom: 40, left: 0 }}>
                <XAxis dataKey="name" angle={-20} textAnchor="end" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#1677ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Tables */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Recent Devices" size="small">
            <Table
              dataSource={deviceList?.items || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                {
                  title: 'Hostname',
                  dataIndex: 'hostname',
                  render: (text, record) => (
                    <Space>
                      <Badge status={record.is_online ? 'success' : 'default'} />
                      <span>{text}</span>
                    </Space>
                  ),
                },
                {
                  title: 'OS',
                  dataIndex: 'os_version',
                  render: (v) => <Text ellipsis style={{ maxWidth: 120 }}>{v || '—'}</Text>,
                },
                {
                  title: 'Compliance',
                  dataIndex: 'compliance_status',
                  render: (v) => (
                    <Tag color={v === 'compliant' ? 'success' : v === 'non_compliant' ? 'error' : 'default'}>
                      {v}
                    </Tag>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Open Alerts" size="small">
            <Table
              dataSource={recentAlerts || []}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                {
                  title: 'Severity',
                  dataIndex: 'severity',
                  width: 80,
                  render: (v: string) => (
                    <Tag color={v === 'critical' ? 'red' : v === 'high' ? 'orange' : v === 'medium' ? 'gold' : 'blue'}>
                      {v}
                    </Tag>
                  ),
                },
                {
                  title: 'Title',
                  dataIndex: 'title',
                  render: (v) => <Text ellipsis style={{ maxWidth: 200 }}>{v}</Text>,
                },
                {
                  title: 'Time',
                  dataIndex: 'created_at',
                  render: (v) => new Date(v).toLocaleTimeString(),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
