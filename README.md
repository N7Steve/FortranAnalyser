# FortranAnalyser

Modernización de un analizador estático de código Fortran, originalmente desarrollado en Java por Michael García Rodríguez en la Universidade de Vigo.

El objetivo es explorar proyectos Fortran desde una interfaz web: consultar métricas, localizar hallazgos en el código y, más adelante, comparar análisis. La aplicación analiza código fuente; no valida resultados científicos ni mide el rendimiento de los modelos.

## Dirección técnica

- **Motor:** Python, con fparser2 para interpretar la estructura sintáctica de Fortran.
- **API:** FastAPI, separada del motor para permitir también su uso desde consola.
- **Frontend:** React y TypeScript.
- **Persistencia:** SQLite cuando se incorpore el historial.
- **Despliegue:** imagen Docker con frontend incluido, almacenamiento persistente y configuración mediante Docker Compose para TrueNAS. La compatibilidad se comprobará con la versión de destino.

## Estado

Motor Python independiente, consola JSON y web React con API FastAPI implementados. Se pueden cargar proyectos ZIP, seguir su análisis, consultar métricas y abrir hallazgos sobre el código. La fase 3 añade una imagen completa, persistencia y un YAML de TrueNAS que construye directamente desde Git.

El [plan de migración](docs/MIGRATION.md) recoge el progreso. Los acuerdos de trabajo están en [AGENTS.md](AGENTS.md), y la [evaluación del parser](docs/PARSER.md) detalla compatibilidad, definición de métricas y límites.

## Ejecutar

**Docker / TrueNAS:** consultar [despliegue](docs/DEPLOYMENT.md). `docker compose up -d --build --wait` construye la copia local y expone la web en `http://localhost:8890/`. [deploy/truenas.yaml](deploy/truenas.yaml) está preparado para pegar en TrueNAS y construir desde `main`.

**Web:** seguir las [instrucciones de arranque local](docs/WEB.md). Incluye un proyecto de ejemplo, explorador visual, filtros, descarga JSON, temas claro/oscuro y una sección sobre la migración. Docker conserva los resultados en su volumen; el arranque local sin configuración de persistencia usa datos temporales.

**Consola:**

Requisitos: Python 3.11 o posterior y [uv](https://docs.astral.sh/uv/). Desde la raíz del repositorio:

```sh
uv sync --frozen --extra dev
uv run --frozen --extra dev fortran-analyser tests/fixtures/project
uv run --frozen --extra dev fortran-analyser tests/fixtures/project --output report.json
```

Se puede indicar un archivo en lugar de una carpeta. `--source-form free` o `--source-form fixed` permite corregir el formato deducido de la extensión. No se compila ni se ejecuta el código Fortran.

El proyecto de ejemplo devuelve 2 archivos analizados y 1 aviso por ausencia de `IMPLICIT NONE` en la subrutina antigua. La fuente moderna tiene 1 módulo, 1 subrutina, 1 función, 12 entidades declaradas y profundidad de bucles 2.

La salida incluye versiones de esquema, reglas y parser; por archivo, estado, formato, líneas, métricas, ámbitos y hallazgos con ubicación. Las métricas desconocidas son `null`. Los códigos de salida son `0` si todos los archivos pudieron analizarse (aunque tengan avisos), `1` si alguno es parcial, fallido u omitido y `2` si hay un error de entrada, límites de proyecto o escritura de salida.

Límites predeterminados: 500 archivos, 2 MB por archivo y 10 segundos de análisis por archivo, configurable con `--max-files`, `--max-file-bytes` y `--timeout`. La consola procesa proyectos locales de confianza; no es aún un servicio de carga de archivos ni un aislamiento para entradas hostiles.

## Verificación

```sh
uv run --frozen --extra web --extra dev python -m pytest -q
uv run --frozen --extra web --extra dev ruff check .
uv run --frozen --extra web --extra dev ruff format --check .
uv build
```

Para la interfaz, ejecutar `npm ci`, `npm run format:check` y `npm run build` desde `frontend/`. Consultar [WEB.md](docs/WEB.md) para el recorrido completo y los límites de carga.

Las pruebas y sus [ejemplos sintéticos](tests/fixtures/README.md) no dependen de `reference/`. El paquete instalable contiene el motor y la consola; la copia Java no se distribuye con él.

## Referencia local

`reference/` conserva íntegra la copia del proyecto Java, incluidos sus recursos y compilados. Está excluida de Git y del contexto Docker: **no se sube a GitHub ni aparece al clonar este repositorio**. Se necesita una copia local independiente si se quiere consultar el original en otro equipo. No se debe borrar durante la migración.

El original sirve como referencia funcional, no como especificación de resultados correctos: varias métricas se basan en búsquedas de texto y necesitan revisión.

## Autoría y licencia

Se conserva en `LICENSE.txt` el aviso original GPL-3.0-o-posterior y la atribución a Michael García Rodríguez. Al reutilizar código, recursos o documentación, conservar sus avisos y revisar las licencias de las dependencias incorporadas.

La web incluye [avisos de terceros](frontend/public/THIRD_PARTY_NOTICES.txt) y copias de sus licencias, distribuidas también con los recursos compilados.
