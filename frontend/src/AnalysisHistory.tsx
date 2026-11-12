import { useEffect, useState } from 'react'
import { request } from './api'
import type { Job } from './types'

const terminal = (job: Job) => ['completed', 'failed', 'cancelled'].includes(job.status)
const labels: Record<Job['status'], string> = {
  uploading: 'Cargando',
  queued: 'En cola',
  extracting: 'Descomprimiendo',
  running: 'Analizando',
  completed: 'Terminado',
  failed: 'Fallido',
  cancelled: 'Cancelado',
}

export default function AnalysisHistory({
  refreshKey,
  onOpen,
  onRemoved,
}: {
  refreshKey: string
  onOpen: (job: Job) => void
  onRemoved: (id: string) => void
}) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    async function load() {
      try {
        const next = await request<Job[]>('/api/analyses', { signal: controller.signal })
        if (controller.signal.aborted) return
        setJobs(next)
        setError('')
        if (next.some((j) => !terminal(j))) timer = setTimeout(load, 1500)
      } catch (e) {
        if (!controller.signal.aborted) setError((e as Error).message)
      }
    }
    void load()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [refreshKey, revision])

  async function remove(job: Job) {
    setPending(true)
    setError('')
    try {
      const result = await request<{ deleted: boolean }>(`/api/analyses/${job.id}`, {
        method: 'DELETE',
      })
      if (result.deleted) onRemoved(job.id)
      setRevision((n) => n + 1)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setPending(false)
    }
  }

  return (
    <details className="analysis-history">
      <summary>Análisis del servidor ({jobs.length})</summary>
      <p>
        Los análisis se guardan en el servidor. No hay cuotas de cantidad de trabajos o informes.
        Eliminar un análisis borra su informe y sus fuentes.
      </p>
      <button
        className="button secondary"
        disabled={pending}
        onClick={() => setRevision((n) => n + 1)}
      >
        Actualizar lista
      </button>
      {error && <p role="alert">{error}</p>}
      {!jobs.length && !error && <p>No hay análisis guardados.</p>}
      <ul>
        {jobs.map((job) => (
          <li key={job.id}>
            <span>
              <strong>{job.name}</strong> · {labels[job.status]}
              {job.error && <small> · {job.error}</small>}
            </span>
            <div>
              <button className="button secondary" disabled={pending} onClick={() => onOpen(job)}>
                {job.status === 'completed' ? 'Abrir informe' : 'Ver estado'}
              </button>
              <button
                className="button secondary"
                disabled={pending}
                onClick={() => void remove(job)}
              >
                {terminal(job) ? 'Eliminar análisis' : 'Cancelar análisis'}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </details>
  )
}
