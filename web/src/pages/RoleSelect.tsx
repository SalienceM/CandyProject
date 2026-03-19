import { Card, Col, Form, Input, Row, Typography } from 'antd'
import { UserOutlined, BarChartOutlined } from '@ant-design/icons'
import { useAppStore, type Role } from '../store'

const { Title, Paragraph } = Typography

export default function RoleSelect() {
  const { setRole, setAuthor } = useAppStore()
  const [form] = Form.useForm()

  const handlePick = (role: Role) => {
    form.validateFields().then(({ name, email }) => {
      setAuthor(name, email)
      setRole(role)
    })
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
      <div style={{ width: 480 }}>
        <Title level={2} style={{ textAlign: 'center', marginBottom: 8 }}>🍬 CandyProject</Title>
        <Paragraph style={{ textAlign: 'center', color: '#888', marginBottom: 32 }}>
          VCS-native project management
        </Paragraph>

        <Form form={form} layout="vertical" style={{ marginBottom: 24 }}>
          <Form.Item name="name" label="Your name" rules={[{ required: true }]}>
            <Input placeholder="Zhang San" />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
            <Input placeholder="zhangsan@example.com" />
          </Form.Item>
        </Form>

        <Row gutter={16}>
          <Col span={12}>
            <Card
              hoverable
              onClick={() => handlePick('user')}
              style={{ textAlign: 'center', cursor: 'pointer' }}
            >
              <UserOutlined style={{ fontSize: 36, color: '#1890ff', marginBottom: 8 }} />
              <div style={{ fontSize: 18, fontWeight: 600 }}>User</div>
              <div style={{ color: '#888', fontSize: 13 }}>View & update my tasks</div>
            </Card>
          </Col>
          <Col span={12}>
            <Card
              hoverable
              onClick={() => handlePick('manager')}
              style={{ textAlign: 'center', cursor: 'pointer' }}
            >
              <BarChartOutlined style={{ fontSize: 36, color: '#52c41a', marginBottom: 8 }} />
              <div style={{ fontSize: 18, fontWeight: 600 }}>Manager</div>
              <div style={{ color: '#888', fontSize: 13 }}>Dashboard & reports</div>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}
