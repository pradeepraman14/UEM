import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Card, Select, Space, Button, Input, Typography, Tabs, Table, Tag, Alert, Form, Spin
} from 'antd'
import { SendOutlined, ReloadOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons'
import { apiClient } from '@/api/client'
import { devicesApi } from '@/api/devices'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { Command, WSMessage } from '@/types'
import toast from 'react-hot-toast'

const { Title, Text } = Typography
const { TextArea } = Input

export default function RemoteToolsPage() {
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null)
  const [commandText, setCommandText] = useState('')
  const [termOutput, setTermOutput] = useState<string[]>([])
  const termRef = useRef<HTMLDivElement>(null)

  const { data: deviceList } = useQuery({
    queryKey: ['devices', 'online'],
    queryFn: () => devicesApi.list({ is_online: true, page_size: 500 }),
    refetchInterval: 30_000,
  })

  const { data: commands, refetch: refetchCommands } = useQuery({
    queryKey: ['commands', selectedDevice],
    queryFn: () =>
      apiClient.get('/commands', {
        params: { device_id: selectedDevice, limit: 20 },
      }).then((r) => r.data),
    enabled: !!selectedDevice,
    refetchInterval: 5000,
  })

  const runCommand = useMutation({
    mutationFn: (cmd: string) =>
      apiClient.post('/commands', {
        device_id: selectedDevice,
        command_type: 'powershell',
        payload: { command: cmd, shell: 'powershell' },
        timeout_seconds: 120,
      }).then((r) => r.data),
    onSuccess: (data: Command) => {
      setTermOutput((prev) => [...prev, `> ${commandText}`, `[${data.id.slice(0, 8)}] Sent...`])
      setCommandText('')
      refetchCommands()
    },
    onError: () => toast.error('Failed to send command'),
  })

  const rebootDevice = useMutation({
    mutationFn: () =>
      apiClient.post('/commands', {
        device_id: selectedDevice,
        command_type: 'reboot',
        payload: { delay_seconds: 0, force: false },
      }),
    onSuccess: () => toast.success('Reboot command sent'),
  })

  const lockDevice = useMutation({
    mutationFn: () =>
      apiClient.post('/commands', {
        device_id: selectedDevice,
        command_type: 'lock',
        payload: {},
      }),
    onSuccess: () => toast.success('Lock command sent'),
  })

  // Listen for command results over WebSocket
  useWebSocket((message: WSMessage) => {
    if (
      message.type === 'command_result' &&
      message.device_id === selectedDevice
    ) {
      const { output, exit_code, error } = message.payload as {
        output?: string; exit_code?: number; error?: string
      }
      setTermOutput((prev) => [
        ...prev,
        output || error || '',
        `[Exit: ${exit_code ?? '?'}]`,
        '',
      ])
    }
  })

  // Scroll to bottom on new output
  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight
    }
  }, [termOutput])

  return (
    <div>
      <div className="page-header">
        <Title level={4} style={{ margin: 0 }}>Remote Management Tools</Title>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Text>Target Device:</Text>
          <Select
            showSearch
            placeholder="Select online device..."
            style={{ width: 300 }}
            onChange={setSelectedDevice}
            filterOption={(input, opt) =>
              (opt?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
            options={deviceList?.items?.map((d) => ({
              value: d.id,
              label: `${d.hostname} (${d.ip_address || '?'})`,
            }))}
          />
          {selectedDevice && (
            <Space>
              <Button danger icon={<ReloadOutlined />} onClick={() => rebootDevice.mutate()}>
                Reboot
              </Button>
              <Button icon={<ReloadOutlined />} onClick={() => lockDevice.mutate()}>
                Lock Screen
              </Button>
            </Space>
          )}
        </Space>
      </Card>

      {!selectedDevice && (
        <Alert
          message="Select an online device above to start remote management"
          type="info"
          showIcon
        />
      )}

      {selectedDevice && (
        <Tabs
          items={[
            {
              key: 'shell',
              label: 'Remote Shell',
              children: (
                <div>
                  <div
                    ref={termRef}
                    className="terminal-container"
                    style={{
                      height: 400,
                      overflowY: 'auto',
                      fontFamily: 'Consolas, monospace',
                      fontSize: 13,
                      color: '#d4d4d4',
                      padding: 12,
                    }}
                  >
                    {termOutput.length === 0 && (
                      <span style={{ color: '#888' }}>
                        # PowerShell / CMD commands will appear here
                      </span>
                    )}
                    {termOutput.map((line, i) => (
                      <div key={i}>{line}</div>
                    ))}
                  </div>
                  <Space.Compact style={{ width: '100%', marginTop: 8 }}>
                    <Input
                      value={commandText}
                      onChange={(e) => setCommandText(e.target.value)}
                      onPressEnter={() => commandText.trim() && runCommand.mutate(commandText)}
                      placeholder="Enter PowerShell command..."
                      prefix={<Text style={{ color: '#52c41a' }}>PS&gt;</Text>}
                      disabled={runCommand.isPending}
                    />
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      loading={runCommand.isPending}
                      onClick={() => commandText.trim() && runCommand.mutate(commandText)}
                    >
                      Run
                    </Button>
                  </Space.Compact>
                </div>
              ),
            },
            {
              key: 'history',
              label: 'Command History',
              children: (
                <Table
                  dataSource={Array.isArray(commands) ? commands : []}
                  rowKey="id"
                  size="small"
                  columns={[
                    { title: 'Type', dataIndex: 'command_type', width: 100 },
                    {
                      title: 'Status', dataIndex: 'status', width: 100,
                      render: (v: string) => {
                        const map: Record<string, string> = {
                          completed: 'success', failed: 'error', running: 'processing',
                          sent: 'processing', pending: 'default',
                        }
                        return <Tag color={map[v] || 'default'}>{v}</Tag>
                      },
                    },
                    { title: 'Exit Code', dataIndex: 'exit_code', width: 80, render: (v) => v ?? '—' },
                    {
                      title: 'Sent',
                      dataIndex: 'sent_at',
                      width: 160,
                      render: (v) => v ? new Date(v).toLocaleString() : '—',
                    },
                    {
                      title: 'Output',
                      dataIndex: 'output',
                      render: (v) => (
                        <Text
                          ellipsis={{ tooltip: v }}
                          style={{ maxWidth: 300, fontSize: 12, fontFamily: 'monospace' }}
                        >
                          {v || '—'}
                        </Text>
                      ),
                    },
                  ]}
                  pagination={{ pageSize: 10 }}
                />
              ),
            },
          ]}
        />
      )}
    </div>
  )
}
