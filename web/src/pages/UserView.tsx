import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Layout, List, Tag, Button, Modal, Input, Tabs, Typography, message, Spin } from 'antd'
import { FolderOpenOutlined } from '@ant-design/icons'
import { api, type Task } from '../api/client'
import { useAppStore } from '../store'
import FileSubmitDrawer from '../components/FileSubmitDrawer'

const { Content } = Layout
const { TextArea } = Input
const { Text, Paragraph } = Typography

const STATUS_COLOR: Record<string, string> = {
  in_progress: 'blue',
  merged: 'green',
  done: 'green',
  archived: 'default',
}

export default function UserView() {
  const { authorName, authorEmail, activeRepoId } = useAppStore()
  const qc = useQueryClient()

  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [progressText, setProgressText] = useState('')
  const [traceText, setTraceText] = useState('')
  const [fileDrawerOpen, setFileDrawerOpen] = useState(false)

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['tasks', activeRepoId],
    queryFn: () => api.tasks.list(activeRepoId ?? undefined),
  })

  const { data: progress } = useQuery({
    queryKey: ['progress', selectedTask?.id],
    queryFn: () => api.tasks.getProgress(selectedTask!.id),
    enabled: !!selectedTask,
  })

  const { data: tracelog } = useQuery({
    queryKey: ['tracelog', selectedTask?.id],
    queryFn: () => api.tasks.getTracelog(selectedTask!.id),
    enabled: !!selectedTask,
  })

  const writeProgress = useMutation({
    mutationFn: (content: string) =>
      api.tasks.writeProgress(selectedTask!.id, content, authorName, authorEmail),
    onSuccess: () => {
      message.success('Progress saved to VCS')
      setProgressText('')
      qc.invalidateQueries({ queryKey: ['progress', selectedTask?.id] })
    },
  })

  const writeTrace = useMutation({
    mutationFn: (content: string) =>
      api.tasks.writeTracelog(selectedTask!.id, content, authorName, authorEmail),
    onSuccess: () => {
      message.success('Tracelog saved to VCS')
      setTraceText('')
      qc.invalidateQueries({ queryKey: ['tracelog', selectedTask?.id] })
    },
  })

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: 24, maxWidth: 900, margin: '0 auto', width: '100%' }}>
        <Typography.Title level={3}>My Tasks</Typography.Title>

        {isLoading ? (
          <Spin />
        ) : (
          <List
            dataSource={tasks}
            renderItem={(task) => (
              <List.Item
                actions={[
                  <Button size="small" onClick={() => setSelectedTask(task)}>Update</Button>,
                  <Button
                    size="small"
                    icon={<FolderOpenOutlined />}
                    onClick={() => { setSelectedTask(task); setFileDrawerOpen(true) }}
                  >
                    Submit Files
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={<><Text strong>{task.task_id}</Text> — {task.title}</>}
                  description={
                    <>
                      <Tag color={STATUS_COLOR[task.status]}>{task.status}</Tag>
                      {task.branch && <Text type="secondary" style={{ marginLeft: 8 }}>{task.branch}</Text>}
                    </>
                  }
                />
              </List.Item>
            )}
          />
        )}

        {/* Progress / Tracelog modal */}
        <Modal
          open={!!selectedTask && !fileDrawerOpen}
          title={`${selectedTask?.task_id} — ${selectedTask?.title}`}
          onCancel={() => setSelectedTask(null)}
          footer={null}
          width={680}
        >
          {selectedTask && (
            <Tabs
              items={[
                {
                  key: 'progress',
                  label: 'Progress',
                  children: (
                    <>
                      <Paragraph style={{ background: '#fafafa', padding: 12, borderRadius: 6, maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 13 }}>
                        {progress?.content || <Text type="secondary">No entries yet.</Text>}
                      </Paragraph>
                      <TextArea
                        rows={4}
                        placeholder="What did you do? What's blocked?"
                        value={progressText}
                        onChange={e => setProgressText(e.target.value)}
                        style={{ marginTop: 8 }}
                      />
                      <Button
                        type="primary"
                        style={{ marginTop: 8 }}
                        loading={writeProgress.isPending}
                        onClick={() => progressText.trim() && writeProgress.mutate(progressText)}
                      >
                        Save to VCS
                      </Button>
                    </>
                  ),
                },
                {
                  key: 'tracelog',
                  label: 'Tracelog',
                  children: (
                    <>
                      <Paragraph style={{ background: '#fafafa', padding: 12, borderRadius: 6, maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap', fontSize: 13 }}>
                        {tracelog?.content || <Text type="secondary">No entries yet.</Text>}
                      </Paragraph>
                      <TextArea
                        rows={4}
                        placeholder="Errors, decisions, references..."
                        value={traceText}
                        onChange={e => setTraceText(e.target.value)}
                        style={{ marginTop: 8 }}
                      />
                      <Button
                        type="primary"
                        style={{ marginTop: 8 }}
                        loading={writeTrace.isPending}
                        onClick={() => traceText.trim() && writeTrace.mutate(traceText)}
                      >
                        Save to VCS
                      </Button>
                    </>
                  ),
                },
              ]}
            />
          )}
        </Modal>

        {selectedTask && (
          <FileSubmitDrawer
            open={fileDrawerOpen}
            task={selectedTask}
            onClose={() => { setFileDrawerOpen(false); setSelectedTask(null) }}
          />
        )}
      </Content>
    </Layout>
  )
}
