# Plan de migración

## Objetivo y límites

Crear una aplicación personal pequeña para inspeccionar código Fortran desde el navegador y desplegarla en Docker sobre TrueNAS. Priorizar resultados fiables y una primera entrega útil con pocas dependencias.

Elección inicial: Python + FastAPI, React + TypeScript y, al incorporar historial, SQLite. La fase 1 ya dispone de motor y consola en `backend/`, pruebas en `tests/` y documentación en `docs/`. `frontend/` se creará en la fase web.

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

- [ ] Exponer el mismo motor mediante FastAPI, con estado y errores de cada análisis y ejecución de trabajo fuera del bucle de atención de peticiones.
- [ ] Cargar un ZIP con límites de tamaño y extracción segura, sin ejecutar código ni scripts del proyecto.
- [ ] Mostrar resumen, árbol de archivos, métricas y hallazgos sobre un visor de código, con filtros básicos.
- [ ] Exportar resultados JSON. Aplazar el PDF y la personalización visual avanzada.
- [ ] Documentar instalación y verificar el recorrido completo con un ejemplo pequeño.

**Aceptación:** subir un proyecto desde el navegador, consultar resultados localizados en el código y descargar el análisis sin bloquear la interfaz.

## 3. Desplegar en Docker y TrueNAS

- [ ] Construir una imagen que incluya la web y la API, con proceso de análisis separado cuando corresponda y sin necesidad de escritorio gráfico.
- [ ] Proporcionar Docker Compose, comprobación de salud, usuario sin privilegios y volúmenes para datos persistentes y trabajo temporal.
- [ ] Documentar puerto, permisos, configuración, límites de recursos, limpieza y actualización. Excluir siempre `reference/`, secretos y datos locales de la imagen.
- [ ] Comprobar arranque, análisis y conservación de resultados tras recrear el contenedor; validar con la edición y versión reales de TrueNAS.

**Aceptación:** instalar siguiendo la documentación y analizar un proyecto desde otro equipo de la red.

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
