/**
 * File submission workflow:
 * 1. Create a server-side worktree session
 * 2. User browses the repo tree and uploads files
 * 3. Conflict check before commit
 * 4. Commit + push, or abort
 */
import { useState } from 'react'
import { Drawer, Button, Tree, Upload, Input, Steps, Alert, Space, message, Spin } from 'antd'
import { UploadOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { useQuery, useMutation } from '@tanstack/react-query'
import type { UploadFile } from 'antd'
import { api, type Task } from '../api/client'
import { useAppStore } from '../store'
import axios from 'axios'

interface Props {
  open: boolean
  task: Task
  onClose: () => void
}

type Step = 'browse' | 'upload' | 'check' | 'done'

export default function FileSubmitDrawer({ open, task, onClose }: Props) {
  const { authorName, authorEmail, activeRepoId } = useAppStore()
  const [step, setStep] = useState<Step>('browse')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [targetPath, setTargetPath] = useState('')
  const [commitMsg, setCommitMsg] = useState(`[${task.task_id}] update files`)
  const [conflicts, setConflicts] = useState<string[]>([])
  const [fileList, setFileList] = useState<UploadFile[]>([])

  const { data: tree = [], isLoading: treeLoading } = useQuery({
    queryKey: ['tree', activeRepoId, targetPath],
    queryFn: () => api.files.tree(activeRepoId!, targetPath, task.branch ?? undefined),
    enabled: !!activeRepoId && open,
  })

  const treeData = tree.map(f => ({
    title: f.name,
    key: f.path,
    isLeaf: f.type === 'file',
  }))

  const createSession = useMutation({
    mutationFn: () =>
      api.files.createSession({
        repo_id: activeRepoId!,
        branch: task.branch ?? 'main',
        author_name: authorName,
        author_email: authorEmail,
      }),
    onSuccess: (data) => {
      setSessionId(data.session_id)
      setStep('upload')
    },
  })

  const checkAndCommit = useMutation({
    mutationFn: async () => {
      const check = await api.files.checkConflicts(sessionId!)
      if (!check.safe_to_commit) {
        setConflicts(check.conflicts)
        setStep('check')
        throw new Error('conflicts')
      }
      return api.files.commit(sessionId!, commitMsg)
    },
    onSuccess: () => {
      message.success('Files committed to VCS successfully')
      setStep('done')
    },
    onError: (e: Error) => {
      if (e.message !== 'conflicts') message.error('Commit failed: ' + e.message)
    },
  })

  const abort = async () => {
    if (sessionId) await api.files.abort(sessionId)
    setSessionId(null)
    setStep('browse')
    setConflicts([])
    onClose()
  }

  const handleUpload = async (file: File) => {
    if (!sessionId || !targetPath) {
      message.warning('Select a target directory first')
      return false
    }
    const formData = new FormData()
    formData.append('file', file)
    await axios.post(
      `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'}/files/sessions/${sessionId}/upload?target_path=${targetPath}/${file.name}`,
      formData,
    )
    message.success(`${file.name} uploaded to worktree`)
    return false // prevent antd auto-upload
  }

  const steps = [
    { title: 'Browse', description: 'Pick directory' },
    { title: 'Upload', description: 'Add files' },
    { title: 'Check', description: 'Conflict scan' },
    { title: 'Done', description: 'Committed' },
  ]
  const stepIndex = { browse: 0, upload: 1, check: 2, done: 3 }[step]

  return (
    <Drawer
      title={`Submit Files — ${task.task_id}`}
      open={open}
      onClose={abort}
      width={560}
      footer={
        <Space>
          {step === 'browse' && (
            <Button type="primary" disabled={!targetPath} onClick={() => createSession.mutate()} loading={createSession.isPending}>
              Open session
            </Button>
          )}
          {step === 'upload' && (
            <Button type="primary" onClick={() => checkAndCommit.mutate()} loading={checkAndCommit.isPending}>
              Check &amp; Commit
            </Button>
          )}
          {step === 'check' && (
            <Button danger onClick={abort}>Abort</Button>
          )}
          {step === 'done' && (
            <Button onClick={() => { setStep('browse'); setSessionId(null); onClose() }}>Close</Button>
          )}
          <Button onClick={abort}>Cancel</Button>
        </Space>
      }
    >
      <Steps size="small" current={stepIndex} items={steps} style={{ marginBottom: 24 }} />

      {step === 'browse' && (
        <>
          <p style={{ color: '#666' }}>Navigate to the directory where you want to submit files.</p>
          {treeLoading ? <Spin /> : (
            <Tree
              treeData={treeData}
              onSelect={(keys) => {
                const key = keys[0] as string
                const node = tree.find(f => f.path === key)
                if (node?.type === 'dir') setTargetPath(key)
              }}
              style={{ border: '1px solid #f0f0f0', borderRadius: 6, padding: 8 }}
            />
          )}
          {targetPath && <Alert style={{ marginTop: 12 }} type="info" message={`Target: ${targetPath}`} />}
        </>
      )}

      {step === 'upload' && (
        <>
          <Alert type="info" message={`Uploading to: ${targetPath}`} style={{ marginBottom: 16 }} />
          <Upload
            beforeUpload={handleUpload}
            fileList={fileList}
            onChange={({ fileList }) => setFileList(fileList)}
            multiple
          >
            <Button icon={<UploadOutlined />}>Select files</Button>
          </Upload>
          <Input.TextArea
            style={{ marginTop: 16 }}
            rows={2}
            value={commitMsg}
            onChange={e => setCommitMsg(e.target.value)}
            placeholder="Commit message"
          />
        </>
      )}

      {step === 'check' && (
        <Alert
          type="warning"
          icon={<WarningOutlined />}
          message="Conflicts detected"
          description={
            <>
              <p>The following files have been modified on the remote since you started:</p>
              <ul>{conflicts.map(f => <li key={f}><code>{f}</code></li>)}</ul>
              <p>Please download the latest version and re-upload.</p>
            </>
          }
        />
      )}

      {step === 'done' && (
        <Alert
          type="success"
          icon={<CheckCircleOutlined />}
          message="Files committed successfully"
          description="Your files have been pushed to the VCS repository."
        />
      )}
    </Drawer>
  )
}
