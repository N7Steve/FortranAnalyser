# Plan de migración

## Objetivo y límites

Crear una aplicación personal pequeña para inspeccionar código Fortran desde el navegador y desplegarla en Docker sobre TrueNAS. Priorizar resultados fiables y una primera entrega útil con pocas dependencias.

Elección inicial: Python + FastAPI, React + TypeScript y, al incorporar historial, SQLite. `backend/` contiene motor, consola y API; `frontend/` contiene la interfaz React. Las pruebas están en `tests/` y la documentación en `docs/`.

## 1. Validar el motor

- [x] Reunir ejemplos representativos con permiso de uso y resultados esperados: formato fijo/libre, comentarios, continuaciones, declaraciones y terminadores.
- [x] Evaluar fparser2, documentar compatibilidad, preprocesado, inclusiones y límites. No prometer soporte completo del lenguaje.
- [x] Implementar un motor independiente con salida estructurada y una consola mínima: archivos, rutinas, líneas, declaraciones, anidamiento e información de análisis parcial.
- [x] Incorporar unas pocas reglas explicables, empezando por las que puedan validarse correctamente por ámbito.
- [x] Cubrir regresiones conocidas: `IMPLICIT NONE` con comentario final, cuatro variables en una declaración, identificadores como `shadow` y rutinas terminadas con `END`.

**Aceptación:** analizar un proyecto representativo desde consola, contrastar sus resultados y señalar explícitamente los archivos o construcciones que no se puedan interpretar.

**Resultado (2026-10-20):** implementado y contrastado con un proyecto sintético propio de formato fijo/libre. El corpus tiene expectativas explícitas y las pruebas cubren también resultados parciales y fallidos. fparser2 0.2.5 se adopta provisionalmente; ver [evaluación](PARSER.md). Pendiente validación adicional con modelos científicos reales aportados por sus propietarios. El siguiente paso de implementación es la fase 2, reutilizando el contrato de resultados existente.

**Verificación de esta entrega:** 34 pruebas pasan en Python 3.11 y 3.12 sobre Windows; Ruff comprueba estilo y formato. Se construyen wheel y distribución fuente y se comprueba que excluyen la referencia Java y los datos locales. La consola analiza el proyecto de ejemplo: 2 archivos completos y 1 aviso FA001 esperado. La validación en Linux/Docker y TrueNAS sigue perteneciendo a la fase 3.

## 2. Entregar una web mínima

- [x] Exponer el mismo motor mediante FastAPI, con estado y errores de cada análisis y ejecución de trabajo fuera del bucle de atención de peticiones.
- [x] Cargar un ZIP con límites de tamaño y extracción segura, sin ejecutar código ni scripts del proyecto.
- [x] Mostrar resumen, árbol de archivos, métricas y hallazgos sobre un visor de código, con filtros básicos.
- [x] Exportar resultados JSON. Aplazar el PDF y la personalización visual avanzada.
- [x] Documentar instalación y verificar el recorrido completo con un ejemplo pequeño.

**Aceptación:** subir un proyecto desde el navegador, consultar resultados localizados en el código y descargar el análisis sin bloquear la interfaz.

**Resultado (2026-10-20):** web React/TypeScript y API FastAPI implementadas. Cola acotada con cancelación, ZIP limitado y fuentes temporales; resumen, árbol, filtros, ámbitos, visor paginado y exportación del contrato JSON original. La aplicación puede servir la web compilada desde el mismo proceso HTTP; ver [arranque y límites](WEB.md). Se conserva explícitamente la distinción entre resultados completos, parciales y fallidos. No hay historial ni autenticación multiusuario. El siguiente paso es la fase 3 de Docker y TrueNAS.

**Verificación de esta entrega:** 63 pruebas pasan en Python 3.11 y 3.12 sobre Windows, incluida una prueba HTTP real durante un análisis. Ruff, formato del frontend, instalación reproducible con `npm ci`, TypeScript y construcción de Vite pasan. En navegador se han probado el ejemplo, la selección de un ZIP local, resultados, salto al código, filtro de gravedad, descarga JSON y recuperación tras recarga. Se construyen los paquetes Python y se comprueban sus exclusiones. El despliegue en Linux/TrueNAS todavía no se ha validado.

## 3. Desplegar en Docker y TrueNAS

- [x] Construir una imagen que incluya la web y la API, con proceso de análisis separado cuando corresponda y sin necesidad de escritorio gráfico.
- [x] Proporcionar Docker Compose, comprobación de salud, usuario sin privilegios y volúmenes para datos persistentes y trabajo temporal.
- [x] Documentar puerto, permisos, configuración, límites de recursos, limpieza y actualización. Excluir siempre `reference/`, secretos y datos locales de la imagen.
- [x] Comprobar arranque, análisis y conservación de resultados tras recrear el contenedor.
- [ ] Validar la instalación con la edición y versión reales de TrueNAS, cuando se disponga de ese entorno.

**Aceptación:** instalar siguiendo la documentación y analizar un proyecto desde otro equipo de la red.

**Resultado (2026-10-20):** imagen completa construida y probada en Docker Linux/amd64. El Compose local expone el puerto 8890; `deploy/truenas.yaml` permite construir desde el repositorio Git público. La imagen usa UID/GID 568:568, raíz de solo lectura, comprobación de salud y almacenamiento persistente. Se conservan fuentes e informes mediante registros JSON atómicos, sin incorporar todavía un historial visual ni comparaciones.

**Verificación:** 68 pruebas pasan tanto en Windows como dentro de la etapa Linux de Docker. Ambos YAML pasan `docker compose config`. Una prueba automática del contenedor valida recursos web, API, ejemplo, descarga, usuario no privilegiado, ausencia de Node/uv en ejecución y conservación del mismo informe y fuente después de recrear el contenedor. Las instrucciones están en [DEPLOYMENT.md](DEPLOYMENT.md). La instalación en el NAS real y el acceso desde otro equipo siguen pendientes; no se ha afirmado validación en TrueNAS.

## Revisión visual (2026-10-20)

- [x] Unificar tipografía DM Sans, aumentar tamaños de lectura y renovar colores, tarjetas y espaciados.
- [x] Gráfico circular de estados y barras de gravedad que filtran los hallazgos.
- [x] Mapa interactivo de archivos con comparación por líneas o hallazgos, selección y leyenda de estados.
- [x] Mapa de posición y extensión de rutinas con navegación al código, sin inferir dependencias ni rendimiento.

Los mapas usan exclusivamente los datos del informe. La vista compacta muestra hasta 18 rutinas; la pestaña de ámbitos conserva la lista completa. Los archivos sin métricas muestran su limitación. Los gráficos se construyen con HTML/CSS, sin servicios externos ni dependencias nuevas.

**Verificación:** TypeScript y construcción de producción correctos; formato del frontend validado. Imagen Docker reconstruida y saludable en el puerto 8890. Comprobadas en navegador la selección de archivo, el cambio de métrica, el filtro por gravedad y el salto de rutina a su línea resaltada. Vista móvil comprobada a 390 px sin desbordamiento horizontal.

## Apariencia y documentación dentro de la web (2026-10-20)

- [x] Aumentar textos auxiliares, etiquetas, cifras pequeñas y lectura del código.
- [x] Incorporar animaciones de entrada y transiciones con respeto al movimiento reducido.
- [x] Ajustes de estilo Original/Moderno y Claro/Oscuro, con persistencia local y navegación por teclado.
- [x] Añadir la sección «La migración»: origen, comparación técnica, casos corregidos y funciones aún no migradas.

La paleta Original se contrasta con `MainWindow.java` (azul 61, 143, 199 y paneles grises). Las explicaciones sobre comentarios y declaraciones se contrastan con `TasksBar.java`, el proyecto Maven original y las regresiones del motor. Se conserva la atribución a Michael García Rodríguez y la licencia del proyecto. Uso y comportamiento documentados en [WEB.md](WEB.md).

**Verificación de apariencia:** las cuatro combinaciones se comprueban en navegador, incluyendo guardado tras recarga, cierre con Escape y retorno del foco. Explorador y sección de migración comprobados con datos reales del ejemplo; vista móvil a 390 px sin desbordamiento de página y ajustes accesibles. TypeScript, construcción Vite, Prettier, Ruff y las 68 pruebas Python pasan. Docker reconstruido y saludable en 8890.

## Después de la primera versión útil

- [ ] Persistencia con SQLite, historial y comparación entre análisis con la misma versión de reglas.
- [ ] Exploración de módulos y dependencias; mapa de llamadas con limitaciones visibles.
- [ ] Diagnósticos opcionales de GNU Fortran, con configuración explícita de dependencias y entorno aislado.
- [ ] Informes PDF y perfiles de reglas según necesidades reales.

Quedan fuera inicialmente: soporte universal de dialectos Fortran, estimación de rendimiento, validación científica, refactorización automática, funciones de IA y una plataforma multiusuario pública.

## Referencia y continuidad

El proyecto original reside únicamente en `reference/`, ignorado por Git. Revisar selectivamente `TasksBar.java` (métricas), `CycloComplexity.java` (complejidad), `NoGUI.java` (modo consola), `MainWindow.java` (interfaz), `PDF.java` e idiomas cuando sean necesarios.

Por petición explícita, se añade un perfil orientativo de calidad con bonus por `EXIT`/`CYCLE`. Su fórmula y límites son visibles; no se presenta como equivalencia con la puntuación Java, validación científica ni estimación de rendimiento. Las instrucciones y decisiones se cuentan desde el AST.

Al terminar una entrega, marcar lo completado, registrar los límites encontrados y concretar el siguiente paso. El coste principal que debe despejar la primera entrega es la compatibilidad del parser con los modelos reales.


## Estructura e informes (2026-11-12)

- [x] Tema adicional Clásico naranja (claro/oscuro) e icono original, conservando atribución.
- [x] Carga ZIP, 7z, TAR, TAR.GZ/TGZ, TAR.BZ2, TAR.XZ y fuentes gzip/bzip2/xz.
- [x] Mantener límites de archivos, bytes, rutas y enlaces; descompresión en proceso con límite de 20 segundos.
- [x] Grafo estático de módulos, rutinas, tipos derivados, USE, CALL explícito, referencias a tipos y EXTENDS.
- [x] CC estructural por rutina, archivo y suma de proyecto; cobertura parcial explícita.
- [x] Nota orientativa adaptada con bonus únicos por EXIT/CYCLE y fórmula publicada.
- [x] PDF descargable con métricas, hallazgos, estados, diagramas, relaciones y sello virtual.

No se promete cualquier formato existente: RAR, archivos multipartes, cifrados y contenedores anidados no están soportados. Los gzip de una sola fuente necesitan conservar la extensión Fortran en el nombre enviado. El grafo no resuelve despacho dinámico, renombrados USE, genéricos ni llamadas a funciones en expresiones; los destinos externos o ambiguos quedan visibles sin resolver. No se calcula CC a partir del grafo de dependencias. La firma es un sello visual y una huella SHA-256 del JSON canónico, sin certificado digital. La puntuación es una adaptación pequeña y explícita, no una reproducción de las once métricas Java.

Verificación de esta entrega: 88 pruebas Python en Windows y Linux (etapa test de Docker), Ruff, TypeScript y construcción web; PDF de muestra renderizado para revisión visual. Navegador Chromium: tema naranja persistente, ejemplo, descarga PDF y móvil a 390 px sin desbordamiento ni errores JavaScript. El despliegue en el NAS real sigue pendiente. Siguiente paso: contrastar grafos y complejidad con un proyecto científico real, incluyendo sus convenciones de módulos e interfaces.


## Recuperación de capacidad del servidor (2026-11-12)

- [x] Distinguir el límite de tres trabajos activos del de ocho análisis guardados.
- [x] Añadir «Análisis del servidor» para recuperar informes, consultar estados, cancelar trabajos o eliminar análisis terminados, incluso sin la sesión original del navegador.
- [x] Conservar los informes hasta que el usuario los elimine y actualizar la lista mientras hay trabajos activos.

Regresión cubierta: servidor persistente con ocho registros después de reiniciar, rechazo explícito de una carga, listado y eliminación de un registro para aceptar otra carga. 90 pruebas Python pasan; Ruff, TypeScript y construcción web verificados. El siguiente paso de validación sigue siendo contrastar el motor con un proyecto científico real.


## Subida de 4 GiB y progreso (2026-11-12)

- [x] Límite de 4 GiB con comprobación anticipada de Content-Length y comprobación de bytes reales para cargas sin longitud.
- [x] Recepción en disco, cola por ruta y limpieza al completar, fallar, cancelar o reiniciar.
- [x] Extracción por streams/temporales de disco, con 8 GiB expandidos y 30 minutos de límite. Se mantienen 100 fuentes, 2 MB por fuente y 20 MB de fuentes en total.
- [x] Modal desde 20 MiB con porcentaje de transferencia real, MiB enviados, confirmación del servidor y cancelación.

Verificaciones: regresiones de formatos y extracción segura, límites escalados y cabecera de 4 GiB, carga de 32 MiB transferida al trabajador por ruta, limpieza y prueba de archivo ZIP real disperso de exactamente 4 GiB en Linux. La prueba dispersa se omite en Windows para evitar asignar físicamente 4 GiB. Documentados espacio de disco y límites de proxies. El NAS real sigue pendiente de validación.


Resultado de verificación: 96 pruebas pasan en Windows y una se omite por requerir archivo disperso Linux; las 97 pasan en Docker Linux. Ruff y compilación TypeScript/Vite pasan. Chromium con red limitada valida progreso parcial real, cancelación y subida posterior de 24 MiB, sin errores JavaScript ni desbordamiento a 390 px. No se ha transferido por HTTP un archivo completo de 4 GiB: el límite exacto se verifica con cabeceras, límites escalados y extracción del ZIP disperso de 4 GiB en disco.


## Diagnóstico de rechazos de carga (2026-11-12)

- [x] Exponer `max_upload_bytes` en `/api/config` y mostrar el límite comunicado por la API.
- [x] Distinguir un 413 sin detalle JSON y explicar la comprobación de API frente a proxy.
- [x] Documentar que la barra de progreso y la etiqueta 0.2.0 no identifican la versión del backend.

Verificación con los dos adjuntos aportados: recepción local HTTP 202 para 129.853.190 y 77.185.588 bytes (extracción sustituida por un comprobador, sin ejecutar el contenido). Ambos TAR superan 1.000 entradas en una inspección acotada; siguen sujetos a los límites de extracción y fuentes. El origen del 413 en el despliegue requiere su URL y/o cabeceras y cuerpo de respuesta; no se ha afirmado corrección del proxy remoto.


## Backend instalado y subida mediante Cloudflare (2026-11-12)

- [x] Confirmar respuesta HTTP 413 «10 MB» de Uvicorn en la IP directa aportada: el problema también existe en el backend desplegado.
- [x] Invalidar caché del paquete local en Docker y rastrear `backend/**` en uv.
- [x] Ejecutar pruebas sobre el wheel instalado y contrastarlo con las fuentes, sin reinstalación editable implícita.
- [x] Subida mediante bloques de 8 MiB, offsets estrictos, finalización con tamaño esperado, cancelación y caducidad de reservas abandonadas.

La imagen remota debe reconstruirse y recrearse; no se ha modificado el NAS ni Cloudflare desde esta sesión. La subida completa de ambos adjuntos es aceptada por la API local, pero ambos sobrepasan 1.000 entradas y no se promete análisis completo bajo los límites actuales.


Validación: 102 pruebas pasan sobre el paquete instalado en Docker Linux. Recepción local por bloques de los adjuntos reales (129.853.190 bytes en 16 peticiones y 77.185.588 bytes en 10), sustituyendo la extracción por un comprobador. Navegador con red limitada: progreso, cancelación y posterior recepción/análisis de un ZIP sintético de 24 MiB; se observan cuatro peticiones PUT para esa carga. Compilación TypeScript/Vite y Ruff correctos.


## Cantidad de entradas del comprimido (2026-11-12)

- [x] Retirar el máximo de 1.000 entradas para ZIP, TAR y 7z, mediante el recolector común.
- [x] Verificar extracción con más de 1.000 entradas en los tres formatos y rechazo de rutas inseguras después de ese umbral.

La cantidad de entradas deja de tener una cuota fija. No se promete memoria ni tiempo infinitos: siguen vigentes 4 GiB de subida, 8 GiB expandidos, 30 minutos de extracción, 100 fuentes Fortran, 2 MB por fuente y 20 MB de fuentes en total. La comprobación de duplicados mantiene un índice de rutas en memoria. Los resultados anteriores sobre la barrera de 1.000 entradas corresponden al estado anterior a esta entrega.
