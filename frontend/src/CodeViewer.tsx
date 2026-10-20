import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, FileCode2, LoaderCircle } from 'lucide-react'
import hljs from 'highlight.js/lib/core'
import fortran from 'highlight.js/lib/languages/fortran'
import { request } from './api'

hljs.registerLanguage('fortran', fortran)
const PAGE_SIZE = 200

export default function CodeViewer({ id, path, line }: { id: string; path: string; line: number }) {
  const [source, setSource] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)
  const selected = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    setSource(null)
    setError('')
    request<{ content: string }>(`/api/analyses/${id}/source?path=${encodeURIComponent(path)}`, {
      signal: controller.signal,
    })
      .then((result) => setSource(result.content))
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message)
      })
    return () => controller.abort()
  }, [id, path])
  useEffect(() => {
    setPage(Math.floor(Math.max(0, line - 1) / PAGE_SIZE))
  }, [path, line])
  useEffect(() => {
    selected.current?.scrollIntoView({
      block: 'nearest',
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    })
  }, [source, page, line])
  const lines = useMemo(() => {
    if (!source) return []
    const result = source.split(/\r\n|\n|\r/)
    if (result.at(-1) === '') result.pop()
    return result
  }, [source])
  const start = page * PAGE_SIZE
  const visible = useMemo(
    () =>
      lines.slice(start, start + PAGE_SIZE).map((text) => ({
        html: hljs.highlight(text.slice(0, 1500), { language: 'fortran' }).value,
        truncated: text.length > 1500,
      })),
    [lines, start],
  )
  if (error)
    return (
      <div className="empty-panel" role="alert">
        {error}
      </div>
    )
  if (source === null)
    return (
      <div className="empty-panel">
        <LoaderCircle className="spin" /> Cargando código…
      </div>
    )
  return (
    <section className="code-panel" aria-label="Código fuente">
      <div className="code-toolbar">
        <span>
          <FileCode2 size={15} />
          {path.split('/').pop()}
        </span>
        <span>Fortran · UTF-8 · solo lectura</span>
      </div>
      <div className="code-scroll">
        {visible.map((item, index) => {
          const number = start + index + 1
          return (
            <div
              key={number}
              ref={number === line ? selected : undefined}
              className={`code-line ${number === line ? 'focused-line' : ''}`}
            >
              <span className="line-number">{number}</span>
              <code dangerouslySetInnerHTML={{ __html: item.html || ' ' }} />
              {item.truncated && <span className="muted"> … línea truncada en el visor</span>}
            </div>
          )
        })}
      </div>
      <div className="code-pagination">
        <span>
          Líneas {Math.min(start + 1, lines.length)}–{Math.min(start + PAGE_SIZE, lines.length)} de{' '}
          {lines.length}
        </span>
        <div>
          <button
            className="icon-button"
            aria-label="Líneas anteriores"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            className="icon-button"
            aria-label="Líneas siguientes"
            disabled={start + PAGE_SIZE >= lines.length}
            onClick={() => setPage(page + 1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </section>
  )
}
