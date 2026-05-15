// Chatbot — wired to POST /api/chat

import { useState, useRef, useEffect, useCallback } from 'react'
import { Icons } from '../components/Icons'
import { KnowledgeBaseModal } from '../components/KnowledgeBaseModal'
import { businessConfig } from '../config'

const BUSINESS_KEYS = businessConfig.business.businesses.map(b => b.key)

function newThreadId() {
  return crypto.randomUUID()
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

export function Chat({ onNavigate }) {
  const [businessKey, setBusinessKey] = useState(BUSINESS_KEYS[0])
  const [threadId,    setThreadId]    = useState(newThreadId)
  const [thread,      setThread]      = useState([])
  const [input,       setInput]       = useState('')
  const [thinking,    setThinking]    = useState(false)
  const [kbOpen,      setKbOpen]      = useState(false)
  const [activeDocs,  setActiveDocs]  = useState([])
  const [docsLoading, setDocsLoading] = useState(false)
  const threadRef  = useRef(null)
  const textareaRef = useRef(null)

  const fetchDocs = useCallback(async () => {
    setDocsLoading(true)
    try {
      const colRes = await fetch('http://localhost:8000/api/collections')
        .then(r => r.ok ? r.json() : { collections: [] })
        .catch(() => ({ collections: [] }))
      const allCollections = colRes.collections ?? []
      const results = await Promise.all(
        allCollections.map(col =>
          fetch(`http://localhost:8000/api/documents/list/${col}`)
            .then(r => r.ok ? r.json() : { documents: [], business_key: col })
            .catch(() => ({ documents: [], business_key: col }))
        )
      )
      const docs = results.flatMap((r, i) =>
        (r.documents ?? []).map(d => ({ name: d.name, chunks: d.chunks, collection: r.business_key ?? allCollections[i] }))
      )
      docs.sort((a, b) => a.collection.localeCompare(b.collection) || a.name.localeCompare(b.name))
      setActiveDocs(docs)
    } finally {
      setDocsLoading(false)
    }
  }, [])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight
  }, [thread, thinking])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [input])

  const newThread = () => {
    setThread([])
    setThreadId(newThreadId())
    setInput('')
  }

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || thinking) return
    setInput('')
    setThread(t => [...t, { role: 'user', text, ts: Date.now() }])
    setThinking(true)
    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_key: businessKey, thread_id: threadId, message: text }),
      })
      if (!res.ok) {
        const err = await res.text()
        setThread(t => [...t, { role: 'ai', text: `Error: ${err}`, isError: true, ts: Date.now() }])
      } else {
        const data = await res.json()
        setThread(t => [...t, { role: 'ai', text: data.answer, ts: Date.now() }])
      }
    } catch (e) {
      setThread(t => [...t, { role: 'ai', text: `Network error: ${e.message}`, isError: true, ts: Date.now() }])
    } finally {
      setThinking(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      <div style={{ display: 'flex', height: '100%', minHeight: 0 }}>
      {/* Chat column */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Thread actions */}
        <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Business key selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1 }}>
            <Icons.Folder size={12} style={{ color: 'var(--text-3)' }} />
            <select
              value={businessKey}
              onChange={e => { setBusinessKey(e.target.value); newThread() }}
              className="input"
              style={{ fontSize: 12, padding: '3px 8px', height: 28, cursor: 'pointer', width: 'auto', minWidth: 120 }}
            >
              {BUSINESS_KEYS.map(k => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn sm" onClick={newThread}><Icons.Plus size={11} />New thread</button>
            <button className="btn ghost sm"><Icons.Clock size={11} />History</button>
          </div>
        </div>

        {/* Thread */}
        <div ref={threadRef} className="scroll-y" style={{ flex: 1, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
          {thread.length === 0 && !thinking && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: 'var(--text-3)', paddingTop: 60 }}>
              <Icons.Sparkle size={28} />
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-2)' }}>Ask Nexus anything</div>
              <div style={{ fontSize: 12 }}>Context: <span style={{ color: 'var(--indigo)', fontFamily: 'var(--mono)' }}>{businessKey}</span></div>
            </div>
          )}

          {thread.map((m, i) => m.role === 'user' ? (
            <div key={i} style={{ alignSelf: 'flex-end', maxWidth: '72%' }}>
              <div className="panel-2" style={{ padding: '10px 14px', borderRadius: 12, borderTopRightRadius: 4, fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{m.text}</div>
              <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', textAlign: 'right', marginTop: 4 }}>You</div>
            </div>
          ) : (
            <div key={i} style={{ alignSelf: 'flex-start', maxWidth: '88%', display: 'flex', gap: 10 }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: m.isError ? 'rgba(255,99,99,0.1)' : 'var(--indigo-soft)', color: m.isError ? 'var(--coral)' : 'var(--indigo)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 28px' }}>
                <Icons.Sparkle size={14} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>Nexus</span>
                </div>
                <div style={{
                  padding: '12px 14px', background: 'var(--panel)',
                  border: '1px solid var(--border)',
                  borderLeft: `2px solid ${m.isError ? 'var(--coral)' : 'var(--teal)'}`,
                  borderRadius: 8, fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap',
                  color: m.isError ? 'var(--coral)' : undefined,
                }}>
                  {m.text}
                </div>
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
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Composer */}
        <div style={{ padding: '12px 20px 18px', borderTop: '1px solid var(--border)', background: 'var(--bg)' }}>
          <div className="panel-2" style={{ padding: 10, display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            <textarea
              ref={textareaRef}
              className="input"
              placeholder={`Ask about ${businessKey}…`}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={thinking}
              style={{ flex: 1, background: 'transparent', border: 'none', resize: 'none', minHeight: 24, maxHeight: 120, lineHeight: 1.5 }}
            />
            <button
              className="btn primary"
              onClick={sendMessage}
              disabled={thinking || !input.trim()}
            >
              <Icons.Send size={12} />{thinking ? 'Sending…' : 'Send'}
            </button>
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 11, color: 'var(--text-3)' }}>
            <span><span className="kbd">⏎</span> send</span>
            <span><span className="kbd">⇧⏎</span> newline</span>
          </div>
        </div>
      </div>

      {/* Context column */}
      <div style={{ width: 300, flex: '0 0 300px', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', fontSize: 13, fontWeight: 600 }}>Conversation context</div>
        <div className="scroll-y" style={{ flex: 1, padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div className="label" style={{ marginBottom: 8 }}>Active Documents</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 260, overflowY: 'auto', paddingRight: 2 }}>
              {docsLoading && <div style={{ fontSize: 11, color: 'var(--text-3)', padding: '6px 0' }}>Loading…</div>}
              {!docsLoading && activeDocs.length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--text-3)', padding: '6px 0' }}>No documents indexed yet.</div>
              )}
              {!docsLoading && activeDocs.map((doc, i) => (
                <div key={`${doc.collection}/${doc.name}/${i}`} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 6px', borderRadius: 6, background: 'var(--panel-2)', border: '1px solid var(--border)', minWidth: 0 }}>
                  <Icons.Folder size={11} style={{ flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.collection}</div>
                    <div className="mono" style={{ fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.name}</div>
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap', flexShrink: 0 }}>{doc.chunks.toLocaleString()}</span>
                </div>
              ))}
            </div>
            <button className="btn sm" style={{ justifyContent: 'flex-start', marginTop: 6 }} onClick={() => setKbOpen(true)}>
              <Icons.Plus size={11} />Manage Documents
            </button>
          </div>

          <div>
            <div className="label" style={{ marginBottom: 8 }}>Thread info</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11, color: 'var(--text-3)' }}>
              <div style={{ display: 'flex', gap: 6 }}>
                <span>Collection:</span>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--indigo)' }}>{businessKey}</span>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <span>Messages:</span>
                <span style={{ fontFamily: 'var(--mono)' }}>{thread.length}</span>
              </div>
              <div style={{ display: 'flex', gap: 6, overflow: 'hidden' }}>
                <span style={{ flexShrink: 0 }}>Thread ID:</span>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{threadId}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <KnowledgeBaseModal open={kbOpen} onClose={() => { setKbOpen(false); fetchDocs() }} />
    </>
  )
}

  const fetchDocs = useCallback(async () => {
    setDocsLoading(true)
    try {
      // Discover all collections (includes dynamically created ones)
      const colRes = await fetch('http://localhost:8000/api/collections').then(r => r.ok ? r.json() : { collections: [] }).catch(() => ({ collections: [] }))
      const allCollections = colRes.collections ?? []

      const results = await Promise.all(
        allCollections.map(col =>
          fetch(`http://localhost:8000/api/documents/list/${col}`)
            .then(r => r.ok ? r.json() : { documents: [], business_key: col })
            .catch(() => ({ documents: [], business_key: col }))
        )
      )
      // Keep collection label per doc (no merging across collections)
      const docs = results.flatMap((r, i) =>
        (r.documents ?? []).map(d => ({ name: d.name, chunks: d.chunks, collection: r.business_key ?? allCollections[i] }))
      )
      docs.sort((a, b) => a.collection.localeCompare(b.collection) || a.name.localeCompare(b.name))
      setActiveDocs(docs)
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
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, height: 240, overflowY: 'auto', paddingRight: 2 }}>
              {docsLoading && (
                <div style={{ fontSize: 11, color: 'var(--text-3)', padding: '6px 0' }}>Loading…</div>
              )}
              {!docsLoading && activeDocs.length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--text-3)', padding: '6px 0' }}>No documents indexed yet.</div>
              )}
              {!docsLoading && activeDocs.map((doc, i) => (
                <div key={`${doc.collection}/${doc.name}/${i}`} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 6px', borderRadius: 6, background: 'var(--panel-2)', border: '1px solid var(--border)', minWidth: 0 }}>
                  <Icons.Folder size={11} style={{ flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.collection}</div>
                    <div className="mono" style={{ fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.name}</div>
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap', flexShrink: 0 }}>{doc.chunks.toLocaleString()} chunks</span>
                </div>
              ))}
            </div>
            <button className="btn sm" style={{ justifyContent: 'flex-start', marginTop: 6 }} onClick={() => setKbOpen(true)}><Icons.Plus size={11} />Manage Documents</button>
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
