import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Braces,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Code2,
  FileArchive,
  FileCode2,
  Files,
  Folder,
  FolderOpen,
  LayoutDashboard,
  History,
  LoaderCircle,
  Plus,
  Search,
  ShieldCheck,
  Terminal,
  Upload,
  X,
} from 'lucide-react'
import { apiUrl, ApiError, request } from './api'
import CodeViewer from './CodeViewer'
import SettingsMenu from './SettingsMenu'
import MigrationPage from './MigrationPage'
import { ProjectMap, ScopeMap, StatusRing, FindingsChart } from './DesignCharts'
import type { FileStatus, Finding, Job, Report, SourceFile } from './types'

const STATUS: Record<FileStatus, string> = {
  ok: 'Completo',
  partial: 'Parcial',
  failed: 'Fallido',
  skipped: 'Omitido',
}
const JOB_STATUS = {
  uploading: 'Subiendo proyecto',
  queued: 'En cola',
  extracting: 'Preparando archivos',
  running: 'Analizando código',
  completed: 'Análisis terminado',
  failed: 'No se pudo analizar',
  cancelled: 'Análisis cancelado',
}
const terminal = (job: Job) => ['completed', 'failed', 'cancelled'].includes(job.status)
const number = (value: number) => new Intl.NumberFormat('es-ES').format(value)

function Badge({ status }: { status: FileStatus }) {
  return (
    <span className={`badge ${status}`}>
      <i />
      {STATUS[status]}
    </span>
  )
}

function FileTree({
  files,
  selected,
  onSelect,
  prefix = '',
}: {
  files: SourceFile[]
  selected: string
  onSelect: (file: SourceFile) => void
  prefix?: string
}) {
  const directories = [
    ...new Set(
      files
        .map((file) => file.path.slice(prefix.length).split('/'))
        .filter((parts) => parts.length > 1)
        .map((parts) => parts[0]),
    ),
  ]
  const direct = files.filter((file) => !file.path.slice(prefix.length).includes('/'))
  return (
    <>
      {directories.map((directory) => (
        <details key={directory} open>
          <summary>
            <ChevronRight size={13} />
            <Folder size={15} />
            {directory}
          </summary>
          <div className="tree-branch">
            <FileTree
              files={files.filter((file) => file.path.startsWith(`${prefix}${directory}/`))}
              prefix={`${prefix}${directory}/`}
              selected={selected}
              onSelect={onSelect}
            />
          </div>
        </details>
      ))}
      {direct.map((file) => (
        <button
          title={file.path}
          key={file.path}
          className={`tree-file ${selected === file.path ? 'selected' : ''}`}
          onClick={() => onSelect(file)}
        >
          <FileCode2 size={15} />
          <span>{file.path.slice(prefix.length)}</span>
          <i className={`status-dot ${file.status}`} />
        </button>
      ))}
    </>
  )
}

function FindingRow({ finding, onClick }: { finding: Finding; onClick: () => void }) {
  return (
    <button className="finding-row" onClick={onClick}>
      <span className={`finding-icon ${finding.severity}`}>
        <CircleAlert size={17} />
      </span>
      <span className="finding-copy">
        <span className="finding-rule">
          {finding.rule}{' '}
          <span>
            {finding.severity === 'info'
              ? 'Observación'
              : finding.severity === 'error'
                ? 'Error'
                : 'Revisar'}
          </span>
        </span>
        <span>{finding.message}</span>
        <small>
          {finding.path} <b>:</b> {finding.line}
        </small>
      </span>
      <ArrowUpRight size={16} />
    </button>
  )
}

export default function App() {
  const [job, setJob] = useState<Job | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [tab, setTab] = useState<'overview' | 'explorer' | 'migration'>('overview')
  const [selected, setSelected] = useState<SourceFile | null>(null)
  const [line, setLine] = useState(0)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [severity, setSeverity] = useState('all')
  const [scopeTab, setScopeTab] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)
  const [form, setForm] = useState('auto')
  const [persistent, setPersistent] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [tab])

  useEffect(() => {
    const controller = new AbortController()
    request<{ persistent: boolean }>('/api/config', { signal: controller.signal })
      .then((result) => setPersistent(result.persistent))
      .catch(() => {
        /* Storage mode is informational; analysis errors have their own UI. */
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const identifier = sessionStorage.getItem('fortran-analysis')
    const controller = new AbortController()
    if (identifier)
      request<Job>(`/api/analyses/${identifier}`, { signal: controller.signal })
        .then(setJob)
        .catch(() => {
          if (!controller.signal.aborted) sessionStorage.removeItem('fortran-analysis')
        })
    return () => controller.abort()
  }, [])
  useEffect(() => {
    if (job) sessionStorage.setItem('fortran-analysis', job.id)
  }, [job?.id])

  useEffect(() => {
    if (!job || (terminal(job) && job.status !== 'completed') || report) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const next = await request<Job>(`/api/analyses/${job.id}`, { signal: controller.signal })
        if (next.status === 'completed') {
          const result = await request<Report>(`/api/analyses/${job.id}/report`, {
            signal: controller.signal,
          })
          setReport(result)
          setSelected(result.files[0] ?? null)
        }
        setJob(next)
        setError('')
        if (!terminal(next)) timer = setTimeout(poll, 650)
      } catch (error) {
        if (!controller.signal.aborted) {
          setError((error as Error).message)
          if (error instanceof ApiError && error.status === 404) {
            setJob(null)
            sessionStorage.removeItem('fortran-analysis')
          } else timer = setTimeout(poll, 2500)
        }
      }
    }
    timer = setTimeout(poll, 300)
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [job?.id, job?.status, !!report])

  async function upload(file: Blob, name: string) {
    if (file.size > 10_000_000) {
      setError('El ZIP debe ocupar como máximo 10 MB.')
      return
    }
    setBusy(true)
    setError('')
    try {
      if (job) await request(`/api/analyses/${job.id}`, { method: 'DELETE' })
      setJob(null)
      setReport(null)
      setSelected(null)
      setLine(0)
      setTab('overview')
      const next = await request<Job>(
        `/api/analyses?name=${encodeURIComponent(name)}&source_form=${form}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/zip' },
          body: file,
        },
      )
      setJob(next)
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }
  async function demo() {
    setBusy(true)
    setError('')
    try {
      const response = await fetch(apiUrl('/api/example'))
      if (!response.ok) throw new Error('No se pudo cargar el proyecto de ejemplo.')
      await upload(await response.blob(), 'Proyecto de ejemplo')
    } catch (error) {
      setError((error as Error).message)
      setBusy(false)
    }
  }
  function choose(file?: File) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Selecciona un proyecto en formato ZIP.')
      return
    }
    void upload(file, file.name.replace(/\.zip$/i, '').slice(0, 120) || 'Proyecto')
  }
  function drop(event: DragEvent) {
    event.preventDefault()
    setDrag(false)
    if (!busy) choose(event.dataTransfer.files[0])
  }
  function open(file: SourceFile, targetLine = 0) {
    setSelected(file)
    setLine(targetLine)
    setScopeTab(false)
    setTab('explorer')
  }
  function openFinding(finding: Finding) {
    const file = report?.files.find((file) => file.path === finding.path)
    if (file) open(file, finding.line)
  }

  const running = busy || (job && !terminal(job))
  const findings = report?.files.flatMap((file) => file.findings) ?? []
  const visibleFindings = findings.filter((f) => severity === 'all' || f.severity === severity)
  const filteredFiles =
    report?.files.filter(
      (file) =>
        file.path.toLowerCase().includes(search.toLowerCase()) &&
        (filter === 'all' || file.status === filter),
    ) ?? []
  const coverage = report ? Math.round((report.summary.ok / report.summary.files) * 100) : 0
  const lines = report?.files.reduce((sum, file) => sum + (file.physical_lines ?? 0), 0) ?? 0
  const routines =
    report?.files.reduce(
      (sum, file) => sum + (file.metrics?.functions ?? 0) + (file.metrics?.subroutines ?? 0),
      0,
    ) ?? 0
  const chartFiles = [...(report?.files ?? [])]
    .sort((a, b) => (b.physical_lines ?? 0) - (a.physical_lines ?? 0))
    .slice(0, 6)
  const maxLines = Math.max(1, ...chartFiles.map((file) => file.physical_lines ?? 0))

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="FortranAnalyser, inicio">
          <span className="brand-mark">
            F<span>_</span>
          </span>
          <span>
            Fortran<span>Analyser</span>
          </span>
        </a>
        <div className="workspace-label">TU ESPACIO DE CÓDIGO</div>
        <nav aria-label="Navegación principal">
          <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>
            <LayoutDashboard size={18} />
            Resumen
            <ChevronRight size={14} />
          </button>
          <button
            className={tab === 'explorer' ? 'active' : ''}
            onClick={() => setTab('explorer')}
            disabled={!report}
          >
            <FolderOpen size={18} />
            Explorador{report && <span className="nav-count">{report.summary.files}</span>}
          </button>
          <button
            className={tab === 'migration' ? 'active' : ''}
            onClick={() => setTab('migration')}
            title="La migración"
          >
            <History size={18} />
            La migración
          </button>
        </nav>
        <div className="sidebar-note">
          <div className="orbital">
            <Braces size={25} />
          </div>
          <h3>El código tiene historia.</h3>
          <p>
            Entiende su estructura.
            <br />
            Encuentra el siguiente paso.
          </p>
          <span>FORTRAN, CON PERSPECTIVA</span>
        </div>
        <div className="sidebar-footer">
          <span className="connection-dot" />
          Análisis local<span>v0.2</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span>
            Proyecto <ChevronRight size={14} />{' '}
            <b>
              {tab === 'migration'
                ? 'La migración'
                : tab === 'overview'
                  ? 'Resumen del proyecto'
                  : 'Explorador de código'}
            </b>
          </span>
          <div className="topbar-actions">
            <span className="private-label">
              <ShieldCheck size={15} /> Tu código se queda aquí
            </span>
            <SettingsMenu />
          </div>
        </header>
        <main>
          {tab === 'migration' ? (
            <MigrationPage />
          ) : (
            <div className="analysis-view" key={tab}>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">ANÁLISIS ESTÁTICO DE FORTRAN</div>
                  <h1>{report ? job?.name : 'Una nueva mirada a tu código.'}</h1>
                  <p>
                    {report
                      ? `${number(lines)} líneas · ${report.summary.files} archivos · ${report.parser}`
                      : 'De código heredado a decisiones claras. Explora, comprende y mejora.'}
                  </p>
                </div>
                {report && (
                  <div className="heading-actions">
                    <a
                      className="button secondary"
                      href={apiUrl(`/api/analyses/${job?.id}/report?download=true`)}
                    >
                      <ArrowDownToLine size={16} />
                      Exportar JSON
                    </a>
                    <button
                      className="button primary"
                      disabled={!!running}
                      onClick={() => input.current?.click()}
                    >
                      <Plus size={17} />
                      Nuevo análisis
                    </button>
                  </div>
                )}
              </div>
              <input
                ref={input}
                className="visually-hidden"
                type="file"
                accept=".zip,application/zip"
                aria-label="Seleccionar proyecto ZIP"
                onChange={(e: ChangeEvent<HTMLInputElement>) => choose(e.target.files?.[0])}
              />
              {error && (
                <div className="error-banner" role="alert">
                  <CircleAlert size={18} />
                  <span>{error}</span>
                  <button aria-label="Cerrar error" onClick={() => setError('')}>
                    <X size={16} />
                  </button>
                </div>
              )}

              {!report && !running && (
                <>
                  <section className="welcome-card">
                    <div className="welcome-content">
                      <span className="pill">
                        <span />
                        Una herramienta para entender
                      </span>
                      <h2>
                        Tu proyecto.
                        <br />
                        Una visión más clara.
                      </h2>
                      <p>
                        Descubre cómo se organiza tu código Fortran y qué merece una segunda mirada,
                        con hallazgos que puedes comprobar.
                      </p>
                      <div className="feature-pills">
                        <span>
                          <Check size={14} />
                          Métricas por rutina
                        </span>
                        <span>
                          <Check size={14} />
                          Hallazgos con contexto
                        </span>
                      </div>
                      <button className="text-button" onClick={demo}>
                        Explorar un ejemplo <ArrowRight size={16} />
                      </button>
                    </div>
                    <div
                      className={`upload-zone ${drag ? 'dragging' : ''}`}
                      onDragOver={(event) => {
                        event.preventDefault()
                        setDrag(true)
                      }}
                      onDragLeave={() => setDrag(false)}
                      onDrop={drop}
                    >
                      <span className="upload-icon">
                        <Upload size={27} />
                      </span>
                      <h3>Empieza con tu proyecto</h3>
                      <p>
                        Arrastra un archivo ZIP aquí
                        <br />o selecciónalo en tu equipo.
                      </p>
                      <button className="button primary" onClick={() => input.current?.click()}>
                        <Plus size={16} />
                        Seleccionar ZIP
                      </button>
                      <label className="form-select">
                        Formato de código
                        <select
                          aria-label="Formato del código"
                          value={form}
                          onChange={(event) => setForm(event.target.value)}
                        >
                          <option value="auto">Automático por extensión</option>
                          <option value="free">Formato libre</option>
                          <option value="fixed">Formato fijo</option>
                        </select>
                        <ChevronDown size={13} />
                      </label>
                      <small>Hasta 10 MB · 100 archivos Fortran</small>
                    </div>
                  </section>
                  <div className="intro-grid">
                    <article>
                      <span className="intro-icon">
                        <Files size={21} />
                      </span>
                      <h3>Conoce la estructura</h3>
                      <p>Archivos, módulos y rutinas. Un mapa de lo que tienes entre manos.</p>
                    </article>
                    <article>
                      <span className="intro-icon">
                        <CircleAlert size={21} />
                      </span>
                      <h3>Revisa con criterio</h3>
                      <p>
                        Observaciones explicadas sobre el código, sin notas de calidad arbitrarias.
                      </p>
                    </article>
                    <article>
                      <span className="intro-icon">
                        <Code2 size={21} />
                      </span>
                      <h3>Ve al origen</h3>
                      <p>Abre cada hallazgo justo en la línea que necesita tu atención.</p>
                    </article>
                  </div>
                </>
              )}

              {running && (
                <section className="processing" role="status">
                  <div className="processing-icon">
                    <LoaderCircle size={32} className="spin" />
                  </div>
                  <span className="eyebrow">UN MOMENTO, ESTAMOS EXPLORANDO</span>
                  <h2>{busy ? 'Preparando tu proyecto' : JOB_STATUS[job!.status]}</h2>
                  <p>
                    {job?.total
                      ? `${job.processed} de ${job.total} archivos procesados`
                      : 'Leemos la estructura del proyecto sin ejecutar tu código.'}
                  </p>
                  <progress max={job?.total || 1} value={job?.processed || 0} />
                  <small>Puedes seguir utilizando la interfaz mientras se analiza.</small>
                  {job && (
                    <button
                      className="button secondary"
                      onClick={() => {
                        void request(`/api/analyses/${job.id}`, { method: 'DELETE' }).catch((e) =>
                          setError(e.message),
                        )
                      }}
                    >
                      Cancelar análisis
                    </button>
                  )}
                </section>
              )}
              {!running && job?.status === 'failed' && (
                <div className="error-banner" role="alert">
                  <CircleAlert size={18} />
                  {job.error}
                </div>
              )}
              {!running && job?.status === 'cancelled' && (
                <div className="notice">Análisis cancelado. Puedes seleccionar otro proyecto.</div>
              )}

              {report && !running && (
                <>
                  <section className="stats-grid">
                    <article className="stat-card">
                      <div>
                        <span>Archivos del proyecto</span>
                        <Files size={18} />
                      </div>
                      <strong>{number(report.summary.files)}</strong>
                      <small>{number(lines)} líneas de código fuente</small>
                    </article>
                    <article className="stat-card">
                      <div>
                        <span>Rutinas identificadas</span>
                        <Braces size={18} />
                      </div>
                      <strong>{number(routines)}</strong>
                      <small>Funciones y subrutinas interpretadas</small>
                    </article>
                    <article className="stat-card">
                      <div>
                        <span>Hallazgos para revisar</span>
                        <CircleAlert size={18} />
                      </div>
                      <strong>
                        {findings.length}
                        <i className="stat-tag">
                          {findings.filter((f) => f.severity === 'error').length
                            ? 'Con errores'
                            : 'Con contexto'}
                        </i>
                      </strong>
                      <small>
                        {findings.filter((f) => f.severity === 'warning').length} avisos ·{' '}
                        {findings.filter((f) => f.severity === 'info').length} observaciones
                      </small>
                    </article>
                    <article className="stat-card">
                      <div>
                        <span>Cobertura del análisis</span>
                        <CheckCheck size={18} />
                      </div>
                      <strong>
                        {coverage}
                        <em>%</em>
                      </strong>
                      <small>
                        {report.summary.ok} de {report.summary.files} archivos completos
                      </small>
                    </article>
                  </section>
                  <div className="content-tabs">
                    <button
                      className={tab === 'overview' ? 'selected' : ''}
                      onClick={() => setTab('overview')}
                    >
                      <LayoutDashboard size={16} />
                      Resumen
                    </button>
                    <button
                      className={tab === 'explorer' ? 'selected' : ''}
                      onClick={() => setTab('explorer')}
                    >
                      <Code2 size={16} />
                      Explorador de código
                    </button>
                    <span>
                      <span className="status-dot ok" />
                      Análisis terminado
                    </span>
                  </div>
                  {tab === 'overview' ? (
                    <>
                      <div className="overview-grid">
                        <section className="panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Dentro del proyecto</h2>
                              <p>Los archivos con más líneas de código fuente</p>
                            </div>
                            <span className="subtle-icon">
                              <Activity size={19} />
                            </span>
                          </div>
                          <div className="file-chart">
                            {chartFiles.map((file) => (
                              <button key={file.path} onClick={() => open(file)}>
                                <span title={file.path}>
                                  <FileCode2 size={15} />
                                  {file.path.split('/').pop()}
                                </span>
                                <div className="bar-track">
                                  <i
                                    style={{
                                      width: `${((file.physical_lines ?? 0) / maxLines) * 100}%`,
                                    }}
                                  />
                                </div>
                                <b>{number(file.physical_lines ?? 0)}</b>
                              </button>
                            ))}
                          </div>
                          <button className="panel-link" onClick={() => setTab('explorer')}>
                            Explorar todos los archivos <ArrowRight size={15} />
                          </button>
                        </section>
                        <section className="panel coverage-panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Una lectura transparente</h2>
                              <p>Qué hemos podido interpretar</p>
                            </div>
                          </div>
                          <StatusRing report={report} />
                          <div className="coverage-track">
                            {(['ok', 'partial', 'failed', 'skipped'] as FileStatus[]).map(
                              (status) => (
                                <i
                                  key={status}
                                  className={status}
                                  style={{
                                    width: `${(report.summary[status] / report.summary.files) * 100}%`,
                                  }}
                                />
                              ),
                            )}
                          </div>
                          <div className="coverage-legend">
                            {(['ok', 'partial', 'failed', 'skipped'] as FileStatus[]).map(
                              (status) => (
                                <span key={status}>
                                  <i className={`status-dot ${status}`} />
                                  {STATUS[status]}
                                  <b>{report.summary[status]}</b>
                                </span>
                              ),
                            )}
                          </div>
                          {coverage < 100 && (
                            <p className="coverage-note">
                              Los archivos parciales o fallidos no aportan métricas de rutinas. Sus
                              límites están en los hallazgos.
                            </p>
                          )}
                        </section>
                      </div>
                      <FindingsChart
                        findings={findings}
                        selected={severity}
                        onSelect={setSeverity}
                      />
                      <section className="panel findings-panel">
                        <div className="panel-heading">
                          <div>
                            <h2>
                              El siguiente paso está en los detalles{' '}
                              <span className="count-label">{findings.length}</span>
                            </h2>
                            <p>Observaciones para investigar, con su ubicación en el código</p>
                          </div>
                          <select
                            aria-label="Filtrar gravedad"
                            value={severity}
                            onChange={(event) => setSeverity(event.target.value)}
                          >
                            <option value="all">Todas las gravedades</option>
                            <option value="warning">Avisos</option>
                            <option value="info">Observaciones</option>
                            <option value="error">Errores</option>
                          </select>
                        </div>
                        {visibleFindings.length ? (
                          visibleFindings.map((finding, index) => (
                            <FindingRow
                              key={index}
                              finding={finding}
                              onClick={() => openFinding(finding)}
                            />
                          ))
                        ) : (
                          <div className="no-findings">
                            <CheckCheck size={23} />
                            <b>
                              {findings.length
                                ? 'Sin hallazgos con este filtro'
                                : 'Sin hallazgos en las reglas actuales'}
                            </b>
                            <p>
                              El análisis es sintáctico. Esto no valida la corrección científica del
                              modelo.
                            </p>
                          </div>
                        )}
                      </section>
                    </>
                  ) : (
                    <>
                      <ProjectMap
                        files={report.files}
                        selected={selected?.path ?? ''}
                        onSelect={open}
                      />
                      <div className="explorer-layout">
                        <section className="panel file-browser">
                          <div className="panel-heading">
                            <h2>
                              Archivos <span className="count-label">{filteredFiles.length}</span>
                            </h2>
                          </div>
                          <label className="search-box">
                            <Search size={15} />
                            <input
                              aria-label="Buscar archivos"
                              placeholder="Buscar archivo…"
                              value={search}
                              onChange={(event) => setSearch(event.target.value)}
                            />
                          </label>
                          <select
                            className="file-filter"
                            aria-label="Filtrar estado"
                            value={filter}
                            onChange={(event) => setFilter(event.target.value)}
                          >
                            <option value="all">Todos los estados</option>
                            {Object.entries(STATUS).map(([value, label]) => (
                              <option key={value} value={value}>
                                {label}
                              </option>
                            ))}
                          </select>
                          <div className="file-tree">
                            <FileTree
                              files={filteredFiles}
                              selected={selected?.path ?? ''}
                              onSelect={(file) => open(file)}
                            />
                            {!filteredFiles.length && (
                              <p className="muted">Sin archivos con este filtro.</p>
                            )}
                          </div>
                        </section>
                        <div className="file-detail">
                          {selected && job ? (
                            <>
                              <div className="file-detail-heading">
                                <span>
                                  <FileCode2 size={18} />
                                  <b>{selected.path}</b>
                                </span>
                                <Badge status={selected.status} />
                              </div>
                              <div className="file-mini-stats">
                                <span>
                                  <b>{selected.physical_lines ?? '—'}</b> líneas
                                </span>
                                <span>
                                  <b>{selected.metrics?.declared_entities ?? '—'}</b> entidades
                                  declaradas
                                </span>
                                <span>
                                  <b>{selected.metrics?.max_loop_depth ?? '—'}</b> profundidad de
                                  bucles
                                </span>
                                <span>
                                  {selected.source_form === 'free'
                                    ? 'Formato libre'
                                    : 'Formato fijo'}
                                </span>
                              </div>
                              <ScopeMap
                                file={selected}
                                onSelect={(target) => {
                                  setLine(target)
                                  setScopeTab(false)
                                }}
                              />
                              <div className="detail-tabs">
                                <button
                                  className={!scopeTab ? 'selected' : ''}
                                  onClick={() => setScopeTab(false)}
                                >
                                  Código fuente
                                </button>
                                <button
                                  className={scopeTab ? 'selected' : ''}
                                  onClick={() => setScopeTab(true)}
                                >
                                  Ámbitos y rutinas <span>{selected.scopes.length}</span>
                                </button>
                              </div>
                              {!scopeTab ? (
                                <CodeViewer id={job.id} path={selected.path} line={line} />
                              ) : (
                                <div className="scopes-panel">
                                  {selected.scopes.map((scope) => (
                                    <button
                                      key={`${scope.line}-${scope.qualified_name}`}
                                      onClick={() => {
                                        setLine(scope.line)
                                        setScopeTab(false)
                                      }}
                                    >
                                      <span>
                                        <Braces size={17} />
                                        <b>{scope.qualified_name}</b>
                                        <small>
                                          {scope.kind} · líneas {scope.line}–{scope.end_line}
                                        </small>
                                      </span>
                                      <span>
                                        {scope.declared_entities} entidades · {scope.loops} bucles
                                        <ArrowUpRight size={15} />
                                      </span>
                                    </button>
                                  ))}
                                  {!selected.scopes.length && (
                                    <div className="empty-panel">
                                      No hay ámbitos disponibles para este archivo.
                                    </div>
                                  )}
                                </div>
                              )}
                              <section className="panel file-findings">
                                <div className="panel-heading">
                                  <h2>
                                    Hallazgos en este archivo{' '}
                                    <span className="count-label">{selected.findings.length}</span>
                                  </h2>
                                </div>
                                {selected.findings.length ? (
                                  selected.findings.map((finding, index) => (
                                    <FindingRow
                                      key={index}
                                      finding={finding}
                                      onClick={() => {
                                        setLine(finding.line)
                                        setScopeTab(false)
                                      }}
                                    />
                                  ))
                                ) : (
                                  <p className="quiet-success">
                                    <Check size={16} />
                                    Sin hallazgos en las reglas actuales.
                                  </p>
                                )}
                              </section>
                            </>
                          ) : (
                            <div className="empty-panel">
                              Selecciona un archivo para explorar su código.
                            </div>
                          )}
                        </div>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          )}
          <footer className="page-footer">
            <span>
              <Terminal size={14} />
              FortranAnalyser <span>·</span> Código con contexto.
            </span>
            <span>
              {persistent ? 'Resultados conservados' : 'Sesión temporal'} · Sin ejecución de modelos
            </span>
          </footer>
        </main>
      </div>
    </div>
  )
}
