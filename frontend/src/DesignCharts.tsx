import { useState } from 'react'
import type { CSSProperties } from 'react'
import { ArrowUpRight, ChartNoAxesCombined, Layers, Map, ScanLine } from 'lucide-react'
import type { Finding, Report, SourceFile } from './types'

const format = (n: number) => new Intl.NumberFormat('es-ES').format(n)
const states = [
  { key: 'ok', label: 'Completo', color: '#109b87' },
  { key: 'partial', label: 'Parcial', color: '#e2a13b' },
  { key: 'failed', label: 'Fallido', color: '#df6378' },
  { key: 'skipped', label: 'Omitido', color: '#a0aec0' },
] as const

export function StatusRing({ report }: { report: Report }) {
  let offset = 0
  const stops = states.map(({ key, color }) => {
    const start = offset
    offset += report.summary.files ? (report.summary[key] / report.summary.files) * 100 : 0
    return `${color} ${start}% ${offset}%`
  })
  const complete = report.summary.files
    ? Math.round((report.summary.ok / report.summary.files) * 100)
    : 0
  return (
    <div className="ring-layout">
      <div
        className="status-ring"
        style={{ background: `conic-gradient(${stops.join(',')})` }}
        role="img"
        aria-label={`${complete}% de archivos completos. ${states.map((s) => `${report.summary[s.key]} ${s.label.toLowerCase()}`).join(', ')}`}
      >
        <div>
          <strong>
            {complete}
            <span>%</span>
          </strong>
          <small>completo</small>
        </div>
      </div>
      <div className="ring-caption">
        <ScanLine size={22} />
        <b>Lectura del proyecto</b>
        <p>Archivos interpretados por completo, sin ocultar los límites del parser.</p>
      </div>
    </div>
  )
}

export function FindingsChart({
  findings,
  selected,
  onSelect,
}: {
  findings: Finding[]
  selected: string
  onSelect: (severity: string) => void
}) {
  const categories = [
    { key: 'error', label: 'Errores', color: '#df6378' },
    { key: 'warning', label: 'Avisos', color: '#d49a35' },
    { key: 'info', label: 'Observaciones', color: '#577dec' },
  ].map((item) => ({ ...item, count: findings.filter((f) => f.severity === item.key).length }))
  const max = Math.max(1, ...categories.map((item) => item.count))
  return (
    <section className="panel findings-distribution">
      <div className="panel-heading">
        <div>
          <h2>Señales del análisis</h2>
          <p>Selecciona una gravedad para filtrar los hallazgos de abajo.</p>
        </div>
        <ChartNoAxesCombined size={21} />
      </div>
      <div className="severity-bars">
        {categories.map((item) => (
          <button
            key={item.key}
            aria-pressed={selected === item.key}
            onClick={() => onSelect(selected === item.key ? 'all' : item.key)}
          >
            <span className="severity-label">
              <i style={{ background: item.color }} />
              {item.label}
              <b>{format(item.count)}</b>
            </span>
            <span className="severity-track">
              <i style={{ width: `${(item.count / max) * 100}%`, background: item.color }} />
            </span>
          </button>
        ))}
      </div>
      {!findings.length && (
        <p className="chart-note">No se han encontrado hallazgos con las reglas actuales.</p>
      )}
    </section>
  )
}

export function ProjectMap({
  files,
  selected,
  onSelect,
}: {
  files: SourceFile[]
  selected: string
  onSelect: (file: SourceFile) => void
}) {
  const [metric, setMetric] = useState<'lines' | 'findings'>('lines')
  const value = (file: SourceFile) =>
    metric === 'lines' ? (file.physical_lines ?? 0) : file.findings.length
  const max = Math.max(1, ...files.map(value))
  const sorted = [...files].sort((a, b) => value(b) - value(a) || a.path.localeCompare(b.path))
  return (
    <section className="panel project-map">
      <div className="panel-heading">
        <div>
          <span className="chart-eyebrow">
            <Map size={14} /> VISTA DEL PROYECTO
          </span>
          <h2>Un mapa para empezar a explorar</h2>
          <p>
            Cada bloque es un archivo. La barra compara{' '}
            {metric === 'lines' ? 'sus líneas' : 'sus hallazgos'} con el mayor valor del proyecto.
          </p>
        </div>
        <div className="chart-toggle" role="group" aria-label="Métrica del mapa">
          <button aria-pressed={metric === 'lines'} onClick={() => setMetric('lines')}>
            Líneas
          </button>
          <button aria-pressed={metric === 'findings'} onClick={() => setMetric('findings')}>
            Hallazgos
          </button>
        </div>
      </div>
      <div className="map-tiles">
        {sorted.map((file) => (
          <button
            key={file.path}
            className={`map-tile ${selected === file.path ? 'active' : ''}`}
            onClick={() => onSelect(file)}
            title={`${file.path} · ${states.find((s) => s.key === file.status)?.label}`}
            aria-label={`Abrir ${file.path}, ${metric === 'lines' && file.physical_lines === null ? 'Líneas no disponibles' : `${format(value(file))} ${metric === 'lines' ? 'líneas' : 'hallazgos'}`}`}
          >
            <span className="tile-top">
              <span className={`status-dot ${file.status}`} />
              <span>{file.path.split('.').pop()?.toUpperCase()}</span>
              <ArrowUpRight size={14} />
            </span>
            <b>{file.path.split('/').pop()}</b>
            <span className="tile-value">
              {metric === 'lines' && file.physical_lines === null ? '—' : format(value(file))}
              <small>{metric === 'lines' ? 'líneas' : 'hallazgos'}</small>
            </span>
            <span className="tile-track">
              <i style={{ width: `${(value(file) / max) * 100}%` }} />
            </span>
          </button>
        ))}
      </div>
      <div className="map-legend">
        {states.map((s) => (
          <span key={s.key}>
            <i className={`status-dot ${s.key}`} />
            {s.label}
          </span>
        ))}
        <span>Selecciona un archivo para ver su código</span>
      </div>
    </section>
  )
}

export function ScopeMap({
  file,
  onSelect,
}: {
  file: SourceFile
  onSelect: (line: number) => void
}) {
  const routines = file.scopes.filter((s) => ['function', 'subroutine', 'program'].includes(s.kind))
  const visible = [...routines].sort((a, b) => a.line - b.line).slice(0, 18)
  const total = Math.max(1, file.physical_lines ?? 1, ...file.scopes.map((s) => s.end_line))
  return (
    <section className="scope-map" aria-label="Mapa de rutinas del archivo">
      <div className="scope-map-heading">
        <span>
          <Layers size={16} />
          <b>Estructura del archivo</b>
        </span>
        <small>
          {visible.length
            ? `${visible.length} de ${routines.length} rutinas · pulsa para ir al código`
            : 'Sin rutinas disponibles'}
        </small>
      </div>
      {visible.length ? (
        <>
          <div className="scope-axis">
            <span>Línea 1</span>
            <span>{format(total)}</span>
          </div>
          <div className="scope-lanes">
            {visible.map((scope) => (
              <button
                key={`${scope.line}-${scope.qualified_name}`}
                onClick={() => onSelect(scope.line)}
                title={`${scope.qualified_name}: líneas ${scope.line}–${scope.end_line}, ${scope.loops} bucles`}
                aria-label={`Ir a ${scope.name}, línea ${scope.line}`}
              >
                <span className="scope-name">{scope.name}</span>
                <span className="scope-track">
                  <i
                    style={
                      {
                        '--start': `${((scope.line - 1) / total) * 100}%`,
                        '--length': `${Math.max(0.6, ((scope.end_line - scope.line + 1) / total) * 100)}%`,
                      } as CSSProperties
                    }
                  />
                </span>
                <small>{format(scope.end_line - scope.line + 1)} líneas</small>
              </button>
            ))}
          </div>
          <p className="chart-note">
            La posición y longitud indican dónde empieza y termina cada rutina. Todos los ámbitos
            están en la pestaña inferior.
          </p>
        </>
      ) : (
        <p className="chart-note">
          {file.status === 'ok'
            ? 'Este archivo no contiene programas, funciones ni subrutinas identificados.'
            : 'El análisis de este archivo no ofrece una estructura de rutinas completa.'}
        </p>
      )}
    </section>
  )
}
