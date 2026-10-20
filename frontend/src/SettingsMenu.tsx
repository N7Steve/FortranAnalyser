import { useLayoutEffect, useRef, useState } from 'react'
import { Check, Moon, Palette, Settings2, Sun, X } from 'lucide-react'

type Preferences = { theme: 'modern' | 'original'; mode: 'light' | 'dark' }
const STORAGE_KEY = 'fortran-appearance'

function readPreferences(): Preferences {
  const fallback: Preferences = {
    theme: 'modern',
    mode: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
  }
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    return {
      theme: saved?.theme === 'original' ? 'original' : 'modern',
      mode: saved?.mode === 'dark' || saved?.mode === 'light' ? saved.mode : fallback.mode,
    }
  } catch {
    return fallback
  }
}

export default function SettingsMenu() {
  const [preferences, setPreferences] = useState(readPreferences)
  const [saved, setSaved] = useState(true)
  const dialog = useRef<HTMLDialogElement>(null)

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = preferences.theme
    document.documentElement.dataset.mode = preferences.mode
    document.documentElement.style.colorScheme = preferences.mode
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
      setSaved(true)
    } catch {
      setSaved(false)
    }
  }, [preferences])

  return (
    <>
      <button
        className="settings-trigger"
        onClick={() => dialog.current?.showModal()}
        aria-label="Abrir ajustes de apariencia"
        aria-haspopup="dialog"
      >
        <Settings2 size={18} />
        <span>Ajustes</span>
      </button>
      <dialog
        className="settings-dialog"
        ref={dialog}
        aria-labelledby="settings-title"
        onClick={(event) => {
          if (event.target === dialog.current) {
            const bounds = dialog.current!.getBoundingClientRect()
            if (
              event.clientX < bounds.left ||
              event.clientX > bounds.right ||
              event.clientY < bounds.top ||
              event.clientY > bounds.bottom
            )
              dialog.current?.close()
          }
        }}
      >
        <div className="settings-heading">
          <span className="settings-symbol">
            <Palette size={22} />
          </span>
          <div>
            <h2 id="settings-title">Hazlo tuyo</h2>
            <p>Elige cómo quieres explorar tu código.</p>
          </div>
          <button
            className="close-settings"
            aria-label="Cerrar ajustes"
            onClick={() => dialog.current?.close()}
            autoFocus
          >
            <X size={20} />
          </button>
        </div>
        <fieldset>
          <legend>Estilo de la interfaz</legend>
          <div className="theme-options">
            {(['modern', 'original'] as const).map((theme) => (
              <label
                key={theme}
                className={`theme-option ${preferences.theme === theme ? 'chosen' : ''}`}
              >
                <input
                  type="radio"
                  name="theme"
                  value={theme}
                  checked={preferences.theme === theme}
                  onChange={() => setPreferences((p) => ({ ...p, theme }))}
                />
                <span className={`theme-preview preview-${theme}`} aria-hidden="true">
                  <i />
                  <span>
                    <b />
                    <b />
                    <b />
                  </span>
                </span>
                <span className="theme-option-title">
                  {theme === 'modern' ? 'Moderno' : 'Original'}
                  {preferences.theme === theme && <Check size={16} />}
                </span>
                <small>
                  {theme === 'modern'
                    ? 'Azul índigo, superficies suaves y bordes redondeados.'
                    : 'Azul y grises inspirados en la aplicación Java original.'}
                </small>
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend>Modo de color</legend>
          <div className="mode-options">
            {(['light', 'dark'] as const).map((mode) => (
              <label key={mode} className={preferences.mode === mode ? 'chosen' : ''}>
                <input
                  type="radio"
                  name="mode"
                  value={mode}
                  checked={preferences.mode === mode}
                  onChange={() => setPreferences((p) => ({ ...p, mode }))}
                />
                {mode === 'light' ? <Sun size={19} /> : <Moon size={19} />}
                <span>{mode === 'light' ? 'Claro' : 'Oscuro'}</span>
                {preferences.mode === mode && <Check size={16} />}
              </label>
            ))}
          </div>
        </fieldset>
        <p className="settings-note" role="status">
          {saved
            ? 'Tu elección se guarda en este navegador y se aplica al instante.'
            : 'La elección se aplica a esta sesión. El navegador no permite guardarla.'}{' '}
          Las animaciones respetan la preferencia de movimiento reducido de tu dispositivo.
        </p>
        <button className="button primary settings-done" onClick={() => dialog.current?.close()}>
          Listo <Check size={16} />
        </button>
      </dialog>
    </>
  )
}
