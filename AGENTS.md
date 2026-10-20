# Acuerdos de trabajo

## Git

- Trabajar directamente en `main`. No crear ramas, worktrees ni pull requests salvo petición explícita del usuario.
- Antes de editar, inspeccionar el árbol de trabajo y sincronizar con `origin/main` mediante fast-forward cuando exista. Preservar los cambios del usuario; nunca resetear, descartar trabajo ni forzar un push para resolver divergencias.
- Si `main` no está disponible, aclarar el destino en vez de inventar una rama.
- Preparar y validar los cambios y mostrar el resultado concreto. Hacer commit y push solo con confirmación del usuario para ese alcance. Una instrucción explícita como «commit y push» o «sube los cambios» ya es confirmación; no volver a pedirla.
- Cumplir las verificaciones aplicables antes de publicar. No cerrar, fusionar ni borrar PRs o ramas existentes por esta convención.

## Alcance y consumo de IA

- Seguir `docs/MIGRATION.md`; completar una entrega pequeña y verificable cada vez.
- No usar subagentes salvo petición explícita del usuario.
- Evitar migraciones línea por línea, infraestructura prematura y relecturas completas del proyecto antiguo. Consultar únicamente los archivos de referencia necesarios.
- Mantener el estado de las entregas en el plan para facilitar la continuidad entre sesiones.
- No añadir IA en tiempo de ejecución, transformación automática de Fortran ni ejecución de modelos científicos al alcance inicial.

## Arquitectura y referencia

- Motor Python independiente de FastAPI, del frontend y de la generación de informes. Resultados estructurados y reutilizables por consola y web.
- React con TypeScript para el frontend. Docker y Docker Compose como objetivo de despliegue en TrueNAS.
- Validar el parser con código representativo antes de consolidar el motor. Informar de sintaxis no soportada y resultados parciales; no presentar fallos de análisis como ausencia de problemas.
- Emitir hallazgos con regla, archivo, ubicación, explicación y gravedad. No reproducir una nota global de calidad sin fundamento.
- `reference/` es una copia local ignorada. No modificarla, borrarla, subirla con `git add -f` ni incluirla en imágenes Docker. Las nuevas instalaciones pueden no tenerla.
- Preservar autoría y avisos de licencia del material reutilizado.

## Verificación

- En esta fase documental, comprobar enlaces locales, contenido del commit, exclusiones y ausencia de cambios en la referencia.
- Al introducir código, añadir las instrucciones reproducibles de instalación y verificación junto con sus herramientas. Ejecutar las comprobaciones pertinentes y comunicar lo que no se haya podido verificar.
- Las pruebas del motor deben cubrir casos de Fortran representativos y regresiones observadas, no limitarse a replicar la implementación antigua.
- No ejecutar comandos de construcción ni scripts proporcionados por proyectos subidos. Limitar archivos, extracción y recursos de análisis cuando se implemente la carga.
