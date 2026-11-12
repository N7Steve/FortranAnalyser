# Web de FortranAnalyser

## Arranque local

Requisitos: Python 3.11 o posterior, uv y Node.js 22.12 o posterior con npm.

```sh
uv sync --frozen --extra web --extra dev
cd frontend
npm ci
npm run build
cd ..
uv run --frozen --extra web python -m fortran_analyser.web
```

Abrir **http://127.0.0.1:8000/**. La API sirve la web compilada y las fuentes tipográficas sin CDN. «Explorar un ejemplo» incluye fuentes sintéticas completas y parciales. Docker/TrueNAS se documenta en [DEPLOYMENT.md](DEPLOYMENT.md).

## Sin cuotas de procesamiento

Por petición explícita del usuario, no hay topes fijos de:

- Bytes subidos, tamaño expandido, tamaño por fuente o suma de fuentes.
- Cantidad de entradas, fuentes, trabajos activos o informes guardados.
- Duración de subida, extracción o análisis; tampoco caducan las reservas de carga.
- Tamaño del registro JSON restaurado ni longitud visible de líneas del visor.

La web y el motor usan estos valores por defecto. Quien invoque directamente el motor o la consola puede optar por imponer `max_file_bytes`, `max_files` o `timeout` (en consola: `--max-file-bytes`, `--max-files`, `--timeout`). La web no los impone. El Compose no fija cuotas de CPU, RAM ni procesos.

Esto no proporciona recursos infinitos: el disco, la RAM, el sistema operativo, el parser y los proxies externos siguen teniendo sus propias restricciones. La extracción y las cargas trabajan en disco; el parser necesita representar cada fuente y su AST en memoria. La cola ejecuta un proyecto cada vez sin rechazar trabajos por su cantidad.

Se mantienen las comprobaciones de integridad y de rutas: rechazo de navegación `..`, rutas absolutas, componentes ambiguos, duplicados y enlaces/archivos especiales. Solo se escriben fuentes Fortran regulares. Los nombres que se materializan deben ser portables; un directorio de documentación no extraído como `About..` no provoca un fallo por reglas de nombres de Windows. No se ejecuta código ni scripts del proyecto.

Formatos soportados: ZIP, 7z, TAR y sus compresiones gzip/bzip2/xz, además de fuentes individuales comprimidas. Para estas últimas, el nombre debe conservar la extensión Fortran (por ejemplo, `.f90.gz`). No se añaden RAR, cifrados ni extracción recursiva de comprimidos internos.

## Transferencia y cancelación

La web envía peticiones independientes de 8 MiB para atravesar proxies como Cloudflare. Es un tamaño de transporte, no un máximo de archivo ni una cuota de bloques de la API. La API acepta bloques mayores y los recibe en un temporal en disco, sin acumularlos en memoria. La transferencia comprueba offsets y tamaño final exactos.

Desde 20 MiB se abre un modal con porcentaje y bytes transferidos. El 100 % de transferencia no significa que haya terminado el análisis. Cancelar o pulsar Escape interrumpe la petición y solicita borrar la carga. No hay plazo de caducidad para cargas abandonadas: pueden eliminarse en «Análisis del servidor». Al reiniciar se limpian temporales de carga propios del servidor; los informes terminados se conservan si se usa almacenamiento persistente.

La extracción y el análisis permanecen en procesos separados y permiten cancelación sin imponer una duración máxima. La lista de trabajos e informes sigue accesible después de borrar la caché del navegador. Eliminar un trabajo terminado borra su informe y sus fuentes; no hay borrado automático para liberar plazas.

## API

| Método y ruta | Resultado |
| --- | --- |
| `GET /api/health` | Salud del servicio. |
| `GET /api/config` | Persistencia, `max_upload_bytes: null` (sin cuota) y `upload_chunk_bytes: 8388608` (tamaño recomendado). |
| `GET /api/example` | ZIP sintético. |
| `GET /api/analyses` | Trabajos e informes retenidos. |
| `POST /api/uploads?name=...&source_form=auto` | Reserva una subida por bloques. |
| `PUT /api/uploads/{id}?offset=...` | Añade el siguiente bloque y devuelve bytes recibidos. |
| `POST /api/uploads/{id}/complete?size=...` | Comprueba el tamaño exacto y encola el análisis. |
| `POST /api/analyses?name=...&source_form=auto` | Alternativa binaria en una sola petición, `application/octet-stream`. |
| `GET /api/analyses/{id}` | Estado y progreso. |
| `GET /api/analyses/{id}/report` | Informe JSON; `?download=true` fuerza descarga. |
| `GET /api/analyses/{id}/report.pdf` | Informe PDF descargable. |
| `GET /api/analyses/{id}/source?path=...` | Fuente UTF-8 de un archivo del informe. |
| `DELETE /api/analyses/{id}` | Cancela un trabajo o elimina un informe terminado. |

El estado de trabajo `completed` no demuestra que todas las fuentes se hayan interpretado: el informe conserva estados completos, parciales, fallidos y omitidos. Los errores de lectura o sintaxis nunca se presentan como ausencia de problemas. El visor pagina las líneas sin truncar su contenido.

## Resultados, métricas y apariencia

El grafo muestra módulos, rutinas, tipos derivados, USE, CALL explícito, pertenencia, herencia y referencias a tipos. Las relaciones externas o ambiguas quedan sin resolver. No reconstruye despacho dinámico, genéricos, renombrados USE ni llamadas en expresiones.

La CC estructural cuenta una base por unidad ejecutable y decisiones IF, ELSE IF, DO con control, CASE no DEFAULT, WHERE y FORALL. No se deduce del grafo de dependencias ni representa un CFG completo. Se agrega por rutina, archivo y proyecto, con cobertura parcial visible.

La nota orientativa 0–10 es `6 × proporción de ámbitos con IMPLICIT NONE + 2 si profundidad de bucles ≤ 3 + 1 si hay EXIT + 1 si hay CYCLE`. Los bonus se conceden una vez por archivo sobre instrucciones AST. La nota global es la media de archivos y no se emite si hay resultados parciales o fallidos. No es una validación científica ni una reproducción de las once métricas Java.

El PDF incluye resultados, estados, métodos, métricas, hallazgos localizados, diagramas y relaciones. La firma virtual es un sello visual, acompañado del SHA-256 del JSON canónico (`json.dumps(report, sort_keys=True, ensure_ascii=True)` en UTF-8), sin certificado digital.

Temas Moderno, Original y Clásico naranja, todos con modo claro/oscuro y preferencias locales. El icono original procede de `fortranAnalyserIcon.png`, de Michael García Rodríguez, bajo la licencia GPL del repositorio. `reference/` sigue ignorado y sin modificaciones. Los informes anteriores necesitan un nuevo análisis para incorporar las métricas nuevas.

## Comprobaciones

```sh
uv run --frozen --extra web --extra dev python -m pytest -q
uv run --frozen --extra web --extra dev ruff check backend tests
uv run --frozen --extra web --extra dev ruff format --check backend tests
cd frontend
npm run build
npm run format:check
```

La etapa Docker `test` prueba el paquete instalado y lo compara con las fuentes. No requiere ejecutar los proyectos subidos.
