// Shell — exact port of nexus/shell.jsx + nexus/app.jsx layout

import { useState, useEffect } from 'react'
import { Icons } from './Icons'

const NAV = [
  { id: 'home',      label: 'Home',      icon: 'Home'    },
  { id: 'chat',      label: 'Chatbot',   icon: 'Chatbot' },
  { id: 'documents', label: 'Documents', icon: 'Doc'     },
  { id: 'social',    label: 'Social',    icon: 'Social'  },
]

// ---------------------------------------------------------------------------
// AgentChip — from nexus/ai-components.jsx
// ---------------------------------------------------------------------------
function AgentChip({ count = 3 }) {
  return (
    <div className="chip indigo" style={{ paddingLeft: 8 }}>
      <span className="pulse-dot" />
      <span>{count} agent{count === 1 ? '' : 's'} running</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sidebar — exact copy of nexus/shell.jsx Sidebar
// ---------------------------------------------------------------------------
function Sidebar({ active, onSelect, collapsed, onToggle, businessGroup }) {
  const W = collapsed ? 56 : 220
  return (
    <div style={{ width: W, flex: `0 0 ${W}px`, background: 'var(--bg-2)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', transition: 'width 200ms ease', overflow: 'hidden' }}>
      {/* Logo + workspace */}
      <div style={{ position: 'relative', height: 48, padding: collapsed ? '0 8px 0 12px' : '0 12px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid var(--border)' }}>
        <div style={{ width: 24, height: 24, borderRadius: 6, background: 'var(--indigo)', color: 'white', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 24px' }}>
          <Icons.Nexus size={14} />
        </div>
        {!collapsed && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{businessGroup}</div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Business Intelligent Platform</div>
          </div>
        )}
        <button
          className="btn ghost icon"
          onClick={onToggle}
          title={collapsed ? 'Expand' : 'Collapse'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{
            marginLeft: 'auto',
            position: collapsed ? 'absolute' : 'static',
            right: collapsed ? 6 : 'auto',
            top: collapsed ? '50%' : 'auto',
            transform: collapsed ? 'translateY(-50%)' : 'none',
            zIndex: 1,
          }}
        >
          {collapsed ? <Icons.ChevronLeft size={14} style={{ transform: 'rotate(180deg)' }} /> : <Icons.PinLeft size={14} />}
        </button>
      </div>

      {/* Workspace switcher */}
      {!collapsed && (
        <div style={{ padding: '10px 12px' }}>
          <div className="search-input" style={{ cursor: 'pointer' }}>
            <Icons.Search size={12} />
            <span style={{ flex: 1 }}>Quick switch…</span>
            <span className="kbd">⌘K</span>
          </div>
        </div>
      )}

      {/* Nav */}
      <div style={{ padding: collapsed ? '8px 6px' : '4px 8px', flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV.map((n) => {
          const Icon = Icons[n.icon]
          const isActive = active === n.id
          return (
            <div key={n.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelect(n.id)}
              title={n.label}
              style={collapsed ? { justifyContent: 'center', padding: '8px' } : {}}>
              <span className="nav-icon"><Icon size={16} /></span>
              {!collapsed && <span style={{ flex: 1 }}>{n.label}</span>}
              {!collapsed && n.id === 'chat' && <span className="chip teal dot" style={{ padding: '0 6px', fontSize: 10 }}>3</span>}
            </div>
          )
        })}
      </div>

      {/* Bottom */}
      <div style={{ padding: collapsed ? '8px 6px' : '8px', borderTop: '1px solid var(--border)' }}>
        <div className="nav-item" style={collapsed ? { justifyContent: 'center', padding: '8px' } : {}}>
          <span className="nav-icon"><Icons.Settings size={16} /></span>
          {!collapsed && <span>Settings</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px', marginTop: 4, borderRadius: 6, cursor: 'pointer' }} className="clickable">
          <div className="avatar indigo">AC</div>
          {!collapsed && (
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 600 }}>Amir Chowdhury</div>
              <div style={{ fontSize: 11, color: 'var(--text-3)' }}>Owner</div>
            </div>
          )}
          {!collapsed && <Icons.ChevronDown size={12} />}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TopBar — exact copy of nexus/shell.jsx TopBar
// ---------------------------------------------------------------------------
function TopBar({ title, breadcrumb, onToggleCtx, ctxOpen, onOpenCmd }) {
  return (
    <div style={{ height: 48, flex: '0 0 48px', borderBottom: '1px solid var(--border)', background: 'var(--bg)', display: 'flex', alignItems: 'center', padding: '0 16px', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <span style={{ fontSize: 14, fontWeight: 600 }}>{title}</span>
        {breadcrumb && <span style={{ fontSize: 12, color: 'var(--text-3)' }}>· {breadcrumb}</span>}
      </div>

      <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
        <button className="search-input" style={{ width: 360, maxWidth: '60%', justifyContent: 'flex-start' }} onClick={onOpenCmd}>
          <Icons.Search size={12} />
          <span style={{ flex: 1, textAlign: 'left' }}>Search or ask AI…</span>
          <span className="kbd">⌘</span>
          <span className="kbd">K</span>
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <AgentChip count={3} />
        <button className="btn ghost icon" title="Notifications" style={{ position: 'relative' }}>
          <Icons.Bell size={14} />
          <span style={{ position: 'absolute', top: 4, right: 4, width: 6, height: 6, borderRadius: 3, background: 'var(--coral)' }} />
        </button>
        <button className="btn ghost icon" title="AI context panel" onClick={onToggleCtx} style={{ color: ctxOpen ? 'var(--indigo)' : 'var(--text-2)', background: ctxOpen ? 'var(--indigo-soft)' : 'transparent' }}>
          <Icons.Sparkle size={14} />
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ContextPanel — exact copy of nexus/shell.jsx ContextPanel
// ---------------------------------------------------------------------------
function ContextPanel({ open, onClose, page }) {
  const traces = {
    home: [
      { tool: 'get_kpis', args: 'range=today', ms: 142, ok: true },
      { tool: 'summarize_alerts', args: 'priority=high', ms: 880, ok: true },
      { tool: 'retrieve_docs', args: 'q="daily briefing"', ms: 240, ok: true },
    ],
    chat: [
      { tool: 'retrieve_kb', args: 'q="refund policy"', ms: 320, ok: true },
      { tool: 'rank_chunks', args: 'topk=8', ms: 64, ok: true },
    ],
    documents: [
      { tool: 'list_reports', args: 'status=ready', ms: 88, ok: true },
      { tool: 'draft_report', args: 'type=weekly', ms: 4210, ok: true },
    ],
    social: [
      { tool: 'get_social_overview', args: 'platform=selected', ms: 180, ok: true },
      { tool: 'get_top_posts', args: 'platform=selected', ms: 260, ok: true },
    ],
  }[page] || []

  return (
    <div className={`ctx-panel ${open ? 'open' : ''}`}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icons.Sparkle size={14} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>AI context</span>
        </div>
        <button className="btn ghost icon" onClick={onClose}><Icons.X size={12} /></button>
      </div>
      <div style={{ padding: '16px' }}>
        <div className="label" style={{ marginBottom: 8 }}>What ran on this page</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {traces.map((t, i) => (
            <div key={i} className="panel-2" style={{ padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Icons.Flash size={12} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mono" style={{ fontSize: 11, color: 'var(--text)' }}>{t.tool}</div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.args}</div>
              </div>
              <span className="mono" style={{ fontSize: 10, color: 'var(--teal)' }}>{t.ms}ms</span>
            </div>
          ))}
        </div>

        <hr className="divider" style={{ margin: '16px 0' }} />

        <div className="label" style={{ marginBottom: 8 }}>Knowledge bases used</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {['ops-handbook.pdf', 'sales-q1-q2-2026.xlsx', 'support-macros.md', 'brand-voice.md'].map(n => (
            <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
              <Icons.Folder size={12} /><span className="mono" style={{ fontSize: 11 }}>{n}</span>
            </div>
          ))}
        </div>

        <hr className="divider" style={{ margin: '16px 0' }} />

        <div className="label" style={{ marginBottom: 8 }}>Suggested next actions</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <button className="btn" style={{ justifyContent: 'flex-start' }}><Icons.Sparkle size={12} />Generate weekly report</button>
          <button className="btn" style={{ justifyContent: 'flex-start' }}><Icons.Sparkle size={12} />Forecast next 7 days</button>
          <button className="btn" style={{ justifyContent: 'flex-start' }}><Icons.Sparkle size={12} />Find anomalies in pipeline</button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// CommandPalette — exact copy of nexus/shell.jsx CommandPalette
// ---------------------------------------------------------------------------
function CommandPalette({ open, onClose, onNavigate }) {
  if (!open) return null
  const items = [
    { kind: 'ask',    label: 'Ask AI — "summarize today"', icon: 'Sparkle' },
    { kind: 'nav',    id: 'home',      label: 'Go to Home',      icon: 'Home'    },
    { kind: 'nav',    id: 'chat',      label: 'Go to Chatbot',   icon: 'Chatbot' },
    { kind: 'nav',    id: 'documents', label: 'Go to Documents',  icon: 'Doc'     },
    { kind: 'nav',    id: 'social',    label: 'Go to Social', icon: 'Social' },
    { kind: 'action', label: 'Generate weekly report',    icon: 'Doc'  },
    { kind: 'action', label: 'Draft reply to top mention', icon: 'Send' },
    { kind: 'action', label: 'Show urgent tickets',        icon: 'Bell' },
  ]
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(8,10,16,0.6)', backdropFilter: 'blur(2px)', zIndex: 200, display: 'flex', justifyContent: 'center', paddingTop: '12vh' }}>
      <div onClick={(e) => e.stopPropagation()} className="panel" style={{ width: 560, maxWidth: '90%', background: 'var(--panel)', boxShadow: '0 24px 60px rgba(0,0,0,0.5)', height: 'fit-content' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
          <Icons.Search size={14} />
          <input className="input" autoFocus placeholder="Type to search or ask…" style={{ flex: 1, background: 'transparent', border: 'none', fontSize: 14 }} onKeyDown={e => e.key === 'Escape' && onClose()} />
          <span className="kbd">esc</span>
        </div>
        <div style={{ padding: 6 }}>
          <div className="label" style={{ padding: '6px 10px' }}>Suggested</div>
          {items.map((it, i) => {
            const Icon = Icons[it.icon]
            return (
              <div key={i} className="clickable" onClick={() => { if (it.kind === 'nav') onNavigate(it.id); onClose() }}
                style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 6, fontSize: 13, background: i === 0 ? 'var(--panel-2)' : 'transparent' }}>
                <Icon size={14} />
                <span style={{ flex: 1 }}>{it.label}</span>
                {i === 0 && <span className="kbd">⏎</span>}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shell — root layout from nexus/app.jsx
// ---------------------------------------------------------------------------
export function Shell({ page, onNavigate, children, businessGroup }) {
  const [collapsed, setCollapsed] = useState(false)
  const [ctxOpen,   setCtxOpen]   = useState(false)
  const [cmdOpen,   setCmdOpen]   = useState(false)

  const PAGES = {
    home:      { title: 'Home',      breadcrumb: 'Overview' },
    chat:      { title: 'Chatbot',   breadcrumb: 'AI Assistant' },
    documents: { title: 'Documents', breadcrumb: 'Knowledge base' },
    social:    { title: 'Social',    breadcrumb: 'Platform Analytics' },
  }
  const P = PAGES[page] || PAGES.home

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); setCmdOpen(o => !o) }
      if (e.key === 'Escape') setCmdOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <>
      <div style={{ display: 'flex', height: '100vh', minHeight: 0 }}>
        <Sidebar active={page} onSelect={onNavigate} collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} businessGroup={businessGroup} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, marginRight: ctxOpen ? 320 : 0, transition: 'margin-right 220ms ease' }}>
          <TopBar
            title={P.title}
            breadcrumb={P.breadcrumb}
            onToggleCtx={() => setCtxOpen(o => !o)}
            ctxOpen={ctxOpen}
            onOpenCmd={() => setCmdOpen(true)}
          />
          <div className="scroll-y" style={{ flex: 1, minHeight: 0 }}>
            {children}
          </div>
        </div>
        <ContextPanel open={ctxOpen} onClose={() => setCtxOpen(false)} page={page} />
      </div>
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNavigate={onNavigate} />
    </>
  )
}
