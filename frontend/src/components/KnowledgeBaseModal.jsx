// KnowledgeBaseModal — pop-up for Upload / Replace / Delete operations on knowledge base collections

import { useState, useRef, useEffect } from 'react'
import { Icons } from './Icons'
import { businessConfig } from '../config'

const ACCEPT = '.pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.md'

// Default collections from business config keys
const DEFAULT_COLLECTIONS = businessConfig.business.businesses.map(b => ({
  key: b.key,
  label: b.key,
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function CollectionPicker({ collections, selected, onSelect, allowNew, newLabel, onNewLabel }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {collections.map(c => (
        <div
          key={c.key}
          onClick={() => onSelect(c.key)}
          className="clickable"
          style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
            borderRadius: 6, border: '1px solid',
            borderColor: selected === c.key ? 'var(--indigo)' : 'var(--border)',
            background: selected === c.key ? 'var(--indigo-soft)' : 'var(--panel-2)',
          }}
        >
          <Icons.Folder size={13} />
          <span style={{ flex: 1, fontSize: 13 }}>{c.label}</span>
          {selected === c.key && <Icons.Check size={13} />}
        </div>
      ))}

      {allowNew && (
        <div
          onClick={() => onSelect('__new__')}
          className="clickable"
          style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
            borderRadius: 6, border: '1px dashed',
            borderColor: selected === '__new__' ? 'var(--indigo)' : 'var(--border)',
            background: selected === '__new__' ? 'var(--indigo-soft)' : 'transparent',
          }}
        >
          <Icons.Plus size={13} />
          <span style={{ flex: 1, fontSize: 13 }}>New collection…</span>
        </div>
      )}

      {allowNew && selected === '__new__' && (
        <input
          className="input"
          autoFocus
          placeholder="Collection name"
          value={newLabel}
          onChange={e => onNewLabel(e.target.value)}
          style={{ marginTop: 2 }}
        />
      )}
    </div>
  )
}

function DocumentPicker({ collection, selected, onSelect }) {
  const [docs, setDocs] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!collection || collection === '__new__') { setDocs([]); return }
    setLoading(true)
    fetch(`http://localhost:8000/api/documents/list/${collection}`)
      .then(r => r.json())
      .then(data => setDocs(data.documents ?? []))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false))
  }, [collection])

  if (!collection) return null
  if (loading) return <div style={{ fontSize: 12, color: 'var(--text-3)', padding: '8px 0' }}>Loading documents…</div>
  if (!docs?.length) return <div style={{ fontSize: 12, color: 'var(--text-3)', padding: '8px 0' }}>No documents in this collection.</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 180, overflowY: 'auto' }}>
      {docs.map(doc => (
        <div
          key={doc.name}
          onClick={() => onSelect(doc.name === selected ? null : doc.name)}
          className="clickable"
          style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px',
            borderRadius: 6, border: '1px solid',
            borderColor: selected === doc.name ? 'var(--indigo)' : 'var(--border)',
            background: selected === doc.name ? 'var(--indigo-soft)' : 'var(--panel-2)',
            fontSize: 12,
          }}
        >
          <Icons.Doc size={12} />
          <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.name}</span>
          <span style={{ fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap' }}>{doc.chunks.toLocaleString()} chunks</span>
          {selected === doc.name && <Icons.Check size={12} />}
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Upload pane
// ---------------------------------------------------------------------------
function UploadPane({ onDone }) {
  const [collection, setCollection] = useState(DEFAULT_COLLECTIONS[0]?.key ?? '')
  const [newLabel, setNewLabel] = useState('')
  const [files, setFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef(null)

  const effectiveKey = collection === '__new__' ? newLabel.trim().toLowerCase().replace(/\s+/g, '_') : collection

  const addFiles = (incoming) => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...Array.from(incoming).filter(f => !existing.has(f.name))]
    })
  }

  const submit = async () => {
    if (!effectiveKey || !files.length) return
    setUploading(true); setError(null)
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    try {
      const res = await fetch(`http://localhost:8000/api/documents/upload/${effectiveKey}`, { method: 'POST', body: form })
      if (!res.ok) throw new Error(await res.text())
      onDone(`${files.length} file(s) uploaded to "${effectiveKey}"`)
    } catch (e) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <div className="label" style={{ marginBottom: 8 }}>Select collection</div>
        <CollectionPicker
          collections={DEFAULT_COLLECTIONS}
          selected={collection}
          onSelect={setCollection}
          allowNew
          newLabel={newLabel}
          onNewLabel={setNewLabel}
        />
      </div>

      <div>
        <div className="label" style={{ marginBottom: 8 }}>Files to upload</div>
        <div
          className="panel"
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }}
          onClick={() => fileRef.current?.click()}
          style={{
            padding: '20px 16px', textAlign: 'center', cursor: 'pointer', borderStyle: 'dashed',
            borderColor: dragging ? 'var(--indigo)' : 'var(--border)',
            background: dragging ? 'var(--indigo-soft)' : 'transparent',
          }}
        >
          <Icons.Download size={18} />
          <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 6 }}>Drop files or click to browse</div>
          <div style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 2 }}>PDF · DOCX · TXT · CSV · XLSX · MD</div>
          <input ref={fileRef} type="file" accept={ACCEPT} multiple hidden onChange={e => { addFiles(e.target.files); e.target.value = '' }} />
        </div>

        {files.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8, maxHeight: 140, overflowY: 'auto' }}>
            {files.map((f, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, padding: '4px 6px', borderRadius: 4, background: 'var(--panel-2)' }}>
                <Icons.Doc size={11} />
                <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.name}</span>
                <button className="btn ghost icon" style={{ padding: 2 }} onClick={e => { e.stopPropagation(); setFiles(prev => prev.filter((_, j) => j !== i)) }}>
                  <Icons.X size={10} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <div style={{ fontSize: 12, color: 'var(--coral)' }}>{error}</div>}

      <button
        className="btn primary"
        onClick={submit}
        disabled={uploading || !effectiveKey || !files.length}
        style={{ alignSelf: 'flex-end' }}
      >
        <Icons.Send size={12} />
        {uploading ? 'Uploading…' : 'Upload'}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Replace pane
// ---------------------------------------------------------------------------
function ReplacePane({ onDone }) {
  const [collection, setCollection] = useState('')
  const [docId, setDocId] = useState(null)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef(null)

  const submit = async () => {
    if (!collection || !docId || !file) return
    setUploading(true); setError(null)
    const form = new FormData()
    form.append('files', file)
    try {
      // Delete old then re-upload
      await fetch(`http://localhost:8000/api/documents/${docId}?business_key=${collection}`, { method: 'DELETE' })
      const res = await fetch(`http://localhost:8000/api/documents/upload/${collection}`, { method: 'POST', body: form })
      if (!res.ok) throw new Error(await res.text())
      onDone(`Document replaced in "${collection}"`)
    } catch (e) {
      setError(e.message || 'Replace failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <div className="label" style={{ marginBottom: 8 }}>Select collection</div>
        <CollectionPicker collections={DEFAULT_COLLECTIONS} selected={collection} onSelect={k => { setCollection(k); setDocId(null) }} />
      </div>

      {collection && (
        <div>
          <div className="label" style={{ marginBottom: 8 }}>Select document to replace</div>
          <DocumentPicker collection={collection} selected={docId} onSelect={setDocId} />
        </div>
      )}

      {docId && (
        <div>
          <div className="label" style={{ marginBottom: 8 }}>Replacement file</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button className="btn sm" onClick={() => fileRef.current?.click()}>
              <Icons.Plus size={11} />{file ? 'Change file' : 'Choose file'}
            </button>
            {file && <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{file.name}</span>}
            <input ref={fileRef} type="file" accept={ACCEPT} hidden onChange={e => { setFile(e.target.files[0]); e.target.value = '' }} />
          </div>
        </div>
      )}

      {error && <div style={{ fontSize: 12, color: 'var(--coral)' }}>{error}</div>}

      <button
        className="btn primary"
        onClick={submit}
        disabled={uploading || !collection || !docId || !file}
        style={{ alignSelf: 'flex-end' }}
      >
        <Icons.ArrowRight size={12} />
        {uploading ? 'Replacing…' : 'Replace'}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Delete pane
// ---------------------------------------------------------------------------
function DeletePane({ onDone }) {
  const [collection, setCollection] = useState('')
  const [docId, setDocId] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState(null)

  const submit = async () => {
    if (!collection || !docId) return
    setDeleting(true); setError(null)
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${docId}?business_key=${collection}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      onDone(`Document removed from "${collection}"`)
    } catch (e) {
      setError(e.message || 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <div className="label" style={{ marginBottom: 8 }}>Select collection</div>
        <CollectionPicker collections={DEFAULT_COLLECTIONS} selected={collection} onSelect={k => { setCollection(k); setDocId(null) }} />
      </div>

      {collection && (
        <div>
          <div className="label" style={{ marginBottom: 8 }}>Select document to delete</div>
          <DocumentPicker collection={collection} selected={docId} onSelect={setDocId} />
        </div>
      )}

      {error && <div style={{ fontSize: 12, color: 'var(--coral)' }}>{error}</div>}

      <button
        className="btn sm"
        onClick={submit}
        disabled={deleting || !collection || !docId}
        style={{ alignSelf: 'flex-end', borderColor: 'var(--coral)', color: 'var(--coral)' }}
      >
        <Icons.X size={12} />
        {deleting ? 'Deleting…' : 'Delete document'}
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Modal root
// ---------------------------------------------------------------------------
const TABS = [
  { id: 'upload',  label: 'Upload',  icon: 'Download' },
  { id: 'replace', label: 'Replace', icon: 'ArrowRight' },
  { id: 'delete',  label: 'Delete',  icon: 'X' },
]

export function KnowledgeBaseModal({ open, onClose }) {
  const [tab, setTab] = useState('upload')
  const [toast, setToast] = useState(null)

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const handleDone = (msg) => {
    showToast(msg)
    setTimeout(onClose, 1800)
  }

  if (!open) return null

  return (
    <div
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(8,10,16,0.6)', backdropFilter: 'blur(2px)', zIndex: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="panel"
        style={{ width: 520, maxWidth: '94vw', height: '560px', maxHeight: '88vh', display: 'flex', flexDirection: 'column', background: 'var(--panel)', boxShadow: '0 24px 60px rgba(0,0,0,0.5)', overflow: 'hidden' }}
      >
        {/* Header */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icons.Folder size={14} />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Knowledge Base</span>
          </div>
          <button className="btn ghost icon" onClick={onClose}><Icons.X size={12} /></button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2, padding: '8px 12px', borderBottom: '1px solid var(--border)', background: 'var(--bg-2)' }}>
          {TABS.map(t => {
            const Icon = Icons[t.icon]
            return (
              <div
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`pill-tab ${tab === t.id ? 'active' : ''}`}
                style={{ display: 'flex', alignItems: 'center', gap: 5 }}
              >
                <Icon size={11} />{t.label}
              </div>
            )
          })}
        </div>

        {/* Body */}
        <div className="scroll-y" style={{ flex: 1, padding: 18 }}>
          {tab === 'upload'  && <UploadPane  onDone={handleDone} />}
          {tab === 'replace' && <ReplacePane onDone={handleDone} />}
          {tab === 'delete'  && <DeletePane  onDone={handleDone} />}
        </div>

        {/* Toast */}
        {toast && (
          <div style={{ padding: '10px 18px', borderTop: '1px solid var(--border)', background: 'var(--teal-soft)', display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
            <Icons.Check size={13} />{toast}
          </div>
        )}
      </div>
    </div>
  )
}
