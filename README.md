# FortranAnalyser

Modernización de un analizador estático de código Fortran, originalmente desarrollado en Java por Michael García Rodríguez en la Universidade de Vigo.

El objetivo es explorar proyectos Fortran desde una interfaz web: consultar métricas, localizar hallazgos en el código y, más adelante, comparar análisis. La aplicación analiza código fuente; no valida resultados científicos ni mide el rendimiento de los modelos.

## Dirección técnica

- **Motor:** Python, con un parser existente de Fortran; fparser2 es el primer candidato que se validará con ejemplos reales.
- **API:** FastAPI, separada del motor para permitir también su uso desde consola.
- **Frontend:** React y TypeScript.
- **Persistencia:** SQLite cuando se incorpore el historial.
- **Despliegue:** imagen Docker con frontend incluido, almacenamiento persistente y configuración mediante Docker Compose para TrueNAS. La compatibilidad se comprobará con la versión de destino.

## Estado

Repositorio inicial de planificación. Todavía no hay una aplicación nueva ejecutable ni instrucciones de instalación.

El [plan de migración](docs/MIGRATION.md) delimita las entregas y sus criterios de aceptación. Los acuerdos de trabajo están en [AGENTS.md](AGENTS.md).

## Referencia local

`reference/` conserva íntegra la copia del proyecto Java, incluidos sus recursos y compilados. Está excluida de Git y del contexto Docker: **no se sube a GitHub ni aparece al clonar este repositorio**. Se necesita una copia local independiente si se quiere consultar el original en otro equipo. No se debe borrar durante la migración.

El original sirve como referencia funcional, no como especificación de resultados correctos: varias métricas se basan en búsquedas de texto y necesitan revisión.

## Autoría y licencia

Se conserva en `LICENSE.txt` el aviso original GPL-3.0-o-posterior y la atribución a Michael García Rodríguez. Al reutilizar código, recursos o documentación, conservar sus avisos y revisar las licencias de las dependencias incorporadas.
