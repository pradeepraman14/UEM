import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, Space, Alert } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/auth'

const { Title, Text } = Typography

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true)
    setError(null)
    try {
      const { access_token } = await authApi.login(values.email, values.password)
      const user = await (async () => {
        const { apiClient } = await import('@/api/client')
        apiClient.defaults.headers.common.Authorization = `Bearer ${access_token}`
        const { data } = await apiClient.get('/users/me')
        return data
      })()
      setAuth(access_token, user)
      navigate('/dashboard')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #001529 0%, #003a8c 100%)',
      }}
    >
      <Card
        style={{ width: 400, boxShadow: '0 8px 32px rgba(0,0,0,0.3)', borderRadius: 12 }}
        styles={{ body: { padding: '40px 40px 32px' } }}
      >
        <Space direction="vertical" size={8} style={{ width: '100%', marginBottom: 32 }}>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: 40 }}>🖥️</span>
          </div>
          <Title level={3} style={{ textAlign: 'center', margin: 0 }}>
            UEM Console
          </Title>
          <Text type="secondary" style={{ display: 'block', textAlign: 'center', fontSize: 13 }}>
            Unified Endpoint Management Platform
          </Text>
        </Space>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: 20 }}
            closable
            onClose={() => setError(null)}
          />
        )}

        <Form
          name="login"
          onFinish={onFinish}
          layout="vertical"
          size="large"
          autoComplete="on"
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: 'Please enter your email' },
              { type: 'email', message: 'Please enter a valid email' },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="Email address"
              type="email"
              autoComplete="email"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Please enter your password' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="Password"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              block
              loading={loading}
              style={{ height: 44, fontSize: 15 }}
            >
              Sign In
            </Button>
          </Form.Item>
        </Form>

        <Text
          type="secondary"
          style={{ display: 'block', textAlign: 'center', marginTop: 24, fontSize: 12 }}
        >
          UEM Platform v1.0
        </Text>
      </Card>
    </div>
  )
}
