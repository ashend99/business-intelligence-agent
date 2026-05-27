// Facebook Analytics — ported from facebook-analytics/page.jsx
// Integrated into the Shell layout (Shell provides the outer sidebar/topbar).

import { useState, useRef, useEffect, useMemo } from 'react'
import { Icons } from '../components/Icons'
import { MultiLine, DonutMulti } from '../components/Charts'

// ---------------------------------------------------------------------------
// Platform config
// ---------------------------------------------------------------------------
const PLATFORMS = [
  { id: 'fb', label: 'Facebook',  icon: 'Facebook',  tone: 'fb',  accent: '#1877F2', pageLabel: 'Facebook Page',    pageSubtitle: 'Overview of your Facebook Page performance'     },
  { id: 'ig', label: 'Instagram', icon: 'Instagram', tone: 'ig',  accent: '#E1306C', pageLabel: 'Instagram Profile', pageSubtitle: 'Overview of your Instagram account performance' },
  { id: 'tk', label: 'TikTok',   icon: 'Flash',     tone: 'tk',  accent: '#010101', pageLabel: 'TikTok Account',    pageSubtitle: 'Overview of your TikTok account performance'   },
]

// ---------------------------------------------------------------------------
// PlatformDropdown
// ---------------------------------------------------------------------------
function PlatformDropdown({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const current = PLATFORMS.find(p => p.id === value) || PLATFORMS[0]
  const Icon = Icons[current.icon]

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        className="select-btn"
        style={{ gap: 10, padding: '7px 12px', fontSize: 13, fontWeight: 600 }}
        onClick={() => setOpen(o => !o)}
      >
        <span className={`platform-tile ${current.tone}`} style={{ width: 26, height: 26, borderRadius: 6 }}>
          <Icon size={14} />
        </span>
        <span>{current.label}</span>
        <Icons.ChevronDown size={12} style={{ marginLeft: 2, opacity: 0.6 }} />
      </button>

      {open && (
        <div className="panel" style={{
          position: 'absolute', top: 'calc(100% + 6px)', left: 0,
          zIndex: 50, minWidth: 180, padding: 4,
          boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
        }}>
          {PLATFORMS.map(p => {
            const PIcon = Icons[p.icon]
            const active = p.id === value
            return (
              <button
                type="button"
                key={p.id}
                onClick={() => { onChange(p.id); setOpen(false) }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  width: '100%', padding: '8px 10px', borderRadius: 6, border: 'none',
                  background: active ? 'var(--indigo-soft)' : 'transparent',
                  color: active ? 'var(--indigo)' : 'var(--text-2)',
                  fontWeight: active ? 600 : 400, fontSize: 13, cursor: 'pointer',
                  fontFamily: 'inherit', textAlign: 'left',
                }}
              >
                <span className={`platform-tile ${p.tone}`} style={{ width: 26, height: 26, borderRadius: 6 }}>
                  <PIcon size={14} />
                </span>
                {p.label}
                {active && <Icons.Check size={13} style={{ marginLeft: 'auto', color: 'var(--indigo)' }} />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

function PageDropdown({ pages, value, onChange, loading, tone }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const current = value || pages[0] || null

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!pages.length) setOpen(false)
  }, [pages.length])

  if (!pages.length) {
    return (
      <button type="button" className="select-btn" disabled={loading}>
        <span style={{ width: 20, height: 20, borderRadius: 4, background: `var(--${tone})`, color: 'white', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, fontWeight: 700 }}>TN</span>
        <span>{loading ? 'Loading…' : 'None'}</span>
        <Icons.ChevronDown size={11} />
      </button>
    )
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        className="select-btn"
        style={{ gap: 8 }}
        onClick={() => setOpen(o => !o)}
      >
        {current?.picture_url
          ? <img src={current.picture_url} alt="" style={{ width: 20, height: 20, borderRadius: 4, objectFit: 'cover' }} />
          : <span style={{ width: 20, height: 20, borderRadius: 4, background: `var(--${tone})`, display: 'inline-block' }} />
        }
        <span>{current?.name || 'Select page'}</span>
        <Icons.ChevronDown size={11} />
      </button>

      {open && (
        <div className="panel" style={{
          position: 'absolute', top: 'calc(100% + 6px)', left: 0,
          zIndex: 50, minWidth: 220, padding: 4,
          boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
        }}>
          {pages.map(page => {
            const active = page.id === current?.id
            return (
              <button
                type="button"
                key={page.id}
                onClick={() => {
                  onChange(page)
                  setOpen(false)
                }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  width: '100%', padding: '8px 10px', borderRadius: 6, border: 'none',
                  background: active ? 'var(--indigo-soft)' : 'transparent',
                  color: active ? 'var(--indigo)' : 'var(--text-2)',
                  fontWeight: active ? 600 : 400, fontSize: 13, cursor: 'pointer',
                  fontFamily: 'inherit', textAlign: 'left',
                }}
              >
                {page.picture_url
                  ? <img src={page.picture_url} alt="" style={{ width: 20, height: 20, borderRadius: 4, objectFit: 'cover' }} />
                  : <span style={{ width: 20, height: 20, borderRadius: 4, background: `var(--${tone})`, display: 'inline-block' }} />
                }
                <span>{page.name}</span>
                {active && <Icons.Check size={13} style={{ marginLeft: 'auto', color: 'var(--indigo)' }} />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-nav tabs (replaces the standalone page's own sidebar sections)
// ---------------------------------------------------------------------------
const TABS = [
  { id: 'overview',     label: 'Overview'     },
  { id: 'analytics',   label: 'Analytics'    },
  { id: 'posts',       label: 'Posts'        },
]

const METRICS_REFRESH_INTERVAL_MS = 600_000
const DEFAULT_WINDOW_UNIT = 'day'
const DEFAULT_WINDOW_COUNT = 7
const SOCIAL_UI_STORAGE_KEY = 'bi.social.ui.v1'

const _readSocialUiState = () => {
  try {
    const raw = localStorage.getItem(SOCIAL_UI_STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

const _writeSocialUiState = (patch) => {
  try {
    const current = _readSocialUiState()
    localStorage.setItem(SOCIAL_UI_STORAGE_KEY, JSON.stringify({ ...current, ...patch }))
  } catch {
    // Ignore storage errors.
  }
}

const _toIsoDate = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const getDefaultOverviewRange = () => ({
  since: _toIsoDate(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)),
  until: _toIsoDate(new Date()),
})
const WINDOW_UNIT_OPTIONS = [
  { value: 'day', label: 'Day' },
  { value: 'month', label: 'Month' },
]
const WINDOW_COUNT_OPTIONS = {
  day: [7, 14, 21, 30],
  month: [1, 2, 3],
}
const PERIOD_OPTIONS = [
  { value: 'day', label: 'Day' },
  { value: 'week', label: 'Week' },
  { value: 'days_28', label: '28 Days' },
  { value: 'month', label: 'Month' },
  { value: 'lifetime', label: 'Lifetime' },
  { value: 'total_over_range', label: 'Total Over Range' },
]

const _formatCompact = (value) => {
  const numeric = Number(value || 0)
  if (!Number.isFinite(numeric) || numeric <= 0) return '0'
  if (numeric >= 1_000_000) return `${(numeric / 1_000_000).toFixed(1)}M`
  if (numeric >= 1_000) return `${(numeric / 1_000).toFixed(1)}K`
  return `${Math.round(numeric)}`
}

const _formatPostTimestamp = (isoValue) => {
  if (!isoValue) return '—'
  const parsed = new Date(isoValue)
  if (Number.isNaN(parsed.getTime())) return '—'
  const datePart = parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  const timePart = parsed.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return `${datePart} · ${timePart}`
}

const _truncatePostCaption = (value, maxLength = 24) => {
  const text = `${value || ''}`.trim()
  if (!text) return 'Untitled post'
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength - 3).trimEnd()}...`
}

const _inclusiveDaysBetween = (sinceIso, untilIso) => {
  if (!sinceIso || !untilIso) return 30
  const sinceDate = new Date(`${sinceIso}T00:00:00`)
  const untilDate = new Date(`${untilIso}T00:00:00`)
  if (Number.isNaN(sinceDate.getTime()) || Number.isNaN(untilDate.getTime()) || sinceDate > untilDate) return 30
  const msPerDay = 24 * 60 * 60 * 1000
  return Math.floor((untilDate.getTime() - sinceDate.getTime()) / msPerDay) + 1
}

const _formatDateRangeShort = (sinceIso, untilIso) => {
  if (!sinceIso || !untilIso) return '—'
  const sinceDate = new Date(`${sinceIso}T00:00:00`)
  const untilDate = new Date(`${untilIso}T00:00:00`)
  if (Number.isNaN(sinceDate.getTime()) || Number.isNaN(untilDate.getTime())) return '—'
  const fmt = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })
  return `${fmt.format(sinceDate)} - ${fmt.format(untilDate)}`
}

const _shiftIsoDate = (isoDate, days) => {
  if (!isoDate) return null
  const date = new Date(`${isoDate}T00:00:00`)
  if (Number.isNaN(date.getTime())) return null
  date.setDate(date.getDate() + days)
  return _toIsoDate(date)
}

// ---------------------------------------------------------------------------
// Local components
// ---------------------------------------------------------------------------
function Section({ title, subtitle, right, children, style }) {
  return (
    <div className="panel" style={{ padding: 22, display: 'flex', flexDirection: 'column', ...style }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{title}</div>
          {subtitle && <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>{subtitle}</div>}
        </div>
        {right}
      </div>
      {children}
    </div>
  )
}

function GranularitySelect({ value = OVERVIEW_PERIOD, onChange }) {
  const current = PERIOD_OPTIONS.find(option => option.value === value)

  return (
    <label className="select-btn" style={{ gap: 8 }}>
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        style={{
          appearance: 'none',
          border: 'none',
          outline: 'none',
          background: 'transparent',
          color: 'inherit',
          font: 'inherit',
          cursor: 'pointer',
          paddingRight: 12,
        }}
      >
        {PERIOD_OPTIONS.map(option => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
      <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{current?.label || 'Day'}</span>
      <Icons.ChevronDown size={11} />
    </label>
  )
}

function TimeRangeWidget({
  windowUnit,
  windowCount,
  since,
  until,
  timezone,
  onApply,
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const [draftUnit, setDraftUnit] = useState(windowUnit)
  const [draftCount, setDraftCount] = useState(windowCount)

  useEffect(() => {
    setDraftUnit(windowUnit)
    setDraftCount(windowCount)
  }, [windowUnit, windowCount])

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const unitLabel = WINDOW_UNIT_OPTIONS.find(option => option.value === windowUnit)?.label || windowUnit
  const summaryLabel = `${windowCount} ${unitLabel}${windowCount > 1 ? 's' : ''} · ${since} to ${until}`

  const applyChanges = () => {
    onApply({ windowUnit: draftUnit, windowCount: Number(draftCount) || 1 })
    setOpen(false)
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button type="button" className="select-btn" onClick={() => setOpen(v => !v)}>
        <Icons.Calendar size={13} />
        <span>{summaryLabel}</span>
        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{timezone}</span>
        <Icons.ChevronDown size={11} />
      </button>

      {open && (
        <div className="panel" style={{
          position: 'absolute',
          top: 'calc(100% + 8px)',
          right: 0,
          zIndex: 60,
          minWidth: 340,
          padding: 12,
          boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}>
          <div style={{ fontSize: 12, color: 'var(--text-3)', fontWeight: 600 }}>Time Range</div>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
            <span style={{ color: 'var(--text-3)' }}>Window Unit</span>
            <select
              value={draftUnit}
              onChange={(e) => {
                const nextUnit = e.target.value
                setDraftUnit(nextUnit)
                const nextOptions = WINDOW_COUNT_OPTIONS[nextUnit] || [1]
                if (!nextOptions.includes(Number(draftCount))) {
                  setDraftCount(nextOptions[0])
                }
              }}
              className="select-btn"
              style={{ width: '100%' }}
            >
              {WINDOW_UNIT_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
            <span style={{ color: 'var(--text-3)' }}>Count</span>
            <select
              value={draftCount}
              onChange={(e) => setDraftCount(Number(e.target.value))}
              className="select-btn"
              style={{ width: '100%' }}
            >
              {(WINDOW_COUNT_OPTIONS[draftUnit] || [1]).map(count => (
                <option key={count} value={count}>{count}</option>
              ))}
            </select>
          </label>

          <div style={{ fontSize: 11, color: 'var(--text-3)' }}>
            Applies to: {since} to {until} ({timezone})
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button type="button" className="btn" onClick={() => setOpen(false)}>Cancel</button>
            <button type="button" className="btn primary" onClick={applyChanges}>Apply</button>
          </div>
        </div>
      )}
    </div>
  )
}

function KPICard({ label, value, delta, color, spark, comparisonLabel, description, changeValue, trend = 'flat' }) {
  const isNeg = trend === 'down' || delta.startsWith('−') || delta.startsWith('-')
  const isFlat = trend === 'flat' && !isNeg
  const changeText = `${isNeg ? '−' : '+'}${changeValue || '0'}`
  return (
    <div className="panel" style={{ padding: 14, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 12, color: 'var(--text-3)', fontWeight: 500 }}>{label}</span>
        <button
          type="button"
          aria-label={description ? `${label} details` : `${label} info`}
          title={description || label}
          style={{
            width: 20,
            height: 20,
            border: 'none',
            background: 'transparent',
            color: 'var(--text-3)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 0,
            cursor: 'pointer',
          }}
        >
          <Icons.Info size={13} />
        </button>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 8 }}>
        <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em' }}>{value}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2, flexWrap: 'wrap' }}>
        <span className="mono" style={{ fontSize: 11, color: isFlat ? 'var(--text-3)' : (isNeg ? 'var(--coral)' : 'var(--teal)') }}>
          {isFlat ? '0' : `${isNeg ? '↓' : '↑'} ${changeText}`}
        </span>
        <span className="mono" style={{ fontSize: 11, color: isFlat ? 'var(--text-3)' : (isNeg ? 'var(--coral)' : 'var(--teal)') }}>
          ({delta.replace(/^[−-]/, '')})
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>{comparisonLabel || 'vs previous period'}</div>
    </div>
  )
}

function ReachCard({ metric, loading }) {
  const totalCount = metric?.total_count ?? metric?.current_total ?? 0
  const hasMetricValue = metric?.total_count != null || metric?.current_total != null
  const displayValue = hasMetricValue
    ? new Intl.NumberFormat().format(Number(totalCount) || 0)
    : (loading ? '...' : '0')

  return (
    <KPICard
      label="Reach"
      value={displayValue}
      delta={metric?.delta || '0.0%'}
      color="#4A8CFF"
      comparisonLabel={metric?.comparison_label || 'vs previous period'}
      description={metric?.description || 'Reach for the selected window.'}
      changeValue={metric?.change_value || '0'}
      trend={metric?.trend || 'flat'}
      spark={metric?.spark?.length ? metric.spark : [0, 0, 0, 0, 0, 0, 0]}
    />
  )
}

function SnapshotMetricCard({ label, value, unavailable = false }) {
  const display = unavailable ? '—' : (value ?? '0')
  return (
    <div className="panel" style={{ padding: 14, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ fontSize: 12, color: 'var(--text-3)', fontWeight: 500 }}>{label}</div>
      <div style={{ marginTop: 8, fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em', color: unavailable ? 'var(--text-3)' : 'var(--text)' }}>
        {display}
      </div>
    </div>
  )
}

function AgeGenderBars() {
  const buckets = [
    ['13-17',  6,  4],
    ['18-24', 14, 10],
    ['25-34', 30, 22],
    ['35-44', 22, 18],
    ['45-54', 11,  8],
    ['55-64',  6,  5],
    ['65+',    4,  3],
  ]
  const max = 32
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, height: 110 }}>
        {/* y-axis */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', paddingBottom: 18 }}>
          {['30%', '20%', '10%', '0%'].map(y => (
            <span key={y} className="mono" style={{ fontSize: 10, color: 'var(--text-3)' }}>{y}</span>
          ))}
        </div>
        {buckets.map(([label, w, m]) => (
          <div key={label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', gap: 3 }}>
              <div style={{ width: 10, height: `${(w / max) * 100}%`, background: 'var(--blue)', borderRadius: '3px 3px 0 0' }} />
              <div style={{ width: 10, height: `${(m / max) * 100}%`, background: 'var(--purple)', borderRadius: '3px 3px 0 0' }} />
            </div>
            <span className="mono" style={{ fontSize: 9, color: 'var(--text-3)', marginTop: 5 }}>{label}</span>
          </div>
        ))}
      </div>
      {/* Legend */}
      <div style={{ display: 'flex', gap: 14, marginTop: 10 }}>
        {[['Women', 'var(--blue)'], ['Men', 'var(--purple)']].map(([l, c]) => (
          <span key={l} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-3)' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: c }} />{l}
          </span>
        ))}
      </div>
    </div>
  )
}

function ToggleSwitch({ checked, onChange, label, disabled = false }) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.6 : 1 }}>
      <span style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 600 }}>{label}</span>
      <button
        type="button"
        aria-pressed={checked}
        aria-label={label}
        onClick={() => { if (!disabled) onChange?.(!checked) }}
        style={{
          width: 36,
          height: 20,
          borderRadius: 999,
          border: '1px solid var(--border)',
          background: checked ? 'var(--indigo)' : 'var(--panel-2)',
          position: 'relative',
          padding: 0,
          transition: 'background 160ms ease',
          cursor: disabled ? 'not-allowed' : 'pointer',
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: 1,
            left: checked ? 17 : 1,
            width: 16,
            height: 16,
            borderRadius: '50%',
            background: '#fff',
            transition: 'left 160ms ease',
          }}
        />
      </button>
    </label>
  )
}

// ---------------------------------------------------------------------------
// Main analytics content
// ---------------------------------------------------------------------------
function AnalyticsContent({
  tab,
  kpis,
  charts,
  topWindowPosts,
  topWindowPostsLoading,
  allPosts,
  allPostsLoading,
  audienceDemographics,
  audienceDemographicsLoading,
  selectedAccount,
  engagementBreakdown,
  engagementBreakdownLoading,
  reachLoading,
  pageLabel,
  period,
  onPeriodChange,
  platform,
  overviewInsights,
}) {
  const reachMetric = kpis?.reach || null
  const viewsMetric = kpis?.views || null
  const engagementMetric = kpis?.engagement || null
  const engagedAccountsMetric = kpis?.engaged_accounts || null
  const followsAndUnfollowsMetric = kpis?.follows_and_unfollows || null
  const profileLinksTapsMetric = kpis?.profile_links_taps || null
  const engagementRateMetric = kpis?.engagement_rate || null

  const overviewFirstRow = useMemo(() => {
    const followersRaw = platform === 'ig'
      ? Number(selectedAccount?.followers_count ?? kpis?.followers?.total_count)
      : Number(selectedAccount?.followers_count ?? selectedAccount?.fan_count ?? kpis?.followers?.total_count)

    const followingRaw = platform === 'ig'
      ? Number(selectedAccount?.follows_count)
      : Number.NaN

    const postsRaw = platform === 'ig'
      ? Number(selectedAccount?.media_count)
      : Number.NaN

    const formatOrNull = (n) => (Number.isFinite(n) ? new Intl.NumberFormat().format(Math.max(0, Math.round(n))) : null)

    return [
      { key: 'followers', label: 'Followers', value: formatOrNull(followersRaw), unavailable: !Number.isFinite(followersRaw) },
      { key: 'following', label: 'Following', value: formatOrNull(followingRaw), unavailable: !Number.isFinite(followingRaw) },
      { key: 'posts', label: 'Posts', value: formatOrNull(postsRaw), unavailable: !Number.isFinite(postsRaw) },
    ]
  }, [platform, selectedAccount, kpis])

  const overviewSecondRow = useMemo(() => {
    // Use insights API total_value metrics for 30-day rolling window
    const reachData = overviewInsights?.reach
    const viewsData = overviewInsights?.views
    const engagementData = overviewInsights?.engagement
    const engagementRateData = overviewInsights?.engagement_rate
    const engagedAccountsData = kpis?.engaged_accounts

    const hasValue = (data) => data?.value !== null && data?.value !== undefined

    const formatValue = (data, isRate = false) => {
      if (!hasValue(data)) return null
      const val = Number(data.value)
      if (!Number.isFinite(val)) return null
      if (isRate) return `${val.toFixed(2)}%`
      return new Intl.NumberFormat().format(Math.round(val))
    }

    return [
      { key: 'reach', label: 'Reach (30d)', value: formatValue(reachData), unavailable: !hasValue(reachData) },
      { key: 'views', label: 'Views (30d)', value: formatValue(viewsData), unavailable: !hasValue(viewsData) || platform !== 'ig' },
      { key: 'engagement', label: 'Engagement (30d)', value: formatValue(engagementData), unavailable: !hasValue(engagementData) },
      {
        key: 'engaged_accounts',
        label: 'Engaged Accounts (30d)',
        value: engagedAccountsData?.value ?? null,
        unavailable: (engagedAccountsData?.value === null || engagedAccountsData?.value === undefined) || platform !== 'ig',
      },
      { key: 'engagement_rate', label: 'Eng. Rate (30d)', value: formatValue(engagementRateData, true), unavailable: !hasValue(engagementRateData) },
    ]
  }, [overviewInsights, kpis, platform])

  const performanceSeries = charts?.performance_overview?.every(s => Array.isArray(s?.points) && s.points.length)
    ? charts.performance_overview
    : [
      { name: 'Reach', color: '#4A8CFF', points: Array.isArray(reachMetric?.spark) ? reachMetric.spark : [] },
    ]

  const performanceXAxisLabels = useMemo(() => {
    const tickCount = 7
    const sinceRaw = charts?.reach_since
    const untilRaw = charts?.reach_until
    if (!sinceRaw || !untilRaw) {
      return Array.from({ length: tickCount }, () => '')
    }

    const sinceDate = new Date(`${sinceRaw}T00:00:00`)
    const untilDate = new Date(`${untilRaw}T00:00:00`)
    if (Number.isNaN(sinceDate.getTime()) || Number.isNaN(untilDate.getTime()) || sinceDate > untilDate) {
      return Array.from({ length: tickCount }, () => '')
    }

    const totalMs = untilDate.getTime() - sinceDate.getTime()
    const formatter = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })
    return Array.from({ length: tickCount }, (_, index) => {
      const ratio = index / (tickCount - 1)
      const valueMs = sinceDate.getTime() + Math.round(totalMs * ratio)
      return formatter.format(new Date(valueMs))
    })
  }, [charts?.reach_since, charts?.reach_until])

  const performancePointLabels = useMemo(() => {
    const sinceRaw = charts?.reach_since
    const untilRaw = charts?.reach_until
    const pointCount = performanceSeries?.[0]?.points?.length || 0
    if (!sinceRaw || !untilRaw || pointCount <= 0) {
      return []
    }

    const sinceDate = new Date(`${sinceRaw}T00:00:00`)
    const untilDate = new Date(`${untilRaw}T00:00:00`)
    if (Number.isNaN(sinceDate.getTime()) || Number.isNaN(untilDate.getTime()) || sinceDate > untilDate) {
      return []
    }

    const totalMs = untilDate.getTime() - sinceDate.getTime()
    const formatter = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })
    return Array.from({ length: pointCount }, (_, index) => {
      const ratio = pointCount === 1 ? 0 : index / (pointCount - 1)
      const valueMs = sinceDate.getTime() + Math.round(totalMs * ratio)
      return formatter.format(new Date(valueMs))
    })
  }, [charts?.reach_since, charts?.reach_until, performanceSeries])

  const analyticsTopPosts = useMemo(() => {
    if (!Array.isArray(topWindowPosts)) return []
    return topWindowPosts.slice(0, 5)
  }, [topWindowPosts])

  const breakdownOrder = useMemo(() => [
    { key: 'likes', label: 'Likes', color: '#4A8CFF' },
    { key: 'comments', label: 'Comments', color: '#2EC27E' },
    { key: 'saves', label: 'Saves', color: '#9B7BFF' },
    { key: 'shares', label: 'Shares', color: '#FF8A4C' },
    { key: 'reposts', label: 'Reposts', color: '#0EA5A6' },
    { key: 'replies', label: 'Replies', color: '#E163C9' },
    { key: 'other', label: 'Other', color: '#6B7280' },
  ], [])

  const engagementBreakdownData = useMemo(() => {
    const raw = engagementBreakdown?.breakdown || {}
    const total = Number(engagementBreakdown?.total_interactions || 0)
    const rows = breakdownOrder.map(item => {
      const value = Number(raw[item.key] || 0)
      const percent = total > 0 ? (value / total) * 100 : 0
      return {
        ...item,
        value,
        percent,
      }
    })
    return {
      total,
      rows,
      subtitle: _formatDateRangeShort(engagementBreakdown?.since, engagementBreakdown?.until),
    }
  }, [engagementBreakdown, breakdownOrder])

  const engagementMetricDetailRows = useMemo(() => {
    const current = engagementBreakdown?.breakdown || {}
    const previous = engagementBreakdown?.previous_breakdown || {}
    const keys = [
      { key: 'likes', label: 'Likes' },
      { key: 'comments', label: 'Comments' },
      { key: 'shares', label: 'Shares' },
      { key: 'reposts', label: 'Reposts' },
      { key: 'replies', label: 'Replies' },
    ]
    return keys.map(item => {
      const curVal = Number(current[item.key] || 0)
      const prevVal = Number(previous[item.key] || 0)
      const diff = curVal - prevVal
      const diffPct = prevVal > 0 ? (diff / prevVal) * 100 : (curVal > 0 ? 100 : 0)
      return {
        ...item,
        current: curVal,
        previous: prevVal,
        diff,
        diffPct,
      }
    })
  }, [engagementBreakdown])

  const currentWindowLabel = useMemo(
    () => _formatDateRangeShort(engagementBreakdown?.since, engagementBreakdown?.until),
    [engagementBreakdown?.since, engagementBreakdown?.until]
  )

  const previousWindowLabel = useMemo(() => {
    const sinceIso = engagementBreakdown?.since
    const untilIso = engagementBreakdown?.until
    const windowDays = Number(engagementBreakdown?.window_days || _inclusiveDaysBetween(sinceIso, untilIso) || 30)
    const prevSince = _shiftIsoDate(sinceIso, -windowDays)
    const prevUntil = _shiftIsoDate(untilIso, -windowDays)
    return _formatDateRangeShort(prevSince, prevUntil)
  }, [engagementBreakdown?.since, engagementBreakdown?.until, engagementBreakdown?.window_days])

  const postBreakdownData = useMemo(() => {
    const postTypeOrder = [
      { key: 'reel', label: 'Reels', color: '#4A8CFF' },
      { key: 'video', label: 'Videos', color: '#2EC27E' },
      { key: 'carousel', label: 'Carousels', color: '#9B7BFF' },
      { key: 'image', label: 'Images', color: '#FF8A4C' },
      { key: 'other', label: 'Other', color: '#6B7280' },
    ]

    const counts = {
      reel: 0,
      video: 0,
      carousel: 0,
      image: 0,
      other: 0,
    }

    allPosts.forEach(post => {
      const raw = `${post?.type || ''}`.toLowerCase()
      if (raw.includes('reel')) {
        counts.reel += 1
      } else if (raw.includes('video')) {
        counts.video += 1
      } else if (raw.includes('carousel')) {
        counts.carousel += 1
      } else if (raw.includes('image') || raw.includes('photo')) {
        counts.image += 1
      } else {
        counts.other += 1
      }
    })

    const total = Object.values(counts).reduce((sum, value) => sum + value, 0)
    const rows = postTypeOrder
      .map(item => {
        const value = counts[item.key]
        const percent = total > 0 ? (value / total) * 100 : 0
        return {
          ...item,
          value,
          percent,
        }
      })
      .filter(item => item.value > 0)

    return {
      total,
      rows,
    }
  }, [allPosts])

  // ---------------------------------------------------------------------------
  // Audience demographics computed data
  // ---------------------------------------------------------------------------
  const _DEMO_AGE_COLORS = ['#4A8CFF', '#2EC27E', '#9B7BFF', '#FF8A4C', '#E163C9']
  const _DEMO_COUNTRY_COLORS = ['#4A8CFF', '#2EC27E', '#9B7BFF', '#FF8A4C', '#0EA5A6', '#E163C9', '#F59E0B', '#EF4444', '#14B8A6', '#6B7280']
  const _DEMO_GENDER_COLORS = { Female: '#E163C9', Male: '#4A8CFF', Unknown: '#6B7280' }

  const ageDonutData = useMemo(() => {
    const raw = audienceDemographics?.age || {}
    const order = ['13-24', '25-34', '35-44', '45-54', '55+']
    const total = Object.values(raw).reduce((s, v) => s + Number(v || 0), 0)
    const rows = order.map((label, idx) => {
      const value = Number(raw[label] || 0)
      return { label, value, color: _DEMO_AGE_COLORS[idx % _DEMO_AGE_COLORS.length], percent: total > 0 ? (value / total) * 100 : 0 }
    }).filter(r => r.value > 0)
    return { total, rows }
  }, [audienceDemographics])

  const countryDonutData = useMemo(() => {
    const raw = audienceDemographics?.country || {}
    const sorted = Object.entries(raw).sort((a, b) => b[1] - a[1])
    const total = sorted.reduce((s, [, v]) => s + Number(v || 0), 0)
    const rows = sorted.map(([label, value], idx) => ({
      label,
      value: Number(value),
      color: _DEMO_COUNTRY_COLORS[idx % _DEMO_COUNTRY_COLORS.length],
      percent: total > 0 ? (Number(value) / total) * 100 : 0,
    }))
    return { total, rows }
  }, [audienceDemographics])

  const genderDonutData = useMemo(() => {
    const raw = audienceDemographics?.gender || {}
    const order = ['Female', 'Male', 'Unknown']
    const total = Object.values(raw).reduce((s, v) => s + Number(v || 0), 0)
    const rows = order.map(label => {
      const value = Number(raw[label] || 0)
      return { label, value, color: _DEMO_GENDER_COLORS[label] || '#6B7280', percent: total > 0 ? (value / total) * 100 : 0 }
    }).filter(r => r.value > 0)
    return { total, rows }
  }, [audienceDemographics])

  const ageGenderData = useMemo(() => {
    const raw = audienceDemographics?.age_gender || {}
    const order = ['13-24', '25-34', '35-44', '45-54', '55+']
    return order.map(label => ({
      label,
      female: Number((raw[label] || {}).Female || 0),
      male: Number((raw[label] || {}).Male || 0),
    }))
  }, [audienceDemographics])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Overview tab: total-value basics */}
      {tab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 14 }}>
            {overviewFirstRow.map(metric => (
              <SnapshotMetricCard
                key={metric.key}
                label={metric.label}
                value={metric.value}
                unavailable={metric.unavailable}
              />
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 14 }}>
            {overviewSecondRow.map(metric => (
              <SnapshotMetricCard
                key={metric.key}
                label={metric.label}
                value={metric.value}
                unavailable={metric.unavailable}
              />
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 14 }}>
            <Section title="Performance Overview" subtitle="Daily reach for last 30 days" style={{ padding: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                {/* <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-2)' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#4A8CFF' }} />Reach
                </span> */}
              </div>
              <div style={{ width: '100%', overflowX: 'auto' }}>
                <MultiLine
                  width={400}
                  height={150}
                  series={performanceSeries}
                  xTickLabels={performanceXAxisLabels}
                  pointLabels={performancePointLabels}
                />
              </div>
            </Section>

            <Section title="Posts Breakdown" subtitle="lifetime" style={{ padding: 16 }}>
              {allPostsLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading posts breakdown...</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '170px minmax(0, 1fr)', gap: 14, alignItems: 'center' }}>
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <DonutMulti
                      size={148}
                      strokeWidth={20}
                      centerLabel={String(postBreakdownData.total)}
                      centerSub="Posts"
                      segments={postBreakdownData.rows.map(row => ({ value: row.value, color: row.color }))}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                    {postBreakdownData.rows.length === 0 ? (
                      <div style={{ fontSize: 12, color: 'var(--text-3)' }}>No posts available for breakdown.</div>
                    ) : postBreakdownData.rows.map(row => (
                      <div key={row.key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
                          <span style={{ width: 8, height: 8, borderRadius: '50%', background: row.color, flex: '0 0 8px' }} />
                          <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{row.label}</span>
                        </div>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>
                          {_formatCompact(row.value)} ({row.percent.toFixed(0)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Section>

            <Section title="Engagement Breakdown" subtitle="last 30 days" style={{ padding: 16 }}>
              {engagementBreakdownLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading engagement breakdown...</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '170px minmax(0, 1fr)', gap: 14, alignItems: 'center' }}>
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <DonutMulti
                      size={148}
                      strokeWidth={20}
                      centerLabel={_formatCompact(engagementBreakdownData.total)}
                      centerSub="Interactions"
                      segments={engagementBreakdownData.rows.filter(row => row.value > 0).map(row => ({ value: row.value, color: row.color }))}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                    {engagementBreakdownData.rows.map(row => (
                      <div key={row.key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
                          <span style={{ width: 8, height: 8, borderRadius: '50%', background: row.color, flex: '0 0 8px' }} />
                          <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{row.label}</span>
                        </div>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>
                          {_formatCompact(row.value)} ({row.percent.toFixed(0)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Section>
          </div>

          {/* Audience demographics row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 14 }}>

            {/* Age Distribution donut */}
            <Section title="Age Distribution" subtitle="this month " style={{ padding: 16 }}>
              {audienceDemographicsLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading…</div>
              ) : ageDonutData.rows.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>No data available.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                  <DonutMulti
                    size={130}
                    strokeWidth={18}
                    centerLabel={_formatCompact(ageDonutData.total)}
                    centerSub="People"
                    segments={ageDonutData.rows.map(r => ({ value: r.value, color: r.color }))}
                  />
                  <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 7 }}>
                    {ageDonutData.rows.map(row => (
                      <div key={row.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: row.color, flex: '0 0 8px' }} />
                        <span style={{ fontSize: 12, color: 'var(--text-2)', flex: 1 }}>{row.label}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{_formatCompact(row.value)}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-2)', minWidth: 36, textAlign: 'right' }}>{row.percent.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Section>

            {/* Top Countries donut */}
            <Section title="Top Countries" subtitle="this month " style={{ padding: 16 }}>
              {audienceDemographicsLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading…</div>
              ) : countryDonutData.rows.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>No data available.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                  <DonutMulti
                    size={130}
                    strokeWidth={18}
                    centerLabel={_formatCompact(countryDonutData.total)}
                    centerSub="People"
                    segments={countryDonutData.rows.map(r => ({ value: r.value, color: r.color }))}
                  />
                  <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 7 }}>
                    {countryDonutData.rows.map(row => (
                      <div key={row.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: row.color, flex: '0 0 8px' }} />
                        <span style={{ fontSize: 12, color: 'var(--text-2)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.label}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{_formatCompact(row.value)}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-2)', minWidth: 36, textAlign: 'right' }}>{row.percent.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Section>

            {/* Gender Split donut */}
            <Section title="Gender Split" subtitle="this month " style={{ padding: 16 }}>
              {audienceDemographicsLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading…</div>
              ) : genderDonutData.rows.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>No data available.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                  <DonutMulti
                    size={130}
                    strokeWidth={18}
                    centerLabel={_formatCompact(genderDonutData.total)}
                    centerSub="People"
                    segments={genderDonutData.rows.map(r => ({ value: r.value, color: r.color }))}
                  />
                  <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 7 }}>
                    {genderDonutData.rows.map(row => (
                      <div key={row.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: row.color, flex: '0 0 8px' }} />
                        <span style={{ fontSize: 12, color: 'var(--text-2)', flex: 1 }}>{row.label}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>{_formatCompact(row.value)}</span>
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-2)', minWidth: 36, textAlign: 'right' }}>{row.percent.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Section>

            {/* Gender by Age group — custom dual-bar chart */}
            <Section title="Gender by Age Group" subtitle="this month " style={{ padding: 16 }}>
              {audienceDemographicsLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading…</div>
              ) : ageGenderData.every(g => g.female === 0 && g.male === 0) ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>No data available.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {(() => {
                    const maxVal = Math.max(...ageGenderData.flatMap(g => [g.female, g.male]), 1)
                    const barMaxH = 100
                    const slotW = 100 / ageGenderData.length
                    return (
                      <div>
                        <div style={{ display: 'flex', alignItems: 'flex-end', height: barMaxH + 24, gap: 0 }}>
                          {ageGenderData.map(g => {
                            const fH = Math.max(g.female > 0 ? 3 : 0, (g.female / maxVal) * barMaxH)
                            const mH = Math.max(g.male > 0 ? 3 : 0, (g.male / maxVal) * barMaxH)
                            return (
                              <div key={g.label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: barMaxH }}>
                                  <div title={`Female: ${_formatCompact(g.female)}`} style={{ width: 10, height: fH, background: '#E163C9', borderRadius: '3px 3px 0 0', transition: 'height 0.3s' }} />
                                  <div title={`Male: ${_formatCompact(g.male)}`} style={{ width: 10, height: mH, background: '#4A8CFF', borderRadius: '3px 3px 0 0', transition: 'height 0.3s' }} />
                                </div>
                                <span className="mono" style={{ fontSize: 9, color: 'var(--text-3)', marginTop: 5, textAlign: 'center', lineHeight: 1.2 }}>{g.label}</span>
                              </div>
                            )
                          })}
                        </div>
                        <div style={{ display: 'flex', gap: 14, marginTop: 4 }}>
                          {[['Female', '#E163C9'], ['Male', '#4A8CFF']].map(([lbl, col]) => (
                            <span key={lbl} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-3)' }}>
                              <span style={{ width: 8, height: 8, borderRadius: '50%', background: col }} />{lbl}
                            </span>
                          ))}
                        </div>
                      </div>
                    )
                  })()}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                    {ageGenderData.filter(g => g.female > 0 || g.male > 0).map(g => {
                      const total = g.female + g.male
                      const fPct = total > 0 ? ((g.female / total) * 100).toFixed(0) : '0'
                      const mPct = total > 0 ? ((g.male / total) * 100).toFixed(0) : '0'
                      return (
                        <div key={g.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)', minWidth: 32 }}>{g.label}</span>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, color: '#E163C9' }}>
                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#E163C9' }} />
                            {fPct}%
                          </span>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, color: '#4A8CFF' }}>
                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4A8CFF' }} />
                            {mPct}%
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </Section>

          </div>
        </div>
      )}

      {/* Analytics tab: time-window analysis */}
      {tab === 'analytics' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: platform === 'ig' ? 'repeat(7, 1fr)' : 'repeat(6, 1fr)', gap: 14 }}>
            <ReachCard metric={reachMetric} loading={reachLoading} />
            {platform === 'ig' && (
              <KPICard
                label="Views"
                value={viewsMetric?.value || '0'}
                delta={viewsMetric?.delta || '0.0%'}
                color="#FF8A4C"
                comparisonLabel={viewsMetric?.comparison_label || 'vs previous period'}
                description={viewsMetric?.description || 'Views for the selected window.'}
                changeValue={viewsMetric?.change_value || '0'}
                trend={viewsMetric?.trend || 'flat'}
                spark={viewsMetric?.spark?.length ? viewsMetric.spark : [0, 0, 0, 0, 0, 0, 0]}
              />
            )}
            <KPICard label="Eng." value={engagementMetric?.value || '0'} delta={engagementMetric?.delta || '21.4%'} color="#2EC27E" comparisonLabel={engagementMetric?.comparison_label || 'vs previous period'} description={engagementMetric?.description || 'Engagement for the selected window.'} changeValue={engagementMetric?.change_value || '0'} trend={engagementMetric?.trend || 'flat'} spark={engagementMetric?.spark?.length ? engagementMetric.spark : [50,52,48,56,62,58,68,72,68,78,82,76,88,98]} />
            {platform === 'ig' && (
              <KPICard label="Engaged Accounts" value={engagedAccountsMetric?.value || '0'} delta={engagedAccountsMetric?.delta || '0.0%'} color="#0EA5A6" comparisonLabel={engagedAccountsMetric?.comparison_label || 'vs previous period'} description={engagedAccountsMetric?.description || 'Unique accounts engaged for the selected window.'} changeValue={engagedAccountsMetric?.change_value || '0'} trend={engagedAccountsMetric?.trend || 'flat'} spark={engagedAccountsMetric?.spark?.length ? engagedAccountsMetric.spark : [0, 0, 0, 0, 0, 0, 0]} />
            )}
            <KPICard label="Eng. Rate" value={engagementRateMetric?.value || '12.24%'} delta={engagementRateMetric?.delta || '8.7%'} color="#FF8A4C" comparisonLabel={engagementRateMetric?.comparison_label || 'vs previous period'} description={engagementRateMetric?.description || 'Engagement Rate = total interactions / reach for the selected window, compared with the previous window.'} changeValue={engagementRateMetric?.change_value || '0'} trend={engagementRateMetric?.trend || 'flat'} spark={engagementRateMetric?.spark?.length ? engagementRateMetric.spark : [70,72,74,76,78,80,82,84,82,86,88,90,92,96]} />
            {platform === 'ig' && (
              <KPICard label="Follows & Unfollows" value={followsAndUnfollowsMetric?.value || '0'} delta={followsAndUnfollowsMetric?.delta || '0.0%'} color="#4A8CFF" comparisonLabel={followsAndUnfollowsMetric?.comparison_label || 'vs previous period'} description={followsAndUnfollowsMetric?.description || 'Follows and unfollows for the selected window.'} changeValue={followsAndUnfollowsMetric?.change_value || '0'} trend={followsAndUnfollowsMetric?.trend || 'flat'} spark={followsAndUnfollowsMetric?.spark?.length ? followsAndUnfollowsMetric.spark : [0, 0, 0, 0, 0, 0, 0]} />
            )}
            {platform === 'ig' && (
              <KPICard label="Profile Link Taps" value={profileLinksTapsMetric?.value || '0'} delta={profileLinksTapsMetric?.delta || '0.0%'} color="#E163C9" comparisonLabel={profileLinksTapsMetric?.comparison_label || 'vs previous period'} description={profileLinksTapsMetric?.description || 'Profile link taps for the selected window.'} changeValue={profileLinksTapsMetric?.change_value || '0'} trend={profileLinksTapsMetric?.trend || 'flat'} spark={profileLinksTapsMetric?.spark?.length ? profileLinksTapsMetric.spark : [0, 0, 0, 0, 0, 0, 0]} />
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '420px minmax(0, 1fr)', gap: 14 }}>
            <Section title="Engagement Breakdown" subtitle={engagementBreakdownData.subtitle}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <DonutMulti
                  size={160}
                  strokeWidth={22}
                  centerLabel={_formatCompact(engagementBreakdownData.total)}
                  centerSub="Total"
                  segments={engagementBreakdownData.rows.filter(row => row.value > 0).map(row => ({ value: row.value, color: row.color }))}
                />
                <div style={{ width: '100%' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10 }}>
                    {engagementBreakdownData.rows.map((row) => (
                      <div key={row.key} style={{ display: 'flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: row.color, flex: '0 0 8px' }} />
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {row.label} {_formatCompact(row.value)} ({row.percent.toFixed(0)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Section>

            <Section title="Top Performance Posts" subtitle={currentWindowLabel === '—' ? 'time-window' : currentWindowLabel}>
              {topWindowPostsLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading top posts...</div>
              ) : (
                <div className="scroll-y" style={{ maxHeight: 260 }}>
                  <table className="dense compact" style={{ width: '100%', tableLayout: 'fixed' }}>
                    <colgroup>
                      <col style={{ width: '44%' }} />
                      <col style={{ width: '14%' }} />
                      <col style={{ width: '14%' }} />
                      <col style={{ width: '14%' }} />
                      <col style={{ width: '14%' }} />
                    </colgroup>
                    <thead>
                      <tr>
                        <th>Post</th>
                        <th>Type</th>
                        <th>Reach</th>
                        <th>Eng.</th>
                        <th>Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analyticsTopPosts.length === 0 && (
                        <tr>
                          <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-3)' }}>No posts found for selected window.</td>
                        </tr>
                      )}
                      {analyticsTopPosts.map((r, idx) => {
                        const rateNumber = Number(r?.engagement_rate)
                        const hasRate = Number.isFinite(rateNumber)
                        return (
                          <tr key={r?.id || `${r?.created_at || 'post'}-${idx}`}>
                            <td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                                {r?.thumbnail_url
                                  ? <img src={r.thumbnail_url} alt="" style={{ width: 30, height: 30, borderRadius: 6, objectFit: 'cover', flex: '0 0 30px' }} />
                                  : <div style={{ width: 30, height: 30, borderRadius: 6, background: 'var(--indigo-soft)', opacity: 0.9, flex: '0 0 30px' }} />
                                }
                                <div style={{ minWidth: 0 }}>
                                  <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{_truncatePostCaption(r?.title, 36)}</div>
                                  <div style={{ fontSize: 10, color: 'var(--text-3)' }}>{_formatPostTimestamp(r?.created_at)}</div>
                                </div>
                              </div>
                            </td>
                            <td style={{ color: 'var(--text-3)', fontSize: 11 }}>{r?.type || 'Post'}</td>
                            <td className="mono">{r?.reach_label || _formatCompact(Number(r?.reach || 0))}</td>
                            <td className="mono">{r?.engagement_label || _formatCompact(Number(r?.engagement_total || 0))}</td>
                            <td className="mono" style={{ fontWeight: 600, color: hasRate ? 'var(--teal)' : 'var(--text-3)' }}>{hasRate ? `${rateNumber.toFixed(1)}%` : '—'}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </Section>
          </div>

          <Section title="Engagement Metric Details" subtitle={`Current Window: ${currentWindowLabel} vs Previous Window: ${previousWindowLabel}`}>
            <div className="scroll-y" style={{ maxHeight: 300 }}>
              <table className="dense compact" style={{ width: '100%', tableLayout: 'fixed' }}>
                <colgroup>
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '20%' }} />
                  <col style={{ width: '20%' }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Current ({currentWindowLabel})</th>
                    <th>Previous ({previousWindowLabel})</th>
                    <th>Change</th>
                    <th>Change %</th>
                  </tr>
                </thead>
                <tbody>
                  {engagementMetricDetailRows.map(row => {
                    const up = row.diff > 0
                    const down = row.diff < 0
                    const trendColor = up ? 'var(--teal)' : down ? 'var(--coral)' : 'var(--text-3)'
                    const sign = up ? '+' : ''
                    const diffDisplay = row.diff === 0
                      ? '0'
                      : `${row.diff > 0 ? '+' : '-'}${_formatCompact(Math.abs(row.diff))}`
                    return (
                      <tr key={row.key}>
                        <td style={{ fontWeight: 600 }}>{row.label}</td>
                        <td className="mono">{_formatCompact(row.current)}</td>
                        <td className="mono">{_formatCompact(row.previous)}</td>
                        <td className="mono" style={{ color: trendColor }}>{diffDisplay}</td>
                        <td className="mono" style={{ color: trendColor }}>{`${sign}${row.diffPct.toFixed(1)}%`}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Section>

          <Section title="Key Insights" subtitle="High-level performance snapshot">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              {[
                { icon: 'Analytics', bg: 'var(--green-soft)',  color: 'var(--green)',  title: 'Reach is up 18.6%',          body: 'You reached 128.4K more people compared to the previous period.' },
                { icon: 'Star',      bg: 'var(--purple-soft)', color: 'var(--purple)', title: 'Engagement Rate improved',    body: 'Your engagement rate increased by 8.7% compared to last period.' },
                { icon: 'Eye',       bg: 'var(--blue-soft)',   color: 'var(--blue)',   title: 'Video performance is great',  body: 'Video views increased by 30.8% and driving more engagement.' },
                { icon: 'Clock',     bg: 'var(--orange-soft)', color: 'var(--orange)', title: 'Best posting time',           body: 'Posts between 6PM — 9PM get the highest engagement.' },
              ].map((k, i) => {
                const Icon = Icons[k.icon]
                return (
                  <div key={i} className="panel-2" style={{ padding: 14, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 8, background: k.bg, color: k.color, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 36px' }}>
                      <Icon size={17} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{k.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 4, lineHeight: 1.45 }}>{k.body}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </Section>
        </>
      )}

      {/* Posts tab: post-level insights */}
      {tab === 'posts' && (
        <div className="panel" style={{ padding: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '22px 22px 0', marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <div style={{ fontSize: 15, fontWeight: 600 }}>All Posts (Lifetime)</div>
          </div>
          <div className="scroll-y" style={{ maxHeight: 520 }}>
            <table className="dense compact" style={{ width: '100%', tableLayout: 'fixed' }}>
              <colgroup>
                <col style={{ width: '26%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '9%' }} />
                <col style={{ width: '9%' }} />
              </colgroup>
              <thead>
                <tr>
                  <th>Post</th>
                  <th>Type</th>
                  <th>Views</th>
                  <th>Likes</th>
                  <th>Comments</th>
                  <th>Shares</th>
                  <th>Reposts</th>
                  <th>Saves</th>
                  <th>Engagement</th>
                  <th>Engagement Rate</th>
                </tr>
              </thead>
              <tbody>
                {!allPostsLoading && allPosts.length === 0 && (
                  <tr>
                    <td colSpan={10} style={{ textAlign: 'center', color: 'var(--text-3)' }}>No posts found.</td>
                  </tr>
                )}
                {allPosts.map((r, idx) => {
                  const engagementTotal = Number(r?.engagement_total || 0)
                  const viewsTotal = Number(r?.view_count ?? r?.reach ?? 0)
                  const likesTotal = Number(r?.like_count || 0)
                  const commentsTotal = Number(r?.comments_count || 0)
                  const sharesTotal = Number(r?.shares_count || 0)
                  const repostsTotal = Number(r?.reposts_count || 0)
                  const savesTotal = Number(r?.saved_count || 0)
                  const rateNumber = Number(r?.engagement_rate)
                  const hasRate = Number.isFinite(rateNumber)
                  return (
                    <tr key={r?.id || `${r?.created_at || 'post'}-${idx}`}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                          {r?.thumbnail_url
                            ? <img src={r.thumbnail_url} alt="" style={{ width: 34, height: 34, borderRadius: 6, objectFit: 'cover', flex: '0 0 34px' }} />
                            : <div style={{ width: 34, height: 34, borderRadius: 6, background: 'var(--indigo-soft)', opacity: 0.9, flex: '0 0 34px' }} />
                          }
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 240 }}>{_truncatePostCaption(r?.title, 40)}</div>
                            <div style={{ fontSize: 10, color: 'var(--text-3)' }}>{_formatPostTimestamp(r?.created_at)}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-3)', fontSize: 11 }}>{r?.type || 'Post'}</td>
                      <td className="mono">{_formatCompact(viewsTotal)}</td>
                      <td className="mono">{_formatCompact(likesTotal)}</td>
                      <td className="mono">{_formatCompact(commentsTotal)}</td>
                      <td className="mono">{_formatCompact(sharesTotal)}</td>
                      <td className="mono">{_formatCompact(repostsTotal)}</td>
                      <td className="mono">{_formatCompact(savesTotal)}</td>
                      <td>
                        <div className="mono" style={{ fontSize: 11 }}>{r?.engagement_label || _formatCompact(engagementTotal)}</div>
                      </td>
                      <td className="mono" style={{ fontWeight: 600, color: hasRate ? 'var(--teal)' : 'var(--text-3)' }}>{hasRate ? `${rateNumber.toFixed(1)}%` : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// FacebookAnalytics — exported page component
// ---------------------------------------------------------------------------
export function FacebookAnalytics({ initialPlatform = 'fb', lockPlatform = false }) {
  const [tab, setTab] = useState(() => {
    const saved = _readSocialUiState().tab
    return TABS.some(t => t.id === saved) ? saved : 'overview'
  })
  const [platform, setPlatform] = useState(() => {
    const saved = _readSocialUiState().platform
    return PLATFORMS.some(p => p.id === saved) ? saved : initialPlatform
  })
  const current = PLATFORMS.find(p => p.id === platform) || PLATFORMS[0]

  // Facebook pages fetched from the API
  const [fbPages, setFbPages] = useState([])            // [{ id, name, picture_url }]
  const [igAccounts, setIgAccounts] = useState([])      // [{ id, name, picture_url }]
  const [selectedPage, setSelectedPage] = useState(null) // { id, name, picture_url } | null
  const [pagesLoading, setPagesLoading] = useState(false)
  const [overviewKpis, setOverviewKpis] = useState({})
  const [overviewCharts, setOverviewCharts] = useState({})
  const [overviewInsights, setOverviewInsights] = useState({})
  const [overviewInsightsLoading, setOverviewInsightsLoading] = useState(false)
  const [topWindowPosts, setTopWindowPosts] = useState([])
  const [topWindowPostsLoading, setTopWindowPostsLoading] = useState(false)
  const [allPosts, setAllPosts] = useState([])
  const [allPostsLoading, setAllPostsLoading] = useState(false)
  const [audienceDemographics, setAudienceDemographics] = useState(null)
  const [audienceDemographicsLoading, setAudienceDemographicsLoading] = useState(false)
  const [engagementBreakdown, setEngagementBreakdown] = useState(null)
  const [engagementBreakdownLoading, setEngagementBreakdownLoading] = useState(false)
  const [reachMetric, setReachMetric] = useState(null)
  const [reachLoading, setReachLoading] = useState(false)
  const [windowUnit, setWindowUnit] = useState(() => {
    const saved = _readSocialUiState().windowUnit
    return WINDOW_UNIT_OPTIONS.some(option => option.value === saved) ? saved : DEFAULT_WINDOW_UNIT
  })
  const [windowCount, setWindowCount] = useState(() => {
    const saved = _readSocialUiState()
    const savedUnit = WINDOW_UNIT_OPTIONS.some(option => option.value === saved.windowUnit)
      ? saved.windowUnit
      : DEFAULT_WINDOW_UNIT
    const savedCount = Number(saved.windowCount)
    return (WINDOW_COUNT_OPTIONS[savedUnit] || []).includes(savedCount)
      ? savedCount
      : DEFAULT_WINDOW_COUNT
  })
  const skipNextAccountFetchRef = useRef(null)

  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

  const { period, since, until } = useMemo(() => {
    const now = new Date()
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const start = new Date(end)

    if (windowUnit === 'month') {
      start.setMonth(start.getMonth() - windowCount)
      start.setDate(start.getDate() + 1)
    } else {
      start.setDate(start.getDate() - Math.max(windowCount - 1, 0))
    }

    return {
      period: windowUnit === 'month' ? 'month' : 'day',
      since: _toIsoDate(start),
      until: _toIsoDate(end),
    }
  }, [windowUnit, windowCount])

  const buildOverviewUrl = (extra = {}) => {
    const params = new URLSearchParams({
      platform,
      period,
      since,
      until,
      timezone,
      ...extra,
    })
    return `/api/social/overview?${params.toString()}`
  }

  const buildAllPostsUrl = () => {
    const params = new URLSearchParams({
      platform,
      account_id: selectedPage?.id || '',
    })
    return `/api/social/posts-metrics?${params.toString()}`
  }

  const buildTopPostsWindowUrl = () => {
    const params = new URLSearchParams({
      platform,
      account_id: selectedPage?.id || '',
      limit: '10',
      link_to_window: 'true',
      since,
      until,
    })
    return `/api/social/top-posts?${params.toString()}`
  }

  const buildAudienceDemographicsUrl = () => {
    const params = new URLSearchParams({
      platform,
      account_id: selectedPage?.id || '',
    })
    return `/api/social/audience-demographics?${params.toString()}`
  }

  const buildEngagementBreakdownUrl = () => {
    const params = new URLSearchParams({
      platform,
      account_id: selectedPage?.id || '',
      link_to_window: 'true',
      since,
      until,
    })
    return `/api/social/engagement-breakdown?${params.toString()}`
  }

  const buildInsightsUrl = (metric, metricType = 'total_value') => {
    const now = new Date()
    const endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const startDate = new Date(endDate)
    startDate.setDate(startDate.getDate() - 29) // 30 days inclusive (today - 29 days back)
    const params = new URLSearchParams({
      metric,
      period: 'day',
      metric_type: metricType,
      since: _toIsoDate(startDate),
      until: _toIsoDate(endDate),
      account_id: selectedPage?.id || '',
      platform,
    })
    return `/api/social/insights?${params.toString()}`
  }

  const buildInsightsBatchUrl = (metricType = 'total_value') => {
    const now = new Date()
    const endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const startDate = new Date(endDate)
    startDate.setDate(startDate.getDate() - 29) // 30 days inclusive (today - 29 days back)
    const params = new URLSearchParams({
      metrics: 'reach,views,engagement,engagement_rate',
      period: 'day',
      metric_type: metricType,
      since: _toIsoDate(startDate),
      until: _toIsoDate(endDate),
      account_id: selectedPage?.id || '',
      platform,
    })
    return `/api/social/insights?${params.toString()}`
  }

  useEffect(() => {
    _writeSocialUiState({
      tab,
      platform,
      windowUnit,
      windowCount,
    })
  }, [tab, platform, windowUnit, windowCount])

  useEffect(() => {
    if (!selectedPage?.id) return
    const saved = _readSocialUiState()
    const nextSelectedIds = {
      ...(saved.selectedAccountIds || {}),
      [platform]: selectedPage.id,
    }
    _writeSocialUiState({ selectedAccountIds: nextSelectedIds })
  }, [platform, selectedPage?.id])

  useEffect(() => {
    setReachMetric(null)
    setReachLoading(false)
    setOverviewKpis({})
    setOverviewCharts({})
    setOverviewInsights({})
    setOverviewInsightsLoading(false)
    setTopWindowPosts([])
    setTopWindowPostsLoading(false)
    setAllPosts([])
    setAllPostsLoading(false)
    setAudienceDemographics(null)
    setAudienceDemographicsLoading(false)
    setEngagementBreakdown(null)
    setEngagementBreakdownLoading(false)
    setSelectedPage(null)
    if (platform === 'tk') {
      setFbPages([])
      setIgAccounts([])
      setPagesLoading(false)
      return
    }

    setPagesLoading(true)
    setReachLoading(true)
    fetch(buildOverviewUrl({ refresh: 'true' }), { cache: 'no-store' })
      .then(r => r.json())
      .then(payload => {
        const items = payload?.summary?.accounts || []
        const saved = _readSocialUiState()
        const preferredId = saved?.selectedAccountIds?.[platform]
        const preferredAccount = items.find(item => item.id === preferredId)
        const nextSelected = preferredAccount || payload?.summary?.selected_account || items[0] || null
        if (platform === 'fb') {
          setFbPages(items)
        } else {
          setIgAccounts(items)
        }
        skipNextAccountFetchRef.current = nextSelected?.id || null
        setSelectedPage(nextSelected)
        setOverviewKpis(payload?.kpis || {})
        setOverviewCharts(payload?.charts || {})
        setReachMetric(payload?.kpis?.reach || null)
      })
      .catch(() => {
        setFbPages([])
        setIgAccounts([])
        setSelectedPage(null)
        setOverviewKpis({})
        setOverviewCharts({})
        setAllPosts([])
        setEngagementBreakdown(null)
        setAudienceDemographics(null)
        setReachMetric(null)
      })
      .finally(() => {
        setPagesLoading(false)
        setReachLoading(false)
      })
  }, [platform])

  useEffect(() => {
    if (platform === 'tk' || !selectedPage?.id) {
      return
    }

    // Skip the immediate follow-up fetch after initial platform bootstrap.
    if (skipNextAccountFetchRef.current === selectedPage.id) {
      skipNextAccountFetchRef.current = null
      return
    }

    let disposed = false
    const controller = new AbortController()
    setReachLoading(true)

    fetch(buildOverviewUrl({ account_id: selectedPage.id, refresh: 'true' }), { signal: controller.signal, cache: 'no-store' })
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}))
          throw new Error(body.detail || 'Failed to refresh overview')
        }
        return r.json()
      })
      .then(payload => {
        if (disposed) return
        setOverviewKpis(payload?.kpis || {})
        setOverviewCharts(payload?.charts || {})
        setReachMetric(payload?.kpis?.reach || null)
      })
      .catch(err => {
        if (err.name !== 'AbortError' && !disposed) {
          setOverviewKpis({})
          setOverviewCharts({})
          setReachMetric(null)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && !disposed) {
          setReachLoading(false)
        }
      })

    return () => {
      disposed = true
      controller.abort()
    }
  }, [platform, selectedPage?.id, period, since, until, timezone])

  useEffect(() => {
    if (platform === 'tk' || !selectedPage?.id) {
      setOverviewInsights({})
      setOverviewInsightsLoading(false)
      return
    }

    let disposed = false
    const controller = new AbortController()
    setOverviewInsightsLoading(true)
    fetch(buildInsightsBatchUrl(), { signal: controller.signal, cache: 'no-store' })
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}))
          throw new Error(body.detail || 'Failed to load insights')
        }
        return r.json()
      })
      .then(payload => {
        if (disposed) return
        if (payload?.metrics && typeof payload.metrics === 'object') {
          setOverviewInsights(payload.metrics)
          return
        }
        if (payload?.metric) {
          setOverviewInsights({ [payload.metric]: payload })
          return
        }
        setOverviewInsights({})
      })
      .catch(err => {
        if (err.name !== 'AbortError' && !disposed) {
          setOverviewInsights({})
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && !disposed) {
          setOverviewInsightsLoading(false)
        }
      })

    return () => {
      disposed = true
      controller.abort()
    }
  }, [platform, selectedPage?.id])

  useEffect(() => {
    if (platform !== 'ig' || !selectedPage?.id) {
      setTopWindowPosts([])
      setTopWindowPostsLoading(false)
      return
    }

    let disposed = false
    const controller = new AbortController()
    setTopWindowPostsLoading(true)

    fetch(buildTopPostsWindowUrl(), { signal: controller.signal, cache: 'no-store' })
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}))
          throw new Error(body.detail || 'Failed to load window top posts')
        }
        return r.json()
      })
      .then(payload => {
        if (!disposed) {
          setTopWindowPosts(Array.isArray(payload?.posts) ? payload.posts : [])
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError' && !disposed) {
          setTopWindowPosts([])
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && !disposed) {
          setTopWindowPostsLoading(false)
        }
      })

    return () => {
      disposed = true
      controller.abort()
    }
  }, [platform, selectedPage?.id, since, until])

  useEffect(() => {
    if (platform !== 'ig' || !selectedPage?.id) {
      setAllPosts([])
      setAllPostsLoading(false)
      return
    }

    let disposed = false
    const controller = new AbortController()
    setAllPostsLoading(true)

    fetch(buildAllPostsUrl(), { signal: controller.signal, cache: 'no-store' })
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}))
          throw new Error(body.detail || 'Failed to load lifetime posts')
        }
        return r.json()
      })
      .then(payload => {
        if (!disposed) {
          setAllPosts(Array.isArray(payload?.posts) ? payload.posts : [])
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError' && !disposed) {
          setAllPosts([])
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && !disposed) {
          setAllPostsLoading(false)
        }
      })

    return () => {
      disposed = true
      controller.abort()
    }
  }, [platform, selectedPage?.id])

  useEffect(() => {
    if (platform !== 'ig' || !selectedPage?.id) {
      setAudienceDemographics(null)
      setAudienceDemographicsLoading(false)
      return
    }

    let disposed = false
    const controller = new AbortController()
    setAudienceDemographicsLoading(true)

    fetch(buildAudienceDemographicsUrl(), { signal: controller.signal, cache: 'no-store' })
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}))
          throw new Error(body.detail || 'Failed to load audience demographics')
        }
        return r.json()
      })
      .then(payload => {
        if (!disposed) {
          setAudienceDemographics(payload || null)
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError' && !disposed) {
          setAudienceDemographics(null)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && !disposed) {
          setAudienceDemographicsLoading(false)
        }
      })

    return () => {
      disposed = true
      controller.abort()
    }
  }, [platform, selectedPage?.id])

  useEffect(() => {
    if (platform !== 'ig' || !selectedPage?.id) {
      setEngagementBreakdown(null)
      setEngagementBreakdownLoading(false)
      return
    }

    let disposed = false
    const controller = new AbortController()
    setEngagementBreakdownLoading(true)

    fetch(buildEngagementBreakdownUrl(), { signal: controller.signal, cache: 'no-store' })
      .then(async r => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}))
          throw new Error(body.detail || 'Failed to load engagement breakdown')
        }
        return r.json()
      })
      .then(payload => {
        if (!disposed) {
          const nextWindowDays = _inclusiveDaysBetween(since, until)
          setEngagementBreakdown({
            ...payload,
            window_days: Number(payload?.window_days || nextWindowDays),
          })
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError' && !disposed) {
          setEngagementBreakdown({
            breakdown: {
              likes: 0,
              comments: 0,
              saves: 0,
              shares: 0,
              reposts: 0,
              replies: 0,
              other: 0,
            },
            total_interactions: 0,
            window_days: _inclusiveDaysBetween(since, until),
            since,
            until,
          })
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && !disposed) {
          setEngagementBreakdownLoading(false)
        }
      })

    return () => {
      disposed = true
      controller.abort()
    }
  }, [platform, selectedPage?.id, since, until])

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Controls row — platform selector + date range + export */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {!lockPlatform && <PlatformDropdown value={platform} onChange={setPlatform} />}
          {!lockPlatform && <div style={{ width: 1, height: 24, background: 'var(--border)' }} />}
          <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{current.pageLabel}:</span>
          <PageDropdown
            pages={platform === 'fb' ? fbPages : platform === 'ig' ? igAccounts : []}
            value={selectedPage}
            onChange={setSelectedPage}
            loading={pagesLoading}
            tone={current.tone}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            {pagesLoading ? (
              <>
                <span className="pulse-dot" style={{ color: 'var(--text-3)' }} />
                <span style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 600 }}>Loading…</span>
              </>
            ) : (platform === 'fb' ? fbPages.length : igAccounts.length) > 0 ? (
              <>
                <span className="pulse-dot" style={{ color: 'var(--teal)' }} />
                <span style={{ fontSize: 11, color: 'var(--teal)', fontWeight: 600 }}>Connected</span>
              </>
            ) : (
              <>
                <span className="pulse-dot" style={{ color: 'var(--coral)' }} />
                <span style={{ fontSize: 11, color: 'var(--coral)', fontWeight: 600 }}>Not Connected</span>
              </>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {tab === 'analytics' && (
            <TimeRangeWidget
              windowUnit={windowUnit}
              windowCount={windowCount}
              since={since}
              until={until}
              timezone={timezone}
              onApply={({ windowUnit: nextUnit, windowCount: nextCount }) => {
                setWindowUnit(nextUnit)
                setWindowCount(nextCount)
              }}
            />
          )}
          <button type="button" className="btn primary">
            <Icons.Download size={13} />
            Export
          </button>
        </div>
      </div>

      {/* Sub-nav tabs */}
      <div style={{ display: 'flex', gap: 2, background: 'var(--panel-2)', padding: 3, borderRadius: 8, width: 'fit-content', border: '1px solid var(--border)' }}>
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            className={`pill-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <AnalyticsContent
        tab={tab}
        kpis={overviewKpis}
        charts={overviewCharts}
        topWindowPosts={topWindowPosts}
        topWindowPostsLoading={topWindowPostsLoading}
        allPosts={allPosts}
        allPostsLoading={allPostsLoading}
        audienceDemographics={audienceDemographics}
        audienceDemographicsLoading={audienceDemographicsLoading}
        selectedAccount={selectedPage}
        engagementBreakdown={engagementBreakdown}
        engagementBreakdownLoading={engagementBreakdownLoading}
        reachLoading={reachLoading}
        pageLabel={current.pageLabel}
        period={period}
        onPeriodChange={undefined}
        platform={platform}
        overviewInsights={overviewInsights}
      />
    </div>
  )
}
