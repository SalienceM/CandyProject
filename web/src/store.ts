import { create } from 'zustand'

export type Role = 'user' | 'manager'

interface AppState {
  role: Role | null
  authorName: string
  authorEmail: string
  activeRepoId: number | null

  setRole: (role: Role) => void
  setAuthor: (name: string, email: string) => void
  setActiveRepo: (id: number) => void
}

export const useAppStore = create<AppState>((set) => ({
  role: null,
  authorName: '',
  authorEmail: '',
  activeRepoId: null,

  setRole: (role) => set({ role }),
  setAuthor: (authorName, authorEmail) => set({ authorName, authorEmail }),
  setActiveRepo: (activeRepoId) => set({ activeRepoId }),
}))
