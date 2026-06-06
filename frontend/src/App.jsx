import { useEffect, useState } from 'react'
import { Shell } from './components/Shell'
import { Home } from './pages/Home'
import { Chat } from './pages/Chat'
import { Documents } from './pages/Documents'
import { Social } from './pages/Social'
import { Calendar } from './pages/Calendar'
import { businessConfig } from './config'

const APP_PAGE_STORAGE_KEY = 'bi.app.activePage'
const APP_THEME_STORAGE_KEY = 'bi.app.theme'
const THEMES = ['light', 'dark', 'midnight', 'ocean', 'sunset']

const PAGES = {
  home: Home,
  chat: Chat,
  documents: Documents,
  social: Social,
  calendar: Calendar,
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

  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem(APP_THEME_STORAGE_KEY)
      return saved && THEMES.includes(saved) ? saved : 'light'
    } catch {
      return 'light'
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(APP_PAGE_STORAGE_KEY, page)
    } catch {}
  }, [page])

  useEffect(() => {
    try {
      localStorage.setItem(APP_THEME_STORAGE_KEY, theme)
    } catch {}
    if (theme === 'light') {
      document.documentElement.removeAttribute('data-theme')
    } else {
      document.documentElement.setAttribute('data-theme', theme)
    }
  }, [theme])

  const Page = PAGES[page] || Home
  return (
    <Shell page={page} onNavigate={setPage} businessGroup={businessConfig.business.group} theme={theme} onThemeChange={setTheme}>
      <Page onNavigate={setPage} />
    </Shell>
  )
}
