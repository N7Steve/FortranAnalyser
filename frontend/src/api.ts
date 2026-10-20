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
