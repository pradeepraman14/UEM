import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Button, Input, Select, Space, Tag, Badge, Typography, Row, Col, Card,
  Modal, Descriptions, Alert, Spin, message,
} from 'antd'
import {
  SearchOutlined, ReloadOutlined, PlusOutlined, CopyOutlined, KeyOutlined,
} from '@ant-design/icons'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import { devicesApi } from '@/api/devices'
import { apiClient } from '@/api/client'
import type { Device } from '@/types'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text } = Typography

export default function DeviceListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [complianceFilter, setComplianceFilter] = useState<string | undefined>()
  const [onlineFilter, setOnlineFilter] = useState<boolean | undefined>()
  const [page] = useState(1)
  const [enrollOpen, setEnrollOpen] = useState(false)
  const [enrollToken, setEnrollToken] = useState<string | null>(null)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['devices', page, search, statusFilter, complianceFilter, onlineFilter],
    queryFn: () =>
      devicesApi.list({
        page,
        page_size: 100,
        search: search || undefined,
        status: statusFilter,
        compliance_status: complianceFilter,
        is_online: onlineFilter,
      }),
    refetchInterval: 30_000,
  })

  const tokenMutation = useMutation({
    mutationFn: () =>
      apiClient.post('/devices/generate-token').then((r) => r.data as { enrollment_token: string }),
    onSuccess: (data) => {
      setEnrollToken(data.enrollment_token)
    },
  })

  const openEnrollModal = () => {
    setEnrollToken(null)
    setEnrollOpen(true)
    tokenMutation.mutate()
  }

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    message.success(`${label} copied to clipboard`)
  }

  const serverUrl = window.location.origin

  const columnDefs = useMemo<ColDef<Device>[]>(() => [
    {
      field: 'is_online',
      headerName: '',
      width: 44,
      cellRenderer: ({ value }: { value: boolean }) => (
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          <Badge status={value ? 'success' : 'default'} />
        </div>
      ),
      sortable: false,
      filter: false,
    },
    {
      field: 'hostname',
      headerName: 'Hostname',
      flex: 1,
      minWidth: 150,
      cellRenderer: ({ value, data: row }: { value: string; data: Device }) => (
        <button
          style={{ background: 'none', border: 'none', color: '#1677ff', cursor: 'pointer', padding: 0, fontSize: 13 }}
          onClick={() => navigate(`/devices/${row.id}`)}
        >
          {value}
        </button>
      ),
    },
    {
      field: 'ip_address',
      headerName: 'IP Address',
      width: 130,
      valueFormatter: ({ value }) => value || '—',
    },
    {
      field: 'os_version',
      headerName: 'OS',
      flex: 1,
      minWidth: 150,
      valueFormatter: ({ value }) => value?.replace('Microsoft ', '') || '—',
    },
    {
      field: 'agent_version',
      headerName: 'Agent',
      width: 90,
      valueFormatter: ({ value }) => value || '—',
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 100,
      cellRenderer: ({ value }: { value: string }) => {
        const colorMap: Record<string, string> = {
          active: 'success', pending: 'processing', inactive: 'default',
          quarantined: 'warning', retired: 'error',
        }
        return <Tag color={colorMap[value] || 'default'}>{value}</Tag>
      },
    },
    {
      field: 'compliance_status',
      headerName: 'Compliance',
      width: 120,
      cellRenderer: ({ value, data: row }: { value: string; data: Device }) => (
        <Space size={4}>
          <Tag color={value === 'compliant' ? 'success' : value === 'non_compliant' ? 'error' : 'default'}>
            {value}
          </Tag>
          {row.compliance_score != null && (
            <span style={{ fontSize: 11, color: '#888' }}>{row.compliance_score}%</span>
          )}
        </Space>
      ),
    },
    {
      field: 'assigned_user',
      headerName: 'User',
      flex: 1,
      minWidth: 120,
      valueFormatter: ({ value }) => value || '—',
    },
    {
      field: 'last_seen',
      headerName: 'Last Seen',
      width: 120,
      valueFormatter: ({ value }) => value ? dayjs(value).fromNow() : '—',
    },
  ], [navigate])

  return (
    <div>
      <div className="page-header">
        <Title level={4} style={{ margin: 0 }}>Devices ({data?.total || 0})</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openEnrollModal}>
            Enroll Device
          </Button>
        </Space>
      </div>

      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col xs={24} sm={8}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="Search hostname, IP, user..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={4}>
            <Select
              placeholder="Status"
              allowClear
              style={{ width: '100%' }}
              onChange={setStatusFilter}
              options={[
                { value: 'active', label: 'Active' },
                { value: 'pending', label: 'Pending' },
                { value: 'inactive', label: 'Inactive' },
                { value: 'quarantined', label: 'Quarantined' },
                { value: 'retired', label: 'Retired' },
              ]}
            />
          </Col>
          <Col xs={12} sm={4}>
            <Select
              placeholder="Compliance"
              allowClear
              style={{ width: '100%' }}
              onChange={setComplianceFilter}
              options={[
                { value: 'compliant', label: 'Compliant' },
                { value: 'non_compliant', label: 'Non-Compliant' },
                { value: 'unknown', label: 'Unknown' },
              ]}
            />
          </Col>
          <Col xs={12} sm={4}>
            <Select
              placeholder="Online Status"
              allowClear
              style={{ width: '100%' }}
              onChange={(v) => setOnlineFilter(v === undefined ? undefined : v === 'online')}
              options={[
                { value: 'online', label: 'Online' },
                { value: 'offline', label: 'Offline' },
              ]}
            />
          </Col>
        </Row>
      </Card>

      <div className="ag-theme-alpine" style={{ height: 600, width: '100%' }}>
        <AgGridReact
          rowData={data?.items || []}
          columnDefs={columnDefs}
          loading={isLoading}
          defaultColDef={{ sortable: true, filter: true, resizable: true }}
          rowSelection="multiple"
          animateRows
          suppressRowClickSelection
          pagination
          paginationPageSize={50}
          rowHeight={44}
          headerHeight={42}
        />
      </div>

      {/* Enrollment Token Modal */}
      <Modal
        title={<Space><KeyOutlined /> Enroll a Windows Device</Space>}
        open={enrollOpen}
        onCancel={() => setEnrollOpen(false)}
        footer={<Button onClick={() => setEnrollOpen(false)}>Close</Button>}
        width={600}
      >
        {tokenMutation.isPending && (
          <div style={{ textAlign: 'center', padding: 32 }}>
            <Spin size="large" />
            <div style={{ marginTop: 12 }}>Generating enrollment token...</div>
          </div>
        )}

        {enrollToken && (
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <Alert
              type="info"
              message="Token is valid for 24 hours. Use it on the Windows machine to enroll the agent."
              showIcon
            />

            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Server URL">
                <Space>
                  <Text code>{serverUrl}</Text>
                  <Button size="small" icon={<CopyOutlined />} onClick={() => copy(serverUrl, 'Server URL')} />
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Enrollment Token">
                <Space>
                  <Text code style={{ wordBreak: 'break-all' }}>{enrollToken}</Text>
                  <Button size="small" icon={<CopyOutlined />} onClick={() => copy(enrollToken, 'Token')} />
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="Run on Windows machine (Administrator PowerShell)">
              <Text code style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                {`# 1. Download and install the agent\n.\\UEMAgentSetup.exe /S /SERVER=${serverUrl} /TOKEN=${enrollToken}\n\n# Or enroll manually if agent is already installed:\nUEMAgent.exe enroll --server ${serverUrl} --token ${enrollToken}`}
              </Text>
              <Button
                size="small"
                icon={<CopyOutlined />}
                style={{ marginTop: 8 }}
                onClick={() => copy(
                  `UEMAgent.exe enroll --server ${serverUrl} --token ${enrollToken}`,
                  'Command'
                )}
              >
                Copy command
              </Button>
            </Card>

            <Alert
              type="warning"
              message="Make sure the Windows machine has the CA certificate installed. Download it from your server at /opt/UEM/pki/ca/ca.crt"
              showIcon
            />
          </Space>
        )}
      </Modal>
    </div>
  )
}
