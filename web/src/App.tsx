import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider, theme } from 'antd'
import { useAppStore } from './store'
import RoleSelect from './pages/RoleSelect'
import UserView from './pages/UserView'
import ManagerView from './pages/ManagerView'

const qc = new QueryClient()

export default function App() {
  const { role } = useAppStore()

  return (
    <QueryClientProvider client={qc}>
      <ConfigProvider theme={{ algorithm: theme.defaultAlgorithm }}>
        {role === null && <RoleSelect />}
        {role === 'user' && <UserView />}
        {role === 'manager' && <ManagerView />}
      </ConfigProvider>
    </QueryClientProvider>
  )
}
