// Home — exact port of nexus/pages/home.jsx

import { useState } from 'react'
import { Icons } from '../components/Icons'

function AIInsight({ children, title = 'AI Insight', actions }) {
  return (
    <div className="ai-insight">
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ width: 22, height: 22, borderRadius: 6, background: 'var(--indigo-soft-2)', color: 'var(--indigo)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 22px' }}>
          <Icons.Sparkle size={12} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
            <span style={{ fontSize: 11, color: 'var(--indigo)', fontWeight: 600, letterSpacing: 0.4, textTransform: 'uppercase' }}>{title}</span>
            <span style={{ color: 'var(--text-4)' }}>·</span>
            <span style={{ fontSize: 11, color: 'var(--text-3)' }}>How did AI get this?</span>
          </div>
          <div style={{ color: 'var(--text)', fontSize: 13, lineHeight: 1.55 }}>{children}</div>
          {actions && <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>{actions}</div>}
        </div>
      </div>
    </div>
  )
}

function Citations({ sources, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ marginTop: 8 }}>
      <button className="btn ghost sm" style={{ padding: '2px 6px', color: 'var(--text-3)' }} onClick={() => setOpen(!open)}>
        <Icons.Doc size={12} />
        <span>Sources · {sources.length}</span>
        <Icons.ChevronDown size={12} />
      </button>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6, paddingLeft: 6, borderLeft: '1px solid var(--border)' }}>
          {sources.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--text-2)', padding: '2px 0' }}>
              <Icons.Doc size={11} />
              <span style={{ flex: 1, fontFamily: 'var(--mono)' }}>{s.name}</span>
              <span style={{ color: 'var(--teal)', fontFamily: 'var(--mono)' }}>{s.relevance}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function KPI({ label, value, delta, deltaColor }) {
  return (
    <div className="panel" style={{ padding: 14, flex: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="label">{label}</span>
        {delta && <span className="mono" style={{ fontSize: 11, color: deltaColor || (delta.startsWith('-') ? 'var(--coral)' : 'var(--teal)') }}>{delta}</span>}
      </div>
      <div className="num-lg" style={{ marginTop: 4 }}>{value}</div>
    </div>
  )
}

function SectionHead({ title, subtitle, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{title}</div>
        {subtitle && <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>{subtitle}</div>}
      </div>
      {right}
    </div>
  )
}

function AgentActionItem({ icon, text, time }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 10px', borderRadius: 6, background: 'var(--panel-2)', border: '1px solid var(--border)' }}>
      <span style={{ fontSize: 12, color: 'var(--indigo)', marginTop: 1 }}>{icon}</span>
      <span style={{ flex: 1, fontSize: 12, color: 'var(--text-2)' }}>{text}</span>
      <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)', whiteSpace: 'nowrap' }}>{time}</span>
    </div>
  )
}

export function Home({ onNavigate }) {
  return (
    <div className="page-body" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Welcome + briefing */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'stretch' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.01em' }}>Good morning, Amir</div>
          <div style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>Tuesday, May 13, 2026 · Aurora Labs workspace</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn"><Icons.Calendar size={12} />Today</button>
          <button className="btn"><Icons.Filter size={12} />All teams</button>
          <button className="btn primary"><Icons.Plus size={12} />New report</button>
        </div>
      </div>

      <AIInsight
        title="Daily briefing · 06:42"
        actions={
          <>
            <button className="btn sm">View full briefing</button>
            <button className="btn ghost sm">Re-run</button>
            <button className="btn ghost sm">Mute briefings</button>
          </>
        }
      >
        Here's what needs your attention today. <span style={{ color: 'var(--text)', fontWeight: 600 }}>Revenue is pacing 12.4% ahead of goal</span>, driven mostly by the LinkedIn campaign that launched Sunday. <span style={{ color: 'var(--coral)' }}>3 support tickets are now past SLA</span> — agent recommends pulling Jordan in. The North-Atlantic shipment delay from yesterday has cascaded into <span style={{ color: 'var(--amber)' }}>11 affected orders</span>; I drafted reply templates and queued them for your approval.
        <Citations sources={[
          { name: 'orders-2026-05-13.csv', relevance: 96 },
          { name: 'support-queue.live', relevance: 91 },
          { name: 'logistics-incidents.md', relevance: 84 },
          { name: 'sales-ops-handbook.pdf', relevance: 71 },
        ]} />
      </AIInsight>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <KPI label="Revenue today" value="$48,210" delta="+8.2%" />
        <KPI label="Open tickets" value="37" delta="+4" deltaColor="var(--coral)" />
        <KPI label="Team tasks due" value="18" delta="−3" />
        <KPI label="Social mentions" value="92" delta="+18%" />
      </div>

      {/* 2x2 preview grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* Analytics mini */}
        <div className="panel clickable" style={{ padding: 16 }} onClick={() => onNavigate('analytics')}>
          <SectionHead
            title="Analytics"
            subtitle="Revenue · 30 days"
            right={<button className="btn ghost sm"><Icons.ArrowRight size={12} /></button>}
          />
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 6 }}>
            <span className="num-md">$248,902</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--teal)' }}>+12.4% MoM</span>
          </div>
          <div style={{ height: 60, background: 'var(--panel-2)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--text-4)' }}>chart</span>
          </div>
        </div>

        {/* Sales pipeline mini */}
        <div className="panel clickable" style={{ padding: 16 }} onClick={() => onNavigate('sales')}>
          <SectionHead
            title="Sales pipeline"
            subtitle="$1.42M weighted · 47 active deals"
            right={<button className="btn ghost sm"><Icons.ArrowRight size={12} /></button>}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              ['Lead', 18, 320, 'var(--text-3)'],
              ['Qualified', 12, 480, 'var(--indigo)'],
              ['Proposal', 9, 360, 'var(--indigo)'],
              ['Negotiation', 5, 220, 'var(--amber)'],
              ['Closed', 3, 90, 'var(--teal)'],
            ].map(([label, count, val, c]) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 12, color: 'var(--text-2)', width: 88 }}>{label}</span>
                <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--panel-2)' }}>
                  <div style={{ width: `${(val / 500) * 100}%`, height: '100%', borderRadius: 3, background: c }} />
                </div>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)', width: 24, textAlign: 'right' }}>{count}</span>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text)', width: 56, textAlign: 'right' }}>${val}k</span>
              </div>
            ))}
          </div>
        </div>

        {/* Team board mini */}
        <div className="panel clickable" style={{ padding: 16 }} onClick={() => onNavigate('team')}>
          <SectionHead
            title="Team"
            subtitle="12 online · 18 tasks due this week"
            right={<button className="btn ghost sm"><Icons.ArrowRight size={12} /></button>}
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
            {[
              ['JK', 'Jordan K.', 72, 'indigo'],
              ['MR', 'Maya R.', 88, 'amber'],
              ['DS', 'Diego S.', 45, 'teal'],
              ['EL', 'Elena L.', 95, 'coral'],
            ].map(([initials, name, load, color]) => (
              <div key={initials} className="panel-2" style={{ padding: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div className={`avatar ${color}`}>{initials}</div>
                  <span style={{ fontSize: 11, color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name.split(' ')[0]}</span>
                </div>
                <div style={{ marginTop: 6, height: 4, borderRadius: 2, background: 'var(--panel-3)' }}>
                  <div style={{ width: `${load}%`, height: '100%', borderRadius: 2, background: load > 85 ? 'var(--coral)' : load > 60 ? 'var(--amber)' : 'var(--teal)' }} />
                </div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 4 }}>{load}% capacity</div>
              </div>
            ))}
          </div>
        </div>

        {/* Social feed mini */}
        <div className="panel clickable" style={{ padding: 16 }} onClick={() => onNavigate('social')}>
          <SectionHead
            title="Social"
            subtitle="Latest mentions · sentiment 78% positive"
            right={<button className="btn ghost sm"><Icons.ArrowRight size={12} /></button>}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              { plat: 'LinkedIn', who: '@greenroofco', text: 'Just installed Nexus across our 4 offices. The AI briefings alone are…', sent: 'Positive', icon: 'LinkedIn' },
              { plat: 'X', who: '@dataeng_kate', text: 'Nexus vs Linear for analytics — anyone made the switch?', sent: 'Neutral', icon: 'Twitter' },
              { plat: 'Instagram', who: '@solar.studio', text: 'Tagged you in a reel · 84K views', sent: 'Positive', icon: 'Instagram' },
            ].map((m, i) => {
              const Icon = Icons[m.icon]
              return (
                <div key={i} style={{ display: 'flex', gap: 10, padding: '8px 0', borderBottom: i < 2 ? '1px solid var(--border)' : 0 }}>
                  <div style={{ width: 24, height: 24, borderRadius: 6, background: 'var(--panel-2)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 24px' }}><Icon size={12} /></div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-3)' }}>
                      <span>{m.who}</span><span>·</span><span>{m.plat}</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.text}</div>
                  </div>
                  <span className={`chip ${m.sent === 'Positive' ? 'teal' : m.sent === 'Negative' ? 'coral' : ''}`}>{m.sent}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Recent AI actions strip */}
      <div className="panel" style={{ padding: 14 }}>
        <SectionHead
          title="Recent agent activity"
          subtitle="What Nexus did for you while you were away"
          right={<button className="btn ghost sm">View audit log <Icons.ArrowRight size={11} /></button>}
        />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
          <AgentActionItem icon="✦" text="Summarized 3 weekly reports into a single brief" time="2m ago" />
          <AgentActionItem icon="✦" text="Answered 12 customer queries in chatbot" time="5m ago" />
          <AgentActionItem icon="✦" text="Flagged Acme Corp deal as at-risk (no reply in 7d)" time="14m ago" />
          <AgentActionItem icon="✦" text="Reassigned 2 tickets based on team workload" time="22m ago" />
          <AgentActionItem icon="✦" text="Drafted 4 social replies for review" time="38m ago" />
          <AgentActionItem icon="✦" text="Generated daily briefing" time="1h ago" />
        </div>
      </div>
    </div>
  )
}        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>How did AI get this?</span>
