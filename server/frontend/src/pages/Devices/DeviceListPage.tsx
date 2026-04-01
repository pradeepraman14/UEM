import { useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Button, Input, Select, Space, Tag, Badge, Tooltip, Typography, Row, Col, Card
} from 'antd'
import {
  SearchOutlined, ReloadOutlined, PlusOutlined, FilterOutlined
} from '@ant-design/icons'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import { devicesApi } from '@/api/devices'
import type { Device } from '@/types'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title } = Typography

export default function DeviceListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [complianceFilter, setComplianceFilter] = useState<string | undefined>()
  const [onlineFilter, setOnlineFilter] = useState<boolean | undefined>()
  const [page, setPage] = useState(1)

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
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/devices?enroll=1')}>
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
    </div>
  )
}
