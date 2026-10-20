# Plan de migración

## Objetivo y límites

Crear una aplicación personal pequeña para inspeccionar código Fortran desde el navegador y desplegarla en Docker sobre TrueNAS. Priorizar resultados fiables y una primera entrega útil con pocas dependencias.

Elección inicial: Python + FastAPI, React + TypeScript y, al incorporar historial, SQLite. No hay implementación todavía. La estructura prevista es `backend/`, `frontend/`, `tests/` y `docs/`; se crearán cuando tengan contenido real.

## 1. Validar el motor

- [ ] Reunir ejemplos representativos con permiso de uso y resultados esperados: formato fijo/libre, comentarios, continuaciones, declaraciones y terminadores.
- [ ] Evaluar fparser2, documentar compatibilidad, preprocesado, inclusiones y límites. No prometer soporte completo del lenguaje.
- [ ] Implementar un motor independiente con salida estructurada y una consola mínima: archivos, rutinas, líneas, declaraciones, anidamiento e información de análisis parcial.
- [ ] Incorporar unas pocas reglas explicables, empezando por las que puedan validarse correctamente por ámbito.
- [ ] Cubrir regresiones conocidas: `IMPLICIT NONE` con comentario final, cuatro variables en una declaración, identificadores como `shadow` y rutinas terminadas con `END`.

**Aceptación:** analizar un proyecto representativo desde consola, contrastar sus resultados y señalar explícitamente los archivos o construcciones que no se puedan interpretar.

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
