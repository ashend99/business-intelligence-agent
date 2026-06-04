// Chatbot — wired to POST /api/chat, with localStorage session persistence

import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Icons } from '../components/Icons'
import { KnowledgeBaseModal } from '../components/KnowledgeBaseModal'
import { businessConfig } from '../config'

const BUSINESS_KEYS = businessConfig.business.businesses.map(b => b.key)
const SESSIONS_KEY  = 'nexus_chat_sessions'

function newThreadId() { return crypto.randomUUID() }

function loadSessions() {
  try { return JSON.parse(localStorage.getItem(SESSIONS_KEY) ?? '[]') } catch { return [] }
}

function persistSessions(sessions) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

function makeSession(threadId, messages = []) {
  const title = messages.find(m => m.role === 'user')?.text?.slice(0, 48) ?? 'New chat'
  return { id: threadId, title, messages, createdAt: Date.now(), updatedAt: Date.now() }
}

function formatReasoningContent(content) {
  if (content == null) return ''
  if (typeof content === 'string') return content
  try {
    return JSON.stringify(content, null, 2)
  } catch {
    return String(content)
  }
}

function appendReasoningStep(message, step) {
  const current = Array.isArray(message.reasoning) ? message.reasoning : []
  return { ...message, reasoning: [...current, step] }
}

// HistoryPanel — sidebar showing saved sessions
function HistoryPanel({ sessions, activeId, onSelect, onDelete, onClose }) {
  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 40,
      display: 'flex', flexDirection: 'row',
    }}>
      {/* Backdrop */}
      <div style={{ flex: 1, background: 'rgba(0,0,0,0.25)' }} onClick={onClose} />
      {/* Panel */}
      <div style={{
        width: 300, background: 'var(--bg)', borderLeft: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', height: '100%',
      }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ flex: 1, fontSize: 13, fontWeight: 600 }}>Chat history</span>
          <button className="btn ghost sm" style={{ padding: '2px 6px' }} onClick={onClose}><Icons.X size={13} /></button>
        </div>
        <div className="scroll-y" style={{ flex: 1, padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {sessions.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--text-3)', padding: '16px 8px', textAlign: 'center' }}>No saved chats yet</div>
          )}
          {[...sessions].reverse().map(s => (
            <div
              key={s.id}
              onClick={() => onSelect(s)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px',
                borderRadius: 8, cursor: 'pointer',
                background: s.id === activeId ? 'var(--indigo-soft)' : 'transparent',
                border: s.id === activeId ? '1px solid var(--indigo)' : '1px solid transparent',
              }}
            >
              <Icons.Chat size={13} style={{ flexShrink: 0, color: s.id === activeId ? 'var(--indigo)' : 'var(--text-3)' }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</div>
                <div style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 2 }}>
                  {s.messages.length} msg · {new Date(s.updatedAt).toLocaleDateString()}
                </div>
              </div>
              <button
                className="btn ghost sm"
                style={{ padding: '2px 4px', flexShrink: 0, opacity: 0.5 }}
                onClick={e => { e.stopPropagation(); onDelete(s.id) }}
              ><Icons.Trash size={12} /></button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function Chat({ onNavigate }) {
  const businessKey = BUSINESS_KEYS[0]

  // Sessions
  const [sessions,     setSessions]     = useState(loadSessions)
  const [threadId,     setThreadId]     = useState(() => {
    const saved = loadSessions()
    return saved.length > 0 ? saved[saved.length - 1].id : newThreadId()
  })
  const [thread,       setThread]       = useState(() => {
    const saved = loadSessions()
    return saved.length > 0 ? saved[saved.length - 1].messages : []
  })

  const [input,        setInput]        = useState('')
  const [thinking,     setThinking]     = useState(false)
  const [kbOpen,       setKbOpen]       = useState(false)
  const [historyOpen,  setHistoryOpen]  = useState(false)
  const [activeDocs,   setActiveDocs]   = useState([])
  const [docsLoading,  setDocsLoading]  = useState(false)
  const threadRef   = useRef(null)
  const textareaRef = useRef(null)

  // Persist sessions whenever thread changes
  const saveThread = useCallback((tid, messages) => {
    setSessions(prev => {
      const idx = prev.findIndex(s => s.id === tid)
      let next
      if (idx >= 0) {
        next = prev.map((s, i) => i === idx
          ? { ...s, messages, title: messages.find(m => m.role === 'user')?.text?.slice(0, 48) ?? s.title, updatedAt: Date.now() }
          : s)
      } else {
        next = [...prev, makeSession(tid, messages)]
      }
      persistSessions(next)
      return next
    })
  }, [])

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

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [input])

  const newThread = () => {
    const tid = newThreadId()
    const emptySession = makeSession(tid, [])
    setSessions(prev => { const next = [...prev, emptySession]; persistSessions(next); return next })
    setThreadId(tid)
    setThread([])
    setInput('')
  }

  const switchSession = (session) => {
    setThreadId(session.id)
    setThread(session.messages)
    setInput('')
    setHistoryOpen(false)
  }

  const deleteSession = (id) => {
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id)
      persistSessions(next)
      // If we deleted the active session, load last or start fresh
      if (id === threadId) {
        if (next.length > 0) {
          const last = next[next.length - 1]
          setThreadId(last.id)
          setThread(last.messages)
        } else {
          const tid = newThreadId()
          setThreadId(tid)
          setThread([])
        }
      }
      return next
    })
  }

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || thinking) return
    setInput('')
    const userMsg = { role: 'user', text, ts: Date.now() }
    setThread(t => {
      const next = [...t, userMsg]
      saveThread(threadId, next)
      return next
    })

    const aiMessageId = crypto.randomUUID()
    setThread(t => {
      const next = [...t, { id: aiMessageId, role: 'ai', text: '', reasoning: [], streaming: true, ts: Date.now() }]
      saveThread(threadId, next)
      return next
    })

    const updateAiMessage = updater => {
      setThread(t => {
        const next = t.map(msg => (msg.id === aiMessageId ? updater(msg) : msg))
        saveThread(threadId, next)
        return next
      })
    }

    setThinking(true)
    try {
      const res = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_key: businessKey, thread_id: threadId, message: text }),
      })
      if (!res.ok) {
        const err = await res.text()
        updateAiMessage(msg => ({ ...msg, text: `Error: ${err}`, isError: true, streaming: false }))
      } else if (!res.body) {
        updateAiMessage(msg => ({ ...msg, text: 'Error: Stream body not available', isError: true, streaming: false }))
      } else {
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { value, done } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed) continue

            let evt
            try {
              evt = JSON.parse(trimmed)
            } catch {
              continue
            }

            if (evt.type === 'reasoning') {
              updateAiMessage(msg => appendReasoningStep(msg, evt.step))
            } else if (evt.type === 'final') {
              updateAiMessage(msg => ({
                ...msg,
                text: evt.answer || '',
                reasoning: Array.isArray(evt.reasoning) ? evt.reasoning : (msg.reasoning || []),
                streaming: false,
              }))
            } else if (evt.type === 'error') {
              updateAiMessage(msg => ({
                ...msg,
                text: `Error: ${evt.error || 'Unknown error'}`,
                isError: true,
                streaming: false,
              }))
            }
          }
        }

        // Flush any final buffered event fragment if newline was omitted.
        const tail = buffer.trim()
        if (tail) {
          try {
            const evt = JSON.parse(tail)
            if (evt.type === 'final') {
              updateAiMessage(msg => ({
                ...msg,
                text: evt.answer || '',
                reasoning: Array.isArray(evt.reasoning) ? evt.reasoning : (msg.reasoning || []),
                streaming: false,
              }))
            }
          } catch {
            // Ignore malformed tail.
          }
        }

        // Ensure streaming state ends even when no explicit final event arrives.
        updateAiMessage(msg => ({ ...msg, streaming: false }))
      }
    } catch (e) {
      updateAiMessage(msg => ({ ...msg, text: `Network error: ${e.message}`, isError: true, streaming: false }))
    } finally {
      setThinking(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  return (
    <>
      <div style={{ display: 'flex', height: '100%', minHeight: 0, position: 'relative' }}>

      {/* History overlay panel */}
      {historyOpen && (
        <HistoryPanel
          sessions={sessions}
          activeId={threadId}
          onSelect={switchSession}
          onDelete={deleteSession}
          onClose={() => setHistoryOpen(false)}
        />
      )}

      {/* Chat column */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Thread actions */}
        <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', gap: 6 }}>
            <button className="btn sm" onClick={newThread}><Icons.Plus size={11} />New thread</button>
            <button className="btn ghost sm" onClick={() => setHistoryOpen(o => !o)}><Icons.Clock size={11} />History ({sessions.length})</button>
          </div>
        </div>

        {/* Thread */}
        <div ref={threadRef} className="scroll-y" style={{ flex: 1, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
          {thread.length === 0 && !thinking && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: 'var(--text-3)', paddingTop: 60 }}>
              <Icons.Sparkle size={28} />
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-2)' }}>Ask Nexus anything</div>
              <div style={{ fontSize: 12 }}>Searches across all knowledge bases</div>
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
                {!!m.reasoning?.length && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ fontSize: 11, color: 'var(--text-3)', cursor: 'pointer', userSelect: 'none' }}>
                      Reasoning and tools ({m.reasoning.length})
                    </summary>
                    <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {m.reasoning.map((step, idx) => (
                        <div
                          key={`${m.ts ?? i}-${idx}`}
                          style={{
                            padding: '8px 10px',
                            border: '1px solid var(--border)',
                            borderRadius: 6,
                            background: 'var(--panel-2)',
                          }}
                        >
                          <div className="mono" style={{ fontSize: 10, color: 'var(--text-3)', marginBottom: 4 }}>
                            {step.type || 'step'}{step.tool ? ` · ${step.tool}` : ''}
                          </div>
                          <div style={{ fontSize: 12, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                            {formatReasoningContent(step.content ?? step.input ?? step)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
                <div style={{
                  padding: '12px 14px', background: 'var(--panel)',
                  border: '1px solid var(--border)',
                  borderLeft: `2px solid ${m.isError ? 'var(--coral)' : 'var(--teal)'}`,
                  borderRadius: 8, fontSize: 13, lineHeight: 1.7,
                  color: m.isError ? 'var(--coral)' : undefined,
                  marginTop: m.reasoning?.length ? 8 : 0,
                }}>
                  {m.streaming && !m.text
                    ? <span style={{ color: 'var(--text-3)' }}>Streaming response…</span>
                    : <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => <p style={{ margin: '0 0 8px' }}>{children}</p>,
                          table: ({ children }) => (
                            <div style={{ overflowX: 'auto', margin: '8px 0' }}>
                              <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>{children}</table>
                            </div>
                          ),
                          th: ({ children }) => (
                            <th style={{ border: '1px solid var(--border)', padding: '6px 10px', background: 'var(--panel-2)', textAlign: 'left', fontWeight: 600 }}>{children}</th>
                          ),
                          td: ({ children }) => (
                            <td style={{ border: '1px solid var(--border)', padding: '6px 10px' }}>{children}</td>
                          ),
                          strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
                          ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: 20 }}>{children}</ul>,
                          li: ({ children }) => <li style={{ margin: '2px 0' }}>{children}</li>,
                          code: ({ children }) => <code style={{ fontFamily: 'var(--mono)', fontSize: 11, background: 'var(--panel-2)', padding: '1px 4px', borderRadius: 3 }}>{children}</code>,
                        }}
                      >
                        {m.text}
                      </ReactMarkdown>
                  }
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
              placeholder="Ask Nexus anything…"
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
