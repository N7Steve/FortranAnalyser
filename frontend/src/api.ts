export const apiUrl = (path: string) =>
  `${import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''}${path}`

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
  }
}

export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(url), options)
  if (!response.ok) {
    let message = `No se pudo completar la petición (${response.status}).`
    try {
      const error = await response.json()
      if (typeof error.detail === 'string') message = error.detail
    } catch {
      /* Keep the actionable HTTP error for non-JSON proxy failures. */
    }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

function uploadBlock<T>(
  url: string,
  file: Blob,
  onProgress: (loaded: number, total: number) => void,
  signal: AbortSignal,
  method = 'POST',
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const abort = () => xhr.abort()
    signal.addEventListener('abort', abort, { once: true })
    const cleanup = () => signal.removeEventListener('abort', abort)
    xhr.open(method, apiUrl(url))
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    xhr.upload.onprogress = (e) => onProgress(e.loaded, e.lengthComputable ? e.total : file.size)
    xhr.onload = () => {
      cleanup()
      let body
      try {
        body = JSON.parse(xhr.responseText)
      } catch {
        /* Proxy errors may be HTML. */
      }
      if (xhr.status >= 200 && xhr.status < 300 && body) resolve(body as T)
      else
        reject(
          new ApiError(
            typeof body?.detail === 'string'
              ? xhr.status === 413
                ? `${body.detail} Esta web no impone un límite de tamaño. Comprueba que la API esté reconstruida y que el proxy permita ese tamaño.`
                : body.detail
              : xhr.status === 413
                ? 'HTTP 413 sin detalle de la API: el servidor HTTP o un proxy ha rechazado el tamaño. Prueba el acceso directo al puerto 8890 y revisa el límite del proxy.'
                : `No se pudo subir el archivo (${xhr.status}).`,
            xhr.status,
          ),
        )
    }
    xhr.onerror = () => {
      cleanup()
      reject(new Error('Se perdió la conexión durante la subida.'))
    }
    xhr.onabort = () => {
      cleanup()
      reject(new Error('Subida cancelada.'))
    }
    if (signal.aborted) {
      cleanup()
      reject(new Error('Subida cancelada.'))
      return
    }
    xhr.send(file)
  })
}

export async function uploadArchive<T>(
  url: string,
  file: Blob,
  onProgress: (loaded: number, total: number) => void,
  signal: AbortSignal,
): Promise<T> {
  const query = url.split('?')[1] || ''
  const config = await request<{ upload_chunk_bytes?: number }>('/api/config', { signal })
  if (!config.upload_chunk_bytes)
    throw new Error(
      'La API desplegada no admite la subida por bloques. Reconstruye y recrea el contenedor con la última versión para subir a través de Cloudflare.',
    )
  const size = Math.min(config.upload_chunk_bytes, 8 * 1024 ** 2)
  if (size <= 0 || !Number.isFinite(size)) throw new Error('Tamaño de bloque inválido en la API.')
  const job = await request<{ id: string }>(`/api/uploads?${query}`, { method: 'POST', signal })
  try {
    for (let offset = 0; offset < file.size; offset += size) {
      await uploadBlock(
        `/api/uploads/${job.id}?offset=${offset}`,
        file.slice(offset, offset + size),
        (loaded) => onProgress(Math.min(offset + loaded, file.size), file.size),
        signal,
        'PUT',
      )
    }
    return await request<T>(`/api/uploads/${job.id}/complete?size=${file.size}`, {
      method: 'POST',
      signal,
    })
  } catch (error) {
    // Cleanup uses its own request: the transfer's AbortSignal may already be cancelled.
    await request(`/api/analyses/${job.id}`, {
      method: 'DELETE',
    }).catch(() => {})
    throw error
  }
}
