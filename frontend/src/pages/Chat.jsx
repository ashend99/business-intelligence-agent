// Chatbot — exact port of nexus/pages/chatbot.jsx

import { useState, useRef, useEffect, useCallback } from 'react'
import { Icons } from '../components/Icons'
import { KnowledgeBaseModal } from '../components/KnowledgeBaseModal'
import { businessConfig } from '../config'

const BUSINESS_KEYS = businessConfig.business.businesses.map(b => b.key)

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

const INITIAL_THREAD = [
  { role: 'user', text: "What's driving the revenue spike this week?" },
  {
    role: 'ai', persona: 'Analyst', text: 'Revenue is up 12.4% WoW, almost entirely driven by the LinkedIn sponsored campaign that launched Sunday May 11. It is responsible for 34% of new MQLs and $84K in attributable revenue. Bounce rate from that source is also notably low at 28%.',
    sources: [
      { name: 'linkedin-ads-may.json', relevance: 96 },
      { name: 'orders-2026-05.csv', relevance: 92 },
      { name: 'attribution-model-v3.pkl', relevance: 81 },
    ],
    followups: ['Forecast next 7 days', 'Why is bounce so low?', 'Compare to Google Ads'],
  },
  { role: 'user', text: 'Are any deals at risk because of the shipping incident last week?' },
  {
    role: 'ai', persona: 'Analyst', text: 'Yes — 2 deals show elevated risk. Acme Corp delayed their Proposal sign-off after a related complaint thread, and Skyline Ltd has been silent for 9 days. I checked the chat logs: both were waiting on hardware that was on the affected North-Atlantic shipment. Recommend personalized outreach + an updated ETA.',
    sources: [
      { name: 'crm-acme-corp.json', relevance: 94 },
      { name: 'crm-skyline-ltd.json', relevance: 91 },
      { name: 'shipments-northatlantic.json', relevance: 88 },
      { name: 'support-tickets-may.db', relevance: 76 },
    ],
    followups: ['Draft outreach for both', 'Open Acme deal', 'Show full shipment impact'],
  },
]

export function Chat({ businessKey, onBusiness }) {
  const [thinking, setThinking] = useState(false)
  const [thread,   setThread]   = useState(INITIAL_THREAD)
  const [kbOpen,   setKbOpen]   = useState(false)
  const [activeDocs, setActiveDocs] = useState([])
  const [docsLoading, setDocsLoading] = useState(false)
  const threadRef = useRef(null)

  const fetchDocs = useCallback(async () => {
    setDocsLoading(true)
    try {
      const results = await Promise.all(
        BUSINESS_KEYS.map(key =>
          fetch(`http://localhost:8000/api/documents/list/${key}`)
            .then(r => r.ok ? r.json() : { documents: [] })
            .catch(() => ({ documents: [] }))
        )
      )
      const merged = results.flatMap(r => r.documents ?? [])
      // Aggregate duplicates across collections
      const map = {}
      for (const d of merged) map[d.name] = (map[d.name] ?? 0) + d.chunks
      setActiveDocs(Object.entries(map).map(([name, chunks]) => ({ name, chunks })).sort((a, b) => a.name.localeCompare(b.name)))
    } finally {
      setDocsLoading(false)
    }
  }, [])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight
  }, [thread, thinking])

  const sendDraft = () => {
    setThinking(true)
    setThread(t => [...t, { role: 'user', text: 'Draft the outreach for both accounts.' }])
    setTimeout(() => {
      setThread(t => [...t, {
        role: 'ai', text: "Drafted two emails — different in tone since Acme is mid-cycle and Skyline has gone quiet. Both reference the shipment context and offer a concrete revised ETA. Want me to send for your approval?",
        sources: [{ name: 'brand-voice.md', relevance: 86 }, { name: 'email-templates.md', relevance: 78 }],
        followups: ['Show drafts', 'Send for approval', 'Adjust tone'],
      }])
      setThinking(false)
    }, 1500)
  }

  return (
    <>
      <div style={{ display: 'flex', height: '100%', minHeight: 0 }}>
      {/* Chat column */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Thread actions */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn sm"><Icons.Plus size={11} />New thread</button>
            <button className="btn sm"><Icons.Clock size={11} />History</button>
            <button className="btn ghost sm"><Icons.Dots size={12} /></button>
          </div>
        </div>

        {/* Thread */}
        <div ref={threadRef} className="scroll-y" style={{ flex: 1, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
          {thread.map((m, i) => m.role === 'user' ? (
            <div key={i} style={{ alignSelf: 'flex-end', maxWidth: '72%' }}>
              <div className="panel-2" style={{ padding: '10px 14px', borderRadius: 12, borderTopRightRadius: 4 }}>{m.text}</div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', textAlign: 'right', marginTop: 4 }}>You · just now</div>
            </div>
          ) : (
            <div key={i} style={{ alignSelf: 'flex-start', maxWidth: '88%', display: 'flex', gap: 10 }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: 'var(--indigo-soft)', color: 'var(--indigo)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 28px' }}>
                <Icons.Sparkle size={14} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>Nexus</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)' }}>1.2s · 1,840 tokens</span>
                </div>
                <div style={{ padding: '12px 14px', background: 'var(--panel)', border: '1px solid var(--border)', borderLeft: '2px solid var(--teal)', borderRadius: 8, fontSize: 13, lineHeight: 1.6 }}>
                  {m.text}
                  {m.sources && <Citations sources={m.sources} />}
                </div>
                {m.followups && (
                  <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                    {m.followups.map((f, fi) => (
                      <button key={fi} className="btn sm" style={{ background: 'var(--bg)', borderColor: 'var(--border)' }}>{f}</button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {thinking && (
            <div style={{ alignSelf: 'flex-start', maxWidth: '88%', display: 'flex', gap: 10 }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: 'var(--indigo-soft)', color: 'var(--indigo)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 28px' }}>
                <Icons.Sparkle size={14} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 8 }}>
                  <span className="pulse-dot" />
                  <span style={{ fontSize: 12 }}>Thinking…</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-3)' }}>Running tool: <span style={{ color: 'var(--indigo)' }}>draft_emails(accounts=[acme,skyline])</span></span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Composer */}
        <div style={{ padding: '12px 20px 18px', borderTop: '1px solid var(--border)', background: 'var(--bg)' }}>
          <div className="panel-2" style={{ padding: 10, display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            <textarea className="input" placeholder="Ask anything…" rows={1}
              style={{ flex: 1, background: 'transparent', border: 'none', resize: 'none', minHeight: 24, maxHeight: 120 }} />
            <button className="btn ghost icon" title="Attach"><Icons.Doc size={14} /></button>
            <button className="btn ghost icon" title="Mention KB"><Icons.Folder size={14} /></button>
            <button className="btn primary" onClick={sendDraft}><Icons.Send size={12} />Send</button>
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 11, color: 'var(--text-3)' }}>
            <span><span className="kbd">⏎</span> send</span>
            <span><span className="kbd">⇧⏎</span> newline</span>
            <span><span className="kbd">/</span> commands</span>
            <span><span className="kbd">@</span> reference a doc</span>
          </div>
        </div>
      </div>

      {/* Context column */}
      <div style={{ width: 340, flex: '0 0 340px', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', fontSize: 13, fontWeight: 600 }}>Conversation context</div>
        <div className="scroll-y" style={{ flex: 1, padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div className="label" style={{ marginBottom: 8 }}>Active Documents</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, height: 160, overflowY: 'auto', paddingRight: 2 }}>
              {docsLoading && (
                <div style={{ fontSize: 11, color: 'var(--text-3)', padding: '6px 0' }}>Loading…</div>
              )}
              {!docsLoading && activeDocs.length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--text-3)', padding: '6px 0' }}>No documents indexed yet.</div>
              )}
              {!docsLoading && activeDocs.map(doc => (
                <div key={doc.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 6px', borderRadius: 6, background: 'var(--panel-2)', border: '1px solid var(--border)', minWidth: 0 }}>
                  <Icons.Folder size={11} style={{ flexShrink: 0 }} />
                  <span className="mono" style={{ flex: 1, fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.name}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap', flexShrink: 0 }}>{doc.chunks.toLocaleString()} chunks</span>
                </div>
              ))}
            </div>
            <button className="btn sm" style={{ justifyContent: 'flex-start', marginTop: 6 }} onClick={() => setKbOpen(true)}><Icons.Plus size={11} />Add/Replace/Delete Documents</button>
          </div>

          <div>
            <div className="label" style={{ marginBottom: 8 }}>Recent topics</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {['Revenue spike · LinkedIn campaign', 'At-risk deals · shipping incident', 'Refund pattern analysis', 'Q2 cohort retention'].map(t => (
                <div key={t} className="clickable" style={{ padding: '6px 8px', borderRadius: 4, fontSize: 12, color: 'var(--text-2)' }}>{t}</div>
              ))}
            </div>
          </div>

          <div>
            <div className="label" style={{ marginBottom: 8 }}>Suggested prompts</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {['Forecast next 7 days of revenue', 'Find anomalies in pipeline', 'Compare May vs April sentiment', "Summarize today's support tickets"].map(p => (
                <button key={p} className="btn sm" style={{ justifyContent: 'flex-start', textAlign: 'left' }}><Icons.Sparkle size={11} />{p}</button>
              ))}
            </div>
          </div>

          <div>
            <div className="label" style={{ marginBottom: 8 }}>Tools available</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {['get_revenue', 'draft_email', 'open_deal', 'run_sql', 'schedule_followup', 'sentiment_score', '+8'].map(t => (
                <span key={t} className="chip mono" style={{ fontSize: 10 }}>{t}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
    <KnowledgeBaseModal open={kbOpen} onClose={() => { setKbOpen(false); fetchDocs() }} />
    </>
  )
}
