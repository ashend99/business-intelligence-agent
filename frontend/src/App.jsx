import { useEffect, useState } from 'react'
import { Shell } from './components/Shell'
import { Home } from './pages/Home'
import { Chat } from './pages/Chat'
import { Documents } from './pages/Documents'
import { FacebookAnalytics } from './pages/FacebookAnalytics'
import { businessConfig } from './config'

const APP_PAGE_STORAGE_KEY = 'bi.app.activePage'

const PAGES = {
  home: Home,
  chat: Chat,
  documents: Documents,
  social: FacebookAnalytics,
}

export default function App() {
  const [page, setPage] = useState(() => {
    try {
      const saved = localStorage.getItem(APP_PAGE_STORAGE_KEY)
      return saved && PAGES[saved] ? saved : 'home'
    } catch {
      return 'home'
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(APP_PAGE_STORAGE_KEY, page)
    } catch {
      // Ignore storage errors (private mode, blocked storage, etc.)
    }
  }, [page])

  const Page = PAGES[page] || Home
  return (
    <Shell page={page} onNavigate={setPage} businessGroup={businessConfig.business.group}>
      <Page onNavigate={setPage} />
    </Shell>
  )
}
