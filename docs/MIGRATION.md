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

No trasladar automáticamente sus puntuaciones: premiar `EXIT`/`CYCLE`, contar palabras como instrucciones o deducir rendimiento a partir del número de variables no constituye una base suficiente.

Al terminar una entrega, marcar lo completado, registrar los límites encontrados y concretar el siguiente paso. El coste principal que debe despejar la primera entrega es la compatibilidad del parser con los modelos reales.
