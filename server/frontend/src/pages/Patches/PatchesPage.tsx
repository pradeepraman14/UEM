import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Table, Tag, Button, Space, Typography, Row, Col, Statistic, Select, Modal, Form, DatePicker } from 'antd'
import { CheckOutlined, CloudSyncOutlined } from '@ant-design/icons'
import { apiClient } from '@/api/client'
import type { Patch } from '@/types'
import toast from 'react-hot-toast'
import dayjs from 'dayjs'
import { useState } from 'react'

const { Title } = Typography

export default function PatchesPage() {
  const qc = useQueryClient()
  const [approveVisible, setApproveVisible] = useState(false)
  const [selectedPatches, setSelectedPatches] = useState<string[]>([])
  const [form] = Form.useForm()

  const { data: dashboard } = useQuery({
    queryKey: ['patches', 'dashboard'],
    queryFn: () => apiClient.get('/patches/dashboard').then((r) => r.data),
    refetchInterval: 60_000,
  })

  const { data: patches, isLoading } = useQuery({
    queryKey: ['patches'],
    queryFn: () => apiClient.get('/patches', { params: { limit: 200 } }).then((r) => r.data),
  })

  const approveMutation = useMutation({
    mutationFn: (data: { patch_ids: string[]; scheduled_at?: string }) =>
      apiClient.post('/patches/approve', data),
    onSuccess: () => {
      toast.success('Patches approved')
      qc.invalidateQueries({ queryKey: ['patches'] })
      setApproveVisible(false)
    },
  })

  const severityColor = (s?: string) => {
    const map: Record<string, string> = { critical: 'red', important: 'orange', moderate: 'gold', low: 'blue' }
    return map[s || ''] || 'default'
  }

  return (
    <div>
      <div className="page-header">
        <Title level={4} style={{ margin: 0 }}>Patch Management</Title>
        <Space>
          <Button
            type="primary"
            icon={<CheckOutlined />}
            disabled={selectedPatches.length === 0}
            onClick={() => setApproveVisible(true)}
          >
            Approve Selected ({selectedPatches.length})
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Total Patches" value={dashboard?.total_patches_in_catalog || 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Critical"
              value={dashboard?.critical_patches || 0}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Missing on Devices"
              value={dashboard?.missing_on_devices || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Installed"
              value={dashboard?.installed || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Table
          dataSource={patches || []}
          rowKey="id"
          loading={isLoading}
          size="small"
          rowSelection={{
            selectedRowKeys: selectedPatches,
            onChange: (keys) => setSelectedPatches(keys as string[]),
          }}
          columns={[
            { title: 'KB', dataIndex: 'kb_article_id', width: 100, render: (v) => v || '—' },
            { title: 'Title', dataIndex: 'title', flex: 1 },
            {
              title: 'Severity', dataIndex: 'severity', width: 100,
              render: (v) => <Tag color={severityColor(v)}>{v || '—'}</Tag>,
            },
            { title: 'Type', dataIndex: 'patch_type', width: 100 },
            { title: 'Released', dataIndex: 'release_date', width: 110, render: (v) => v || '—' },
            {
              title: 'Reboot', dataIndex: 'reboot_required', width: 80,
              render: (v) => v ? <Tag color="warning">Yes</Tag> : 'No',
            },
          ]}
          pagination={{ pageSize: 50 }}
        />
      </Card>

      <Modal
        title="Approve Patches"
        open={approveVisible}
        onCancel={() => setApproveVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={approveMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={(v) => approveMutation.mutate({
          patch_ids: selectedPatches,
          scheduled_at: v.scheduled_at?.toISOString(),
        })}>
          <Form.Item label="Schedule Deployment (optional)" name="scheduled_at">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
        <p>Approving {selectedPatches.length} patches for deployment.</p>
      </Modal>
    </div>
  )
}
