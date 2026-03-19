import { useQuery } from '@tanstack/react-query'
import { Layout, Row, Col, Card, Statistic, Table, Tag, Select, Button, message } from 'antd'
import { SyncOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { api } from '../api/client'
import { useAppStore } from '../store'

const { Content } = Layout

const STATUS_COLOR: Record<string, string> = {
  in_progress: 'blue',
  merged: 'green',
  done: 'green',
  archived: 'default',
}

export default function ManagerView() {
  const { activeRepoId, setActiveRepo } = useAppStore()

  const { data: repos = [] } = useQuery({
    queryKey: ['repos'],
    queryFn: api.repos.list,
  })

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['tasks', activeRepoId],
    queryFn: () => api.tasks.list(activeRepoId ?? undefined),
  })

  const handleSync = async (repoId: number) => {
    await api.repos.sync(repoId)
    message.success('Sync triggered')
  }

  // ── Compute stats ────────────────────────────────────────────────────────
  const byStatus = tasks.reduce<Record<string, number>>((acc, t) => {
    acc[t.status] = (acc[t.status] ?? 0) + 1
    return acc
  }, {})

  const pieOption = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '65%',
      data: Object.entries(byStatus).map(([name, value]) => ({ name, value })),
    }],
  }

  const byAuthor = tasks.reduce<Record<string, number>>((acc, t) => {
    const a = t.author ?? 'unknown'
    acc[a] = (acc[a] ?? 0) + 1
    return acc
  }, {})

  const barOption = {
    tooltip: {},
    xAxis: { type: 'category', data: Object.keys(byAuthor) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: Object.values(byAuthor) }],
  }

  const columns = [
    { title: 'Task ID', dataIndex: 'task_id', key: 'task_id' },
    { title: 'Title', dataIndex: 'title', key: 'title', ellipsis: true },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => <Tag color={STATUS_COLOR[s]}>{s}</Tag>,
    },
    { title: 'Author', dataIndex: 'author', key: 'author' },
    { title: 'Updated', dataIndex: 'updated_at', key: 'updated_at', render: (d: string) => d?.slice(0, 10) },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: 24 }}>
        <Row gutter={16} style={{ marginBottom: 16 }} align="middle">
          <Col>
            <Select
              placeholder="Select repo"
              style={{ width: 240 }}
              allowClear
              onChange={(val) => val !== undefined && setActiveRepo(val)}
              options={repos.map(r => ({ value: r.id, label: `${r.name} (${r.vcs_type})` }))}
            />
          </Col>
          {activeRepoId && (
            <Col>
              <Button icon={<SyncOutlined />} onClick={() => handleSync(activeRepoId)}>
                Sync
              </Button>
            </Col>
          )}
        </Row>

        {/* Summary cards */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}><Card><Statistic title="Total Tasks" value={tasks.length} /></Card></Col>
          <Col span={6}><Card><Statistic title="In Progress" value={byStatus.in_progress ?? 0} valueStyle={{ color: '#1890ff' }} /></Card></Col>
          <Col span={6}><Card><Statistic title="Merged / Done" value={(byStatus.merged ?? 0) + (byStatus.done ?? 0)} valueStyle={{ color: '#52c41a' }} /></Card></Col>
          <Col span={6}><Card><Statistic title="Archived" value={byStatus.archived ?? 0} /></Card></Col>
        </Row>

        {/* Charts */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={10}>
            <Card title="Task Status Distribution">
              <ReactECharts option={pieOption} style={{ height: 260 }} />
            </Card>
          </Col>
          <Col span={14}>
            <Card title="Tasks by Author">
              <ReactECharts option={barOption} style={{ height: 260 }} />
            </Card>
          </Col>
        </Row>

        {/* Task table */}
        <Card title="All Tasks">
          <Table
            dataSource={tasks}
            columns={columns}
            rowKey="id"
            loading={isLoading}
            size="small"
            pagination={{ pageSize: 20 }}
          />
        </Card>
      </Content>
    </Layout>
  )
}
