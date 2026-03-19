import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
})

export default client

// ── Types ────────────────────────────────────────────────────────────────────

export interface Repo {
  id: number
  name: string
  vcs_type: 'git' | 'svn'
  url: string
  default_branch: string
  last_synced_at: string | null
}

export interface Task {
  id: number
  repo_id: number
  task_id: string
  title: string
  branch: string | null
  status: 'in_progress' | 'merged' | 'done' | 'archived'
  author: string | null
  updated_at: string | null
}

export interface FileNode {
  name: string
  type: 'file' | 'dir'
  path: string
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const api = {
  repos: {
    list: () => client.get<Repo[]>('/repos/').then(r => r.data),
    create: (body: Omit<Repo, 'id' | 'last_synced_at'>) =>
      client.post<Repo>('/repos/', body).then(r => r.data),
    sync: (id: number) => client.post(`/repos/${id}/sync`).then(r => r.data),
  },

  tasks: {
    list: (repoId?: number, status?: string) =>
      client.get<Task[]>('/tasks/', { params: { repo_id: repoId, status } }).then(r => r.data),
    get: (id: number) => client.get<Task>(`/tasks/${id}`).then(r => r.data),
    getProgress: (id: number) =>
      client.get<{ task_id: string; content: string }>(`/tasks/${id}/progress`).then(r => r.data),
    writeProgress: (id: number, content: string, author_name: string, author_email: string) =>
      client.post(`/tasks/${id}/progress`, { content, author_name, author_email }).then(r => r.data),
    getTracelog: (id: number) =>
      client.get<{ task_id: string; content: string }>(`/tasks/${id}/tracelog`).then(r => r.data),
    writeTracelog: (id: number, content: string, author_name: string, author_email: string) =>
      client.post(`/tasks/${id}/tracelog`, { content, author_name, author_email }).then(r => r.data),
  },

  files: {
    tree: (repoId: number, path = '', branch?: string) =>
      client.get<FileNode[]>('/files/tree', { params: { repo_id: repoId, path, branch } }).then(r => r.data),
    createSession: (body: { repo_id: number; branch: string; author_name: string; author_email: string }) =>
      client.post<{ session_id: string; worktree_path: string }>('/files/sessions', body).then(r => r.data),
    checkConflicts: (sessionId: string) =>
      client.get<{ conflicts: string[]; safe_to_commit: boolean }>(`/files/sessions/${sessionId}/conflicts`).then(r => r.data),
    commit: (sessionId: string, message: string) =>
      client.post(`/files/sessions/${sessionId}/commit`, { message }).then(r => r.data),
    abort: (sessionId: string) =>
      client.delete(`/files/sessions/${sessionId}`).then(r => r.data),
  },
}
