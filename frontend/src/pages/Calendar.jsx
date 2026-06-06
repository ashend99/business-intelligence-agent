import { useState, useEffect, useCallback, useRef } from 'react'
import { Icons } from '../components/Icons'

const API = 'http://localhost:8000'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December']

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toDateStr(date) {
  return date.toISOString().split('T')[0]
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  if (isoStr.length === 10) return 'All day'
  const d = new Date(isoStr)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDisplayDate(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr.length === 10 ? isoStr + 'T00:00:00' : isoStr)
  return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
}

function isSameDay(isoStr, year, month, day) {
  if (!isoStr) return false
  const s = isoStr.length === 10 ? isoStr : isoStr.split('T')[0]
  const [y, m, d] = s.split('-').map(Number)
  return y === year && m === month + 1 && d === day
}

function localISOString(date) {
  const pad = n => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

function Toast({ message, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [onClose])

  const bg = type === 'error' ? 'var(--coral)' : type === 'success' ? 'var(--teal)' : 'var(--indigo)'
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
      background: bg, color: '#fff', borderRadius: 10,
      padding: '12px 18px', fontSize: 13, fontWeight: 500,
      boxShadow: '0 8px 24px rgba(0,0,0,0.18)', display: 'flex', alignItems: 'center', gap: 10,
      maxWidth: 360,
    }}>
      <span style={{ flex: 1 }}>{message}</span>
      <button onClick={onClose} style={{ background: 'none', color: '#fff', opacity: 0.7, cursor: 'pointer', padding: 0, lineHeight: 1 }}>
        <Icons.X size={14} />
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Event Modal (create + edit)
// ---------------------------------------------------------------------------

function EventModal({ event, accounts, defaultDate, onSave, onDelete, onClose }) {
  const isEdit = Boolean(event?.id)
  const connectedAccounts = accounts.filter(a => a.connected)

  const [form, setForm] = useState(() => {
    if (event) {
      return {
        title: event.title || '',
        description: event.description || '',
        location: event.location || '',
        account_email: event.account_email || connectedAccounts[0]?.email || '',
        all_day: event.all_day || false,
        start: event.start ? (event.all_day ? event.start : localISOString(new Date(event.start))) : '',
        end: event.end ? (event.all_day ? event.end : localISOString(new Date(event.end))) : '',
      }
    }
    const base = defaultDate || new Date()
    const startStr = localISOString(new Date(base.getFullYear(), base.getMonth(), base.getDate(), 9, 0))
    const endStr = localISOString(new Date(base.getFullYear(), base.getMonth(), base.getDate(), 10, 0))
    return {
      title: '', description: '', location: '',
      account_email: connectedAccounts[0]?.email || '',
      all_day: false, start: startStr, end: endStr,
    }
  })

  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.title.trim()) return
    if (!form.account_email) return
    setSaving(true)
    await onSave({
      ...form,
      start: form.all_day ? form.start.slice(0, 10) : new Date(form.start).toISOString(),
      end: form.all_day ? form.end.slice(0, 10) : new Date(form.end).toISOString(),
      ...(isEdit ? { id: event.id } : {}),
    })
    setSaving(false)
  }

  const handleDelete = async () => {
    setDeleting(true)
    await onDelete(event.id, event.account_email)
    setDeleting(false)
  }

  const inputStyle = {
    width: '100%', padding: '8px 10px', borderRadius: 7, fontSize: 13,
    border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)',
    outline: 'none', boxSizing: 'border-box',
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 500,
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="panel" style={{ width: 440, maxHeight: '90vh', overflowY: 'auto', padding: 24, borderRadius: 14, boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>
            {isEdit ? 'Edit Event' : 'New Event'}
          </div>
          <button className="btn ghost icon" onClick={onClose}><Icons.X size={14} /></button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Title */}
          <input
            style={inputStyle}
            placeholder="Event title *"
            value={form.title}
            onChange={e => set('title', e.target.value)}
            autoFocus
          />

          {/* Account */}
          <div>
            <div className="label" style={{ marginBottom: 5 }}>Calendar</div>
            <select style={inputStyle} value={form.account_email} onChange={e => set('account_email', e.target.value)}>
              {connectedAccounts.length === 0
                ? <option value="">No accounts connected</option>
                : connectedAccounts.map(a => (
                    <option key={a.email} value={a.email}>{a.name}</option>
                  ))
              }
            </select>
          </div>

          {/* All day toggle */}
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, width: 'fit-content' }}>
            <input type="checkbox" checked={form.all_day} onChange={e => set('all_day', e.target.checked)} />
            <span style={{ color: 'var(--text-2)' }}>All day</span>
          </label>

          {/* Date / time */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div style={{ minWidth: 0 }}>
              <div className="label" style={{ marginBottom: 5 }}>Start</div>
              <input
                style={inputStyle}
                type={form.all_day ? 'date' : 'datetime-local'}
                value={form.all_day ? form.start.slice(0, 10) : form.start}
                onChange={e => set('start', e.target.value)}
              />
            </div>
            <div style={{ minWidth: 0 }}>
              <div className="label" style={{ marginBottom: 5 }}>End</div>
              <input
                style={inputStyle}
                type={form.all_day ? 'date' : 'datetime-local'}
                value={form.all_day ? form.end.slice(0, 10) : form.end}
                onChange={e => set('end', e.target.value)}
              />
            </div>
          </div>

          {/* Location */}
          <input
            style={inputStyle}
            placeholder="Location (optional)"
            value={form.location}
            onChange={e => set('location', e.target.value)}
          />

          {/* Description */}
          <textarea
            style={{ ...inputStyle, minHeight: 72, resize: 'vertical', fontFamily: 'inherit' }}
            placeholder="Description (optional)"
            value={form.description}
            onChange={e => set('description', e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20, gap: 10 }}>
          <div>
            {isEdit && (
              <button
                className="btn ghost"
                onClick={handleDelete}
                disabled={deleting}
                style={{ color: 'var(--coral)', fontSize: 13 }}
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn ghost" onClick={onClose}>Cancel</button>
            <button
              className="btn primary"
              onClick={handleSave}
              disabled={saving || !form.title.trim() || !form.account_email}
            >
              {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Event'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Month grid
// ---------------------------------------------------------------------------

function MonthGrid({ year, month, events, activeEmails, onDayClick, onEventClick }) {
  const firstDay = (new Date(year, month, 1).getDay() + 6) % 7
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const today = new Date()

  const visibleEvents = events.filter(e => activeEmails.has(e.account_email))

  const cells = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  const rows = []
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7))
  while (rows[rows.length - 1].length < 7) rows[rows.length - 1].push(null)

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', borderBottom: '1px solid var(--border)' }}>
        {DAYS.map(d => (
          <div key={d} style={{ padding: '8px 10px', fontSize: 11, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', textAlign: 'center' }}>
            {d}
          </div>
        ))}
      </div>

      {/* Grid rows */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {rows.map((row, ri) => (
          <div key={ri} style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', borderBottom: ri < rows.length - 1 ? '1px solid var(--border)' : 'none' }}>
            {row.map((day, ci) => {
              if (!day) return <div key={ci} style={{ background: 'var(--bg-2)', borderRight: ci < 6 ? '1px solid var(--border)' : 'none', overflow: 'hidden' }} />

              const isToday = today.getFullYear() === year && today.getMonth() === month && today.getDate() === day
              const dayEvents = visibleEvents.filter(e => isSameDay(e.start, year, month, day))

              return (
                <div
                  key={ci}
                  onClick={() => onDayClick(new Date(year, month, day))}
                  style={{
                    padding: '6px 8px', cursor: 'pointer',
                    borderRight: ci < 6 ? '1px solid var(--border)' : 'none',
                    background: isToday ? 'var(--indigo-soft)' : 'var(--bg)',
                    transition: 'background 0.1s',
                    overflow: 'hidden',
                  }}
                  onMouseEnter={e => { if (!isToday) e.currentTarget.style.background = 'var(--bg-2)' }}
                  onMouseLeave={e => { if (!isToday) e.currentTarget.style.background = 'var(--bg)' }}
                >
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: isToday ? 700 : 400,
                    background: isToday ? 'var(--indigo)' : 'transparent',
                    color: isToday ? '#fff' : 'var(--text)',
                    marginBottom: 4,
                  }}>
                    {day}
                  </div>
                  {dayEvents.slice(0, 3).map(ev => (
                    <div
                      key={ev.id}
                      onClick={e => { e.stopPropagation(); onEventClick(ev) }}
                      style={{
                        fontSize: 11, padding: '2px 6px', borderRadius: 4, marginBottom: 2,
                        background: ev.color + '22', color: ev.color,
                        fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        cursor: 'pointer', border: `1px solid ${ev.color}33`,
                      }}
                    >
                      {!ev.all_day && <span style={{ opacity: 0.7, marginRight: 4 }}>{formatTime(ev.start)}</span>}
                      {ev.title}
                    </div>
                  ))}
                  {dayEvents.length > 3 && (
                    <div style={{ fontSize: 10, color: 'var(--text-3)', paddingLeft: 2 }}>
                      +{dayEvents.length - 3} more
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Upcoming events sidebar
// ---------------------------------------------------------------------------

function UpcomingSidebar({ events, accounts, activeEmails, onEventClick }) {
  const now = new Date()
  const cutoff = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000)

  const upcoming = events
    .filter(e => activeEmails.has(e.account_email))
    .filter(e => {
      const start = new Date(e.start?.length === 10 ? e.start + 'T00:00:00' : e.start)
      return start >= now && start <= cutoff
    })
    .slice(0, 20)

  return (
    <div style={{ width: 240, borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Upcoming
        </div>
        <div className="label">Next 14 days</div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        {upcoming.length === 0 ? (
          <div style={{ padding: '20px 16px', fontSize: 12, color: 'var(--text-3)', textAlign: 'center' }}>
            No upcoming events
          </div>
        ) : (
          upcoming.map(ev => (
            <div
              key={ev.id}
              onClick={() => onEventClick(ev)}
              style={{
                padding: '8px 16px', cursor: 'pointer', borderLeft: `3px solid ${ev.color}`,
                marginBottom: 2,
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {ev.title}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-3)' }}>{formatDisplayDate(ev.start)}</div>
              {!ev.all_day && <div style={{ fontSize: 11, color: ev.color }}>{formatTime(ev.start)}</div>}
              <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 2 }}>{ev.account_name}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Accounts panel
// ---------------------------------------------------------------------------

function AccountsPanel({ accounts, onConnect, onDisconnect, loading }) {
  return (
    <div style={{ borderTop: '1px solid var(--border)', padding: '12px 16px' }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
        Connected Accounts
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {accounts.map(acc => (
          <div key={acc.email} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: acc.connected ? acc.color : 'var(--border)', flex: '0 0 8px' }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{acc.name}</div>
              <div style={{ fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{acc.email}</div>
            </div>
            {acc.connected ? (
              <button
                className="btn ghost"
                style={{ fontSize: 11, padding: '3px 8px', color: 'var(--text-3)' }}
                onClick={() => onDisconnect(acc.email)}
              >
                Disconnect
              </button>
            ) : (
              <button
                className="btn primary"
                style={{ fontSize: 11, padding: '3px 8px' }}
                onClick={() => onConnect(acc.email)}
              >
                Connect
              </button>
            )}
          </div>
        ))}
        {accounts.length === 0 && (
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>No accounts configured</div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Calendar page
// ---------------------------------------------------------------------------

export function Calendar() {
  const [accounts, setAccounts] = useState([])
  const [events, setEvents] = useState([])
  const [currentDate, setCurrentDate] = useState(new Date())
  const [activeEmails, setActiveEmails] = useState(new Set())
  const [modal, setModal] = useState(null)        // null | { mode: 'create', date } | { mode: 'edit', event }
  const [toast, setToast] = useState(null)
  const [loadingAccounts, setLoadingAccounts] = useState(true)
  const [loadingEvents, setLoadingEvents] = useState(false)

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  // -------------------------------------------------------------------------
  // Handle OAuth redirect back from Google
  // -------------------------------------------------------------------------
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('calendar_connected')) {
      const email = params.get('email') || ''
      setToast({ message: `Successfully connected ${email}`, type: 'success' })
      window.history.replaceState({}, '', window.location.pathname)
    } else if (params.get('calendar_error')) {
      setToast({ message: 'Failed to connect Google account. Please try again.', type: 'error' })
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  // -------------------------------------------------------------------------
  // Fetch accounts
  // -------------------------------------------------------------------------
  const fetchAccounts = useCallback(async () => {
    setLoadingAccounts(true)
    try {
      const res = await fetch(`${API}/api/calendar/accounts`)
      const data = await res.json()
      setAccounts(data)
      setActiveEmails(new Set(data.filter(a => a.connected).map(a => a.email)))
    } catch {
      setToast({ message: 'Failed to load accounts', type: 'error' })
    } finally {
      setLoadingAccounts(false)
    }
  }, [])

  useEffect(() => { fetchAccounts() }, [fetchAccounts])

  // -------------------------------------------------------------------------
  // Fetch events whenever month or accounts change
  // -------------------------------------------------------------------------
  const fetchEvents = useCallback(async () => {
    const connectedEmails = accounts.filter(a => a.connected).map(a => a.email)
    if (connectedEmails.length === 0) { setEvents([]); return }

    setLoadingEvents(true)
    try {
      const start = new Date(year, month, 1).toISOString()
      const end = new Date(year, month + 1, 1).toISOString()
      const res = await fetch(
        `${API}/api/calendar/events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
      )
      const data = await res.json()
      setEvents(Array.isArray(data) ? data : [])
    } catch {
      setToast({ message: 'Failed to load events', type: 'error' })
    } finally {
      setLoadingEvents(false)
    }
  }, [accounts, year, month])

  useEffect(() => { fetchEvents() }, [fetchEvents])

  // -------------------------------------------------------------------------
  // Account connect / disconnect
  // -------------------------------------------------------------------------
  const handleConnect = async (email) => {
    try {
      const res = await fetch(`${API}/api/calendar/accounts/${encodeURIComponent(email)}/connect`)
      const data = await res.json()
      if (data.auth_url) window.location.href = data.auth_url
    } catch {
      setToast({ message: 'Failed to start OAuth flow', type: 'error' })
    }
  }

  const handleDisconnect = async (email) => {
    try {
      await fetch(`${API}/api/calendar/accounts/${encodeURIComponent(email)}`, { method: 'DELETE' })
      setToast({ message: `Disconnected ${email}`, type: 'success' })
      fetchAccounts()
    } catch {
      setToast({ message: 'Failed to disconnect account', type: 'error' })
    }
  }

  // -------------------------------------------------------------------------
  // Event CRUD
  // -------------------------------------------------------------------------
  const handleSaveEvent = async (form) => {
    const isEdit = Boolean(form.id)
    const url = isEdit ? `${API}/api/calendar/events/${form.id}` : `${API}/api/calendar/events`
    const method = isEdit ? 'PUT' : 'POST'

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error()
      setToast({ message: isEdit ? 'Event updated' : 'Event created', type: 'success' })
      setModal(null)
      fetchEvents()
    } catch {
      setToast({ message: 'Failed to save event', type: 'error' })
    }
  }

  const handleDeleteEvent = async (eventId, accountEmail) => {
    try {
      const res = await fetch(
        `${API}/api/calendar/events/${eventId}?account_email=${encodeURIComponent(accountEmail)}`,
        { method: 'DELETE' }
      )
      if (!res.ok) throw new Error()
      setToast({ message: 'Event deleted', type: 'success' })
      setModal(null)
      fetchEvents()
    } catch {
      setToast({ message: 'Failed to delete event', type: 'error' })
    }
  }

  const toggleEmail = (email) => {
    setActiveEmails(prev => {
      const next = new Set(prev)
      next.has(email) ? next.delete(email) : next.add(email)
      return next
    })
  }

  const prevMonth = () => setCurrentDate(d => new Date(d.getFullYear(), d.getMonth() - 1, 1))
  const nextMonth = () => setCurrentDate(d => new Date(d.getFullYear(), d.getMonth() + 1, 1))
  const goToday = () => setCurrentDate(new Date())

  const connectedAccounts = accounts.filter(a => a.connected)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Page header ── */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
      }}>
        <div style={{ flex: 1 }}>
          {/* <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Calendar</div>
          <div className="label">Manage events across all business calendars</div> */}
        </div>

        {/* Account filter pills */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {connectedAccounts.map(acc => (
            <button
              key={acc.email}
              onClick={() => toggleEmail(acc.email)}
              style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 20, cursor: 'pointer',
                border: `1px solid ${acc.color}`,
                background: activeEmails.has(acc.email) ? acc.color : 'transparent',
                color: activeEmails.has(acc.email) ? '#fff' : acc.color,
                fontWeight: 500, transition: 'all 0.15s',
              }}
            >
              {acc.name}
            </button>
          ))}
        </div>

        <button
          className="btn primary"
          style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}
          onClick={() => setModal({ mode: 'create', date: new Date() })}
          disabled={connectedAccounts.length === 0}
        >
          <Icons.Plus size={13} />
          New Event
        </button>
      </div>

      {/* ── Body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Left: calendar ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Month nav */}
          <div style={{
            padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10,
            borderBottom: '1px solid var(--border)', flexShrink: 0,
          }}>
            <button className="btn ghost icon" onClick={prevMonth}><Icons.ChevronLeft size={14} /></button>
            <button className="btn ghost icon" onClick={nextMonth} style={{ transform: 'rotate(180deg)' }}><Icons.ChevronLeft size={14} /></button>
            <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', minWidth: 160 }}>
              {MONTHS[month]} {year}
            </span>
            <button className="btn ghost" style={{ fontSize: 12 }} onClick={goToday}>Today</button>
            {loadingEvents && <span className="label" style={{ fontSize: 11 }}>Loading…</span>}
          </div>

          {/* Grid */}
          <MonthGrid
            year={year}
            month={month}
            events={events}
            activeEmails={activeEmails}
            onDayClick={date => setModal({ mode: 'create', date })}
            onEventClick={ev => setModal({ mode: 'edit', event: ev })}
          />
        </div>

        {/* ── Right sidebar ── */}
        <div style={{ width: 240, display: 'flex', flexDirection: 'column', borderLeft: '1px solid var(--border)', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <UpcomingSidebar
              events={events}
              accounts={accounts}
              activeEmails={activeEmails}
              onEventClick={ev => setModal({ mode: 'edit', event: ev })}
            />
          </div>
          <AccountsPanel
            accounts={accounts}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
            loading={loadingAccounts}
          />
        </div>
      </div>

      {/* ── Modals ── */}
      {modal && (
        <EventModal
          event={modal.mode === 'edit' ? modal.event : null}
          accounts={accounts}
          defaultDate={modal.mode === 'create' ? modal.date : null}
          onSave={handleSaveEvent}
          onDelete={handleDeleteEvent}
          onClose={() => setModal(null)}
        />
      )}

      {/* ── Toast ── */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  )
}
