import { useState } from 'react'
import { Shell } from './components/Shell'
import { Home } from './pages/Home'
import { Chat } from './pages/Chat'
import { Documents } from './pages/Documents'
import { businessConfig } from './config'

const PAGES = { home: Home, chat: Chat, documents: Documents }

export default function App() {
  const [page, setPage] = useState('home')
  const Page = PAGES[page] || Home
  return (
    <Shell page={page} onNavigate={setPage} businessGroup={businessConfig.business.group}>
      <Page onNavigate={setPage} />
    </Shell>
  )
}
