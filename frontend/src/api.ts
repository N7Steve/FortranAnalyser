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

export function uploadArchive<T>(
  url: string,
  file: Blob,
  onProgress: (loaded: number, total: number) => void,
  signal: AbortSignal,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const abort = () => xhr.abort()
    signal.addEventListener('abort', abort, { once: true })
    const cleanup = () => signal.removeEventListener('abort', abort)
    xhr.open('POST', apiUrl(url))
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
              ? body.detail
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
