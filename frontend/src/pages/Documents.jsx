// Documents — upload, list, and delete indexed documents
// Styled to match nexus panel/chip/button conventions

import { useState, useEffect, useRef, useCallback } from 'react'
import { Icons } from '../components/Icons'

const BUSINESSES = {
  cafe:  'Café & Restaurant',
  hotel: 'Airport Hotel',
  gems:  'Gem & Jewellery',
}

const ACCEPT = '.pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.md'

export function Documents({ businessKey }) {
  const [docs,     setDocs]     = useState([])
  const [loading,  setLoading]  = useState(false)
  const [uploading,setUploading]= useState(false)
  const [toast,    setToast]    = useState(null)
  const [dragging, setDragging] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const fileRef = useRef(null)

  const showToast = (msg, ok = true) => {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 3200)
  }

  const fetchDocs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/documents?business_key=${businessKey}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setDocs(data.documents || [])
    } catch {
      showToast('Failed to load documents', false)
    } finally {
      setLoading(false)
    }
  }, [businessKey])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  const upload = async (files) => {
    if (!files?.length) return
    setUploading(true)
    const form = new FormData()
    Array.from(files).forEach(f => form.append('files', f))
    form.append('business_key', businessKey)
    try {
      const res = await fetch('/api/documents/upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      showToast(`${data.uploaded ?? files.length} file(s) indexed`)
      fetchDocs()
    } catch (e) {
      showToast(e.message || 'Upload failed', false)
    } finally {
      setUploading(false)
    }
  }

  const deleteDoc = async (docId) => {
    setDeleting(docId)
    try {
      const res = await fetch(`/api/documents/${docId}?business_key=${businessKey}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      showToast('Document deleted')
      fetchDocs()
    } catch {
      showToast('Delete failed', false)
    } finally {
      setDeleting(null)
    }
  }

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false)
    upload(e.dataTransfer.files)
  }

  const bizLabel = BUSINESSES[businessKey] || businessKey

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860 }}>

      {/* Stats row */}
      <div className="panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 24 }}>
        <div>
          <div className="label">Indexed documents</div>
          <div className="num-md" style={{ marginTop: 2 }}>{docs.length}</div>
        </div>
        <div style={{ width: 1, alignSelf: 'stretch', background: 'var(--border)' }} />
        <div>
          <div className="label">Knowledge base</div>
          <div style={{ marginTop: 2, fontSize: 13, fontWeight: 500 }}>{bizLabel}</div>
        </div>
        <div style={{ flex: 1 }} />
        <button className="btn primary" onClick={() => fileRef.current?.click()} disabled={uploading}>
          <Icons.Plus size={12} />
          {uploading ? 'Uploading…' : 'Upload files'}
        </button>
        <button className="btn ghost" onClick={fetchDocs} disabled={loading}>
          <Icons.ArrowRight size={12} />Refresh
        </button>
        <input ref={fileRef} type="file" accept={ACCEPT} multiple hidden onChange={e => { upload(e.target.files); e.target.value = '' }} />
      </div>

      {/* Upload zone */}
      <div
        className="panel"
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{ padding: '32px 24px', textAlign: 'center', borderStyle: 'dashed', borderColor: dragging ? 'var(--indigo)' : 'var(--border)', background: dragging ? 'var(--indigo-soft)' : 'transparent', transition: 'border-color 0.15s, background 0.15s', cursor: 'pointer' }}
        onClick={() => fileRef.current?.click()}
      >
        <Icons.Download size={22} />
        <div style={{ marginTop: 8, fontSize: 13, fontWeight: 500, color: 'var(--text-2)' }}>Drop files here or click to browse</div>
        <div style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 4 }}>Supported: PDF · DOCX · TXT · CSV · XLSX · MD</div>
        {uploading && (
          <div style={{ marginTop: 10 }}>
            <span className="chip indigo"><span className="pulse-dot" />Processing files…</span>
          </div>
        )}
      </div>

      {/* Document list */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '20px 0', color: 'var(--text-3)', fontSize: 13 }}>
          <span className="pulse-dot" style={{ color: 'var(--indigo)' }} />Loading…
        </div>
      ) : docs.length === 0 ? (
        <div className="panel" style={{ padding: '32px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📄</div>
          <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-2)', marginBottom: 4 }}>No documents yet</div>
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Upload files to build the {bizLabel} knowledge base</div>
        </div>
      ) : (
        <div className="panel" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '10px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>Indexed files</span>
            <span className="chip" style={{ fontSize: 10 }}>{docs.length} total</span>
          </div>
          {docs.map((doc, i) => (
            <div key={doc.id || i} style={{ padding: '12px 18px', borderBottom: i < docs.length - 1 ? '1px solid var(--border)' : 'none', display: 'flex', alignItems: 'center', gap: 12 }}>
              <Icons.Doc size={14} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.name || doc.filename || doc.id}</div>
                {doc.created && (
                  <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 1 }}>Indexed {new Date(doc.created).toLocaleDateString()}</div>
                )}
              </div>
              {doc.type && <span className="chip mono" style={{ fontSize: 10 }}>{doc.type.toUpperCase()}</span>}
              <button
                className="btn ghost sm"
                style={{ color: 'var(--coral)', opacity: deleting === (doc.id || i) ? 0.5 : 1 }}
                onClick={() => deleteDoc(doc.id || i)}
                disabled={deleting === (doc.id || i)}
              >
                <Icons.X size={12} />Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Danger zone */}
      <div className="panel" style={{ borderColor: 'rgba(255,107,107,0.35)', padding: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--coral)', marginBottom: 4 }}>Danger zone</div>
        <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 10 }}>
          Clearing the index removes all vectors for <strong>{bizLabel}</strong> and cannot be undone.
        </div>
        <button className="btn sm" style={{ borderColor: 'var(--coral)', color: 'var(--coral)' }}
          onClick={() => {
            if (window.confirm(`Clear all ${bizLabel} documents? This cannot be undone.`)) {
              showToast('Index cleared', false)
              setDocs([])
            }
          }}>
          Clear index
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div className="toast" style={{ borderColor: toast.ok ? 'var(--teal)' : 'var(--coral)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            {toast.ok ? <Icons.Check size={14} /> : <Icons.X size={14} />}
            {toast.msg}
          </div>
        </div>
      )}
    </div>
  )
}
