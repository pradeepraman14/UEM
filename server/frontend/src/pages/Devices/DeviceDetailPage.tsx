import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Card, Tabs, Descriptions, Tag, Badge, Button, Space, Typography, Spin, Table, Alert, Row, Col, Statistic
} from 'antd'
import {
  ArrowLeftOutlined, ReloadOutlined, DeleteOutlined, PoweroffOutlined,
  DesktopOutlined, LockOutlined, SafetyOutlined
} from '@ant-design/icons'
import { devicesApi } from '@/api/devices'
import dayjs from 'dayjs'

const { Title, Text } = Typography

export default function DeviceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: device, isLoading } = useQuery({
    queryKey: ['device', id],
    queryFn: () => devicesApi.get(id!),
    enabled: !!id,
    refetchInterval: 30_000,
  })

  const { data: hardware } = useQuery({
    queryKey: ['device', id, 'hardware'],
    queryFn: () => devicesApi.getHardware(id!),
    enabled: !!id,
  })

  const { data: software } = useQuery({
    queryKey: ['device', id, 'software'],
    queryFn: () => devicesApi.getSoftware(id!),
    enabled: !!id,
  })

  const { data: compliance } = useQuery({
    queryKey: ['device', id, 'compliance'],
    queryFn: () => devicesApi.getCompliance(id!),
    enabled: !!id,
  })

  const { data: bitlocker } = useQuery({
    queryKey: ['device', id, 'bitlocker'],
    queryFn: () => devicesApi.getBitLocker(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  }

  if (!device) {
    return <Alert message="Device not found" type="error" />
  }

  return (
    <div>
      <div className="page-header">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/devices')} />
          <Badge status={device.is_online ? 'success' : 'default'} />
          <Title level={4} style={{ margin: 0 }}>{device.hostname}</Title>
          <Tag color={device.status === 'active' ? 'success' : 'default'}>{device.status}</Tag>
        </Space>
        <Space>
          <Button icon={<DesktopOutlined />} onClick={() => navigate('/remote-tools')}>
            Remote Tools
          </Button>
          <Button icon={<ReloadOutlined />} danger>Reboot</Button>
        </Space>
      </div>

      {/* Quick Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Compliance Score"
              value={device.compliance_score ?? '—'}
              suffix="%"
              valueStyle={{ color: (device.compliance_score || 0) >= 80 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Last Seen"
              value={device.last_seen ? dayjs(device.last_seen).fromNow() : 'Never'}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Agent Version" value={device.agent_version || '—'} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="IP Address" value={device.ip_address || '—'} />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs
          defaultActiveKey="overview"
          items={[
            {
              key: 'overview',
              label: 'Overview',
              children: (
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="Device Name">{device.device_name}</Descriptions.Item>
                  <Descriptions.Item label="Hostname">{device.hostname}</Descriptions.Item>
                  <Descriptions.Item label="FQDN">{device.fqdn || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Serial Number">{device.serial_number || '—'}</Descriptions.Item>
                  <Descriptions.Item label="OS Version">{device.os_version || '—'}</Descriptions.Item>
                  <Descriptions.Item label="OS Build">{device.os_build || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Architecture">{device.os_edition || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Assigned User">{device.assigned_user || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Department">{device.department || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Location">{device.location || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Enrolled At">
                    {device.enrolled_at ? dayjs(device.enrolled_at).format('YYYY-MM-DD HH:mm') : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Compliance">
                    <Tag color={device.compliance_status === 'compliant' ? 'success' : 'error'}>
                      {device.compliance_status}
                    </Tag>
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: 'hardware',
              label: 'Hardware',
              children: hardware ? (
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="CPU">{hardware.cpu?.name || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Cores/Threads">
                    {hardware.cpu?.cores || '—'} cores / {hardware.cpu?.threads || '—'} threads
                  </Descriptions.Item>
                  <Descriptions.Item label="RAM">
                    {hardware.memory?.total_mb ? `${(hardware.memory.total_mb / 1024).toFixed(1)} GB` : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Manufacturer">
                    {hardware.system?.manufacturer || '—'} {hardware.system?.model}
                  </Descriptions.Item>
                  <Descriptions.Item label="BIOS">
                    {hardware.bios?.vendor} {hardware.bios?.version}
                  </Descriptions.Item>
                  <Descriptions.Item label="TPM">
                    {hardware.security?.tpm_enabled ? `TPM ${hardware.security?.tpm_version}` : 'Not present'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Secure Boot">
                    {hardware.security?.secure_boot ? '✅ Enabled' : '❌ Disabled'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Chassis">{hardware.system?.chassis_type || '—'}</Descriptions.Item>
                  {hardware.storage && (
                    <Descriptions.Item label="Storage" span={2}>
                      {hardware.storage.map((d: { drive: string; type: string; size_gb: number; free_gb: number }, i: number) => (
                        <div key={i}>{d.drive} — {d.type} {d.size_gb}GB ({d.free_gb}GB free)</div>
                      ))}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              ) : <Text type="secondary">Hardware inventory not yet collected</Text>,
            },
            {
              key: 'software',
              label: `Software (${software?.total || 0})`,
              children: (
                <Table
                  dataSource={software?.software || []}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 20 }}
                  columns={[
                    { title: 'Name', dataIndex: 'name', ellipsis: true },
                    { title: 'Publisher', dataIndex: 'publisher', width: 200 },
                    { title: 'Version', dataIndex: 'version', width: 120 },
                    {
                      title: 'Install Date', dataIndex: 'install_date', width: 120,
                      render: (v) => v || '—',
                    },
                  ]}
                />
              ),
            },
            {
              key: 'compliance',
              label: 'Compliance',
              children: compliance ? (
                <div>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col>
                      <Statistic title="Score" value={compliance.compliance_score ?? '—'} suffix="%" />
                    </Col>
                    <Col>
                      <Statistic title="Status" value={compliance.compliance_status} />
                    </Col>
                  </Row>
                  <Table
                    dataSource={compliance.checks || []}
                    rowKey="rule_name"
                    size="small"
                    columns={[
                      { title: 'Rule', dataIndex: 'rule_name', ellipsis: true },
                      { title: 'Category', dataIndex: 'category', width: 100 },
                      {
                        title: 'Severity', dataIndex: 'severity', width: 100,
                        render: (v: string) => (
                          <Tag color={v === 'critical' ? 'red' : v === 'high' ? 'orange' : 'default'}>{v}</Tag>
                        ),
                      },
                      {
                        title: 'Status', dataIndex: 'status', width: 100,
                        render: (v: string) => (
                          <Tag color={v === 'compliant' ? 'success' : 'error'}>{v}</Tag>
                        ),
                      },
                      { title: 'Actual Value', dataIndex: 'actual_value', width: 150, render: (v) => v || '—' },
                    ]}
                  />
                </div>
              ) : <Text type="secondary">No compliance data yet</Text>,
            },
            {
              key: 'bitlocker',
              label: 'BitLocker',
              icon: <LockOutlined />,
              children: bitlocker ? (
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="Status">
                    <Tag color={bitlocker.is_enabled ? 'success' : 'error'}>
                      {bitlocker.is_enabled ? 'Enabled' : 'Disabled'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="OS Volume">
                    {bitlocker.os_volume_protected ? '✅ Protected' : '❌ Not Protected'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Encryption Method">
                    {bitlocker.encryption_method || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Encryption %">
                    {bitlocker.encryption_percentage != null ? `${bitlocker.encryption_percentage}%` : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Recovery Key Escrowed">
                    {bitlocker.recovery_key_escrowed ? '✅ Yes' : '❌ No'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Collected At">
                    {bitlocker.collected_at ? dayjs(bitlocker.collected_at).format('YYYY-MM-DD HH:mm') : '—'}
                  </Descriptions.Item>
                </Descriptions>
              ) : <Text type="secondary">BitLocker status not collected</Text>,
            },
          ]}
        />
      </Card>
    </div>
  )
}
