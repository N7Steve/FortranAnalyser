import type { Report } from './types'

export default function StructureReport({ report }: { report: Report }) {
  const a = report.analysis
  if (!a)
    return (
      <p>Este informe anterior no tiene métricas estructurales. Analiza de nuevo el proyecto.</p>
    )
  const names = new Map(a.nodes.map((n) => [n.id, `${n.name} (${n.kind})`]))
  return (
    <section className="structure-report">
      <h2>Estructura, complejidad y calidad</h2>
      <p>
        Complejidad ciclomática {a.complete ? 'total' : 'parcial'}:{' '}
        <strong>{a.cyclomatic_complexity}</strong> · Nota orientativa:{' '}
        <strong>{a.quality_score ?? 'No disponible'}</strong>
        {a.quality_score !== null && ' / 10'}
      </p>
      <details>
        <summary>Métodos y límites</summary>
        <p>{a.method}</p>
        <p>{a.quality_method}</p>
      </details>
      <div className="structure-scroll">
        <table>
          <thead>
            <tr>
              <th>Archivo</th>
              <th>CC</th>
              <th>Nota / 10</th>
              <th>EXIT</th>
              <th>CYCLE</th>
            </tr>
          </thead>
          <tbody>
            {report.files.map((f) => (
              <tr key={f.path}>
                <td>{f.path}</td>
                <td>{f.analysis?.cyclomatic_complexity ?? 'N/D'}</td>
                <td>{f.analysis?.quality_score ?? 'N/D'}</td>
                <td>{f.analysis?.exit_count ?? 'N/D'}</td>
                <td>{f.analysis?.cycle_count ?? 'N/D'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <details open>
        <summary>Diagrama de clases y dependencias</summary>
        <p>
          Tipos derivados, módulos y rutinas. Flechas dirigidas; contains indica pertenencia, use
          importación, call llamada, type referencia a tipo y extends herencia.
        </p>
        <div className="structure-scroll">
          <svg
            role="img"
            aria-label="Grafo de dependencias Fortran"
            width="100%"
            height={Math.max(150, a.nodes.length * 75)}
            viewBox={`0 0 1000 ${Math.max(150, a.nodes.length * 75)}`}
          >
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M0,0 L8,4 L0,8 Z" fill="currentColor" />
              </marker>
            </defs>
            {a.edges
              .filter((e) => e.resolved)
              .map((e, i) => {
                const from = a.nodes.findIndex((n) => n.id === e.source)
                const to = a.nodes.findIndex((n) => n.id === e.target)
                return (
                  <g key={i}>
                    <path
                      d={`M430 ${from * 75 + 30} C${530 + (i % 6) * 55} ${from * 75 + 30},${530 + (i % 6) * 55} ${to * 75 + 30},430 ${to * 75 + 30}`}
                      fill="none"
                      stroke="currentColor"
                      markerEnd="url(#arrow)"
                    />
                    <text x={540 + (i % 6) * 55} y={(from + to) * 37.5 + 25} fontSize="12">
                      {e.kind}
                    </text>
                  </g>
                )
              })}
            {a.nodes.map((n, i) => (
              <g key={n.id}>
                <title>
                  {n.path}:{n.line}
                </title>
                <rect
                  x="10"
                  y={i * 75 + 5}
                  width="420"
                  height="55"
                  rx="5"
                  fill="var(--ui-soft)"
                  stroke="currentColor"
                />
                <text x="22" y={i * 75 + 27} fontSize="15">
                  {n.kind}: {n.name.slice(0, 40)}
                </text>
                <text x="22" y={i * 75 + 47} fontSize="12">
                  {n.path.slice(0, 55)}:{n.line}
                </text>
              </g>
            ))}
          </svg>
        </div>
        <div className="structure-scroll">
          <table>
            <thead>
              <tr>
                <th>Origen</th>
                <th>Relación</th>
                <th>Destino</th>
                <th>Línea</th>
              </tr>
            </thead>
            <tbody>
              {a.edges.map((e, i) => (
                <tr key={i}>
                  <td>{names.get(e.source)}</td>
                  <td>{e.kind}</td>
                  <td>{names.get(e.target) ?? `${e.target} (externo / no resuelto)`}</td>
                  <td>{e.line}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <details>
        <summary>Complejidad por rutina</summary>
        {report.files.map((f) => (
          <div key={f.path}>
            <h3>{f.path}</h3>
            {f.analysis?.routines.map((r) => (
              <p key={r.name}>
                {r.name}:{r.line} - CC {r.complexity}
              </p>
            )) ?? <p>Análisis no disponible.</p>}
          </div>
        ))}
      </details>
    </section>
  )
}
