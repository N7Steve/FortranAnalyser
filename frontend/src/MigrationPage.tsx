import {
  ArrowRight,
  Braces,
  CheckCheck,
  ChevronRight,
  Code2,
  Container,
  FileSearch,
  GitBranch,
  History,
  Layers,
  Monitor,
  Sparkles,
} from 'lucide-react'

const comparisons = [
  [
    'Interfaz',
    'Aplicación de escritorio Java Swing, con disposición fija.',
    'Web React + TypeScript, adaptable a móvil y escritorio, con cuatro combinaciones de apariencia.',
  ],
  [
    'Motor',
    'Java 8; varias métricas basadas en búsquedas de texto por línea.',
    'Python + fparser2: se interpreta la estructura sintáctica de Fortran para obtener ámbitos y métricas.',
  ],
  [
    'Resultados',
    'Métricas, puntuaciones y generación de informes PDF con iText.',
    'Hallazgos con regla, gravedad, archivo y línea; estados completos, parciales y fallidos. Exportación JSON.',
  ],
  [
    'Exploración',
    'Selección de directorios e informes desde el equipo de escritorio.',
    'Carga ZIP, árbol de archivos, mapas visuales, filtros y visor con navegación al hallazgo o rutina.',
  ],
  [
    'Arquitectura',
    'Proyecto Maven distribuido como JAR, con interfaz Swing y modo de consola.',
    'Motor independiente, consola y API FastAPI; frontend compilado con Vite.',
  ],
  [
    'Despliegue y datos',
    'Ejecución local sobre una instalación de Java.',
    'Una imagen Docker con web y API. Compose para TrueNAS y persistencia de fuentes e informes en un volumen.',
  ],
]

const corrections = [
  {
    title: 'Los comentarios ya no ocultan instrucciones',
    before: 'IMPLICIT NONE ! tipos explícitos',
    text: 'El comprobador antiguo descartaba las líneas con «!». El nuevo parser reconoce la instrucción aunque tenga un comentario al final, y comprueba IMPLICIT NONE por ámbito y herencia del host.',
  },
  {
    title: 'Declaraciones y variables son cosas distintas',
    before: 'integer :: a, b, c, d',
    text: 'El contador antiguo sumaba una declaración y, como máximo, otra variable al detectar una coma. Ahora se distinguen una declaración y cuatro entidades, también con arrays e inicializadores.',
  },
  {
    title: 'Una palabra dentro de un nombre no es un bucle',
    before: 'real :: shadow',
    text: 'Las búsquedas de texto podían confundir «DO» dentro de un identificador con una instrucción. Las métricas nuevas recorren nodos sintácticos; los nombres y literales no se cuentan como palabras clave.',
  },
  {
    title: 'Cada resultado explica sus límites',
    before: '#ifdef DOUBLE_PRECISION',
    text: 'El preprocesado y las inclusiones sin resolver quedan señalados como análisis parcial. No se presentan métricas de rutinas inventadas ni se interpreta un fallo de lectura como ausencia de problemas.',
  },
]

export default function MigrationPage() {
  return (
    <div className="migration-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">EL PROYECTO, ANTES Y AHORA</div>
          <h1>El mismo origen. Una nueva etapa.</h1>
          <p>Qué conservamos, qué hemos cambiado y por qué.</p>
        </div>
        <span className="migration-tag">
          <History size={16} /> La migración
        </span>
      </div>
      <section className="migration-hero panel">
        <span className="chart-eyebrow">
          <GitBranch size={15} /> DE ESCRITORIO A WEB
        </span>
        <h2>De leer líneas a entender la estructura.</h2>
        <p>
          FortranAnalyser nació como un proyecto académico de Michael García Rodríguez en la
          Universidade de Vigo. Esta versión retoma su propósito: ayudar a explorar código Fortran y
          localizar aspectos que conviene revisar. La migración reescribe el motor y la interfaz,
          conserva el reconocimiento a su autor y mantiene la licencia GPL-3.0-or-later.
        </p>
        <div className="migration-journey">
          <span>
            <Monitor size={21} />
            <b>Java + Swing</b>
            <small>La aplicación original</small>
          </span>
          <ArrowRight size={23} />
          <span>
            <Braces size={21} />
            <b>Python + fparser2</b>
            <small>Un motor independiente</small>
          </span>
          <ArrowRight size={23} />
          <span>
            <Code2 size={21} />
            <b>React + FastAPI</b>
            <small>La experiencia web</small>
          </span>
          <ArrowRight size={23} />
          <span>
            <Container size={21} />
            <b>Docker + TrueNAS</b>
            <small>Despliegue en tu servidor</small>
          </span>
        </div>
      </section>
      <section className="panel migration-comparison">
        <div className="panel-heading">
          <div>
            <h2>Qué cambia en la práctica</h2>
            <p>Una comparación de capacidades y decisiones técnicas.</p>
          </div>
          <Layers size={22} />
        </div>
        <div className="comparison-scroll">
          <table>
            <caption className="visually-hidden">
              Comparación entre la aplicación original y la migración web
            </caption>
            <thead>
              <tr>
                <th scope="col">Área</th>
                <th scope="col">Aplicación original</th>
                <th scope="col">Versión web actual</th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map(([area, before, now]) => (
                <tr key={area}>
                  <th scope="row">{area}</th>
                  <td>{before}</td>
                  <td>{now}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="migration-corrections">
        <div className="section-heading">
          <span className="chart-eyebrow">
            <FileSearch size={15} /> CORRECCIONES DEL ANÁLISIS
          </span>
          <h2>Menos suposiciones, más contexto.</h2>
          <p>Casos concretos cubiertos por las pruebas de regresión del motor.</p>
        </div>
        <div className="correction-grid">
          {corrections.map((item) => (
            <article className="panel correction-card" key={item.title}>
              <CheckCheck size={21} />
              <h3>{item.title}</h3>
              <code>{item.before}</code>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>
      <div className="migration-bottom">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Una forma diferente de revisar</h2>
              <p>Lo nuevo que ya puedes utilizar.</p>
            </div>
            <Sparkles size={21} />
          </div>
          <ul>
            <li>Gráficos de cobertura y gravedad basados en el informe real.</li>
            <li>Mapa de archivos por líneas o hallazgos y vista de posición de rutinas.</li>
            <li>Fuentes e informes conservados al recrear el contenedor con su volumen.</li>
            <li>Cargas limitadas, extracción ZIP validada y análisis sin ejecutar el modelo.</li>
            <li>
              Temas Original y Moderno, modo claro u oscuro y preferencias guardadas en el
              navegador.
            </li>
          </ul>
        </section>
        <section className="panel migration-limits">
          <div className="panel-heading">
            <div>
              <h2>Lo que queda por hacer</h2>
              <p>Una migración útil, con un alcance explícito.</p>
            </div>
          </div>
          <ul>
            <li>El PDF y los idiomas de la aplicación original todavía no están migrados.</li>
            <li>
              No se traslada la nota global de calidad ni se premia el uso de EXIT o CYCLE: esos
              criterios necesitan contexto.
            </li>
            <li>
              No hay todavía historial visual, comparaciones, mapa de llamadas ni diagnóstico de
              compilación.
            </li>
            <li>
              fparser2 no cubre todos los dialectos. Interpretar sintaxis no demuestra corrección
              científica ni rendimiento.
            </li>
            <li>
              Docker está probado localmente; falta validar la instalación en el TrueNAS real.
            </li>
          </ul>
        </section>
      </div>
      <aside className="migration-sources">
        <GitBranch size={18} />
        <p>
          Comparación contrastada con <code>MainWindow.java</code>, <code>TasksBar.java</code> y{' '}
          <code>pom.xml</code> de la referencia original, y con las pruebas y documentación del
          motor actual. La copia antigua se conserva aparte como referencia local.
        </p>
        <a
          href="https://github.com/N7Steve/FortranAnalyser/blob/main/docs/MIGRATION.md"
          target="_blank"
          rel="noreferrer"
        >
          Ver plan de migración
          <ChevronRight size={16} />
        </a>
      </aside>
    </div>
  )
}
