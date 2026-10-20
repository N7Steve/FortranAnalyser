# Web mínima — fase 2

## Arranque local

Requisitos: Python 3.11 o posterior, uv y Node.js 22.12 o posterior con npm. En la raíz del repositorio:

```sh
uv sync --frozen --extra web --extra dev
cd frontend
npm ci
npm run build
cd ..
uv run --frozen --extra web python -m fortran_analyser.web
```

Abrir **http://127.0.0.1:8000/**. La API sirve la web compilada y sus fuentes tipográficas localmente, sin CDN ni servicios de análisis externos. El botón «Explorar un ejemplo» utiliza tres fuentes sintéticas incluidas con el paquete para mostrar resultados completos y parciales.

El lanzador usa un bucle Selector para el servicio local en Windows, donde también se crean procesos de análisis. Se debe utilizar un único proceso de servidor: la cola y los resultados pertenecen a su memoria.

Para desarrollar la interfaz con recarga automática, mantener la API anterior y ejecutar en otra terminal:

```sh
cd frontend
npm run dev
```

Abrir **http://127.0.0.1:5173/**. En desarrollo React consulta directamente la API en el puerto 8000; CORS solo permite los orígenes locales `127.0.0.1:5173` y `localhost:5173`. La versión compilada usa el mismo origen que la API. `FORTRAN_FRONTEND_DIR` permite indicar otro directorio de archivos compilados al arrancar el servidor.

## Recorrido de uso

1. Seleccionar o arrastrar un ZIP y elegir formato automático, libre o fijo. Solo se extraen fuentes Fortran; no se ejecutan scripts ni modelos.
2. Consultar el estado y el avance, o cancelar. El análisis se ejecuta fuera del bucle de atención HTTP, usando el mismo motor de consola y sus procesos limitados por archivo.
3. Ver resumen de archivos, rutinas, hallazgos y cobertura. Los archivos parciales o fallidos conservan sus estados y no aportan métricas desconocidas.
4. Filtrar por gravedad o abrir un hallazgo. El explorador muestra árbol de archivos, búsqueda, filtro de estado, ámbitos y código con la línea resaltada.
5. Exportar el contrato JSON original del motor.

El visor representa hasta 200 líneas por página y acorta visualmente las líneas que superan los 1.500 caracteres. El contenido original se conserva en el servidor y las ubicaciones del motor no se modifican. Las métricas cuentan líneas físicas, no solo líneas ejecutables.

## API

| Método y ruta | Resultado |
| --- | --- |
| `GET /api/health` | Estado del servicio. |
| `GET /api/example` | ZIP sintético distribuido con la aplicación. |
| `POST /api/analyses?name=Proyecto&source_form=auto` | Cuerpo ZIP binario con `Content-Type: application/zip`; devuelve identificador y estado, HTTP 202. No usa multipart. |
| `GET /api/analyses/{id}` | Estado, archivos procesados, total y error si existe. |
| `GET /api/analyses/{id}/report` | JSON original, disponible al terminar. `?download=true` lo entrega como descarga. |
| `GET /api/analyses/{id}/source?path=...` | Fuente UTF-8 de un archivo perteneciente al informe. No permite leer rutas arbitrarias. |
| `DELETE /api/analyses/{id}` | Cancela un análisis activo (202) o elimina sus resultados temporales si ya terminó (200). |

Estados de trabajo: `uploading`, `queued`, `extracting`, `running`, `completed`, `failed`, `cancelled`. Que el trabajo termine no implica que todas las fuentes se hayan interpretado: sus estados siguen estando en el informe. Un ZIP inválido es un fallo del trabajo, no un informe vacío exitoso.

## Límites y conservación

- ZIP de hasta 10 MB; carga limitada a 30 segundos.
- Hasta 1.000 entradas, 20 MB descomprimidos totales y 100 fuentes Fortran de hasta 2 MB cada una.
- Rechazo de rutas absolutas, navegación `..`, separadores ambiguos, nombres reservados, duplicados sin distinción de mayúsculas, enlaces, archivos especiales y ZIP cifrados.
- Un trabajador, hasta tres trabajos activos/en cola y ocho análisis retenidos por proceso. Las fuentes se analizan secuencialmente con un máximo de cinco segundos por archivo.
- Los archivos de un trabajo inválido o cancelado se limpian; los terminados se conservan en un directorio temporal privado hasta su eliminación o parada del servidor.
- El navegador recuerda el identificador del último trabajo en su pestaña para recuperarlo al recargar. Un nuevo análisis sustituye al anterior. El arranque local sin `FORTRAN_DATA_DIR` es temporal. La fase 3 añade persistencia opcional, activada en Docker; ver [despliegue](DEPLOYMENT.md).

Es una aplicación personal, sin autenticación ni separación entre usuarios, no un servicio público de subida de código. Los límites de lectura y tiempo no son una cuota estricta de memoria ni un sandbox completo. El despliegue de la fase 3 configura almacenamiento y acceso por la red local.

## Comprobaciones

```sh
uv run --frozen --extra web --extra dev python -m pytest -q
uv run --frozen --extra web --extra dev ruff check .
uv run --frozen --extra web --extra dev ruff format --check .
cd frontend
npm run format:check
npm run build
```

Las pruebas cubren extracción segura y límites, carga real del ejemplo, estados y errores, descarga, lectura de fuentes autorizadas, cancelación, limpieza y respuesta de la API mientras un trabajo está ocupado. TypeScript verifica la interfaz y Vite construye los recursos. El recorrido de navegador se contrasta con la API real, no con datos simulados.


## Apariencia y explicación de la migración

El botón **Ajustes** de la barra superior permite combinar dos estilos (**Moderno** y **Original**) con modo **Claro** u **Oscuro**. El estilo Original recupera el azul RGB 61, 143, 199 y los paneles grises de `MainWindow.java`; es una adaptación web, no una reproducción de Swing. La primera visita toma el modo del dispositivo; las elecciones posteriores se guardan en `localStorage` del navegador. Si el almacenamiento está bloqueado, la elección sigue funcionando durante la sesión y el menú informa de ello.

El menú usa un diálogo nativo: mantiene el foco dentro, se cierra con Escape y devuelve el foco al botón de ajustes. Los grupos de opciones funcionan con teclado. Las transiciones de botones y barras y las animaciones de entrada respetan `prefers-reduced-motion`; el salto del visor también evita el desplazamiento suave con esa preferencia.

La navegación **La migración**, disponible incluso sin cargar un proyecto, explica la autoría original, la comparación Java/Swing/Maven con Python/fparser2/FastAPI/React/Vite/Docker, las correcciones comprobadas y las capacidades que siguen pendientes. No requiere ni sirve los archivos de `reference/`. Cambiar de sección mantiene el informe y el trabajo en curso.
