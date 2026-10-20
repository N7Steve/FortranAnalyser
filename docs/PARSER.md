# Evaluación de fparser2 — fase 1

## Decisión

Se adopta provisionalmente **fparser 0.2.5**, con la gramática `f2008` de fparser2. La dependencia está fijada porque el motor utiliza sus clases AST y un adaptador del lector para impedir la expansión automática de `INCLUDE`.

La [documentación oficial de fparser2](https://fparser.readthedocs.io/en/stable/fparser2.html) describe soporte de Fortran 2003 y parte de Fortran 2008. Es un parser sintáctico: que un archivo se pueda interpretar no demuestra que compile, que sus tipos sean correctos ni que su modelo científico sea válido.

La evaluación usa ejemplos sintéticos propios bajo la licencia del proyecto, con expectativas en [el corpus](../tests/fixtures/README.md), y regresiones definidas junto a sus entradas en las pruebas. Permite verificar la selección técnica; sigue pendiente validarla con modelos reales de los usuarios. Una comprobación local adicional del `DISTANCE.f90` original reconoce 1 función, 12 declaraciones/entidades de datos, 1 bucle y `IMPLICIT NONE`; esa copia ignorada no es una dependencia de las pruebas.

## Compatibilidad comprobada

- Formatos libre y fijo, comentarios, comentarios al final de instrucciones y continuaciones en ambos formatos.
- Programas con y sin cabecera, módulos, subrutinas, funciones y bloques de datos.
- Terminación con `END`, declaraciones con varias entidades, arrays e inicializadores con comas.
- Bucles `DO` anidados, consecutivos y con etiquetas terminales compartidas.
- `IMPLICIT NONE` propio o heredado del host dentro del mismo archivo, sin confundir interfaces con implementaciones.
- Separación entre identificadores/literales y palabras clave: `shadow`, texto que contiene `DO`, `CALL` o `!`.

El formato automático usa `.f`, `.for`, `.ftn` y `.f77` como fijo; `.f90`, `.f95`, `.f03`, `.f08` y `.h90` como libre, sin distinguir mayúsculas. La extensión no garantiza una versión de lenguaje. Un `.h90` que solo contenga un fragmento puede no constituir una unidad interpretable.

## Métricas y ámbitos

- `physical_lines`: líneas físicas, incluidas líneas vacías y comentarios. No son instrucciones ni líneas ejecutables.
- `declarations`: instrucciones de declaración de tipo de datos, no todas las instrucciones de especificación.
- `declared_entities`: entidades en esas declaraciones; incluye argumentos declarados, constantes y resultados explícitos. No estima memoria ni cuenta variables implícitas, ni deduplica declaraciones inválidas.
- `functions`, `subroutines`, `modules`, `programs`: implementaciones/unidades encontradas en el AST, incluidas rutinas internas.
- `calls`: instrucciones `CALL`; no incluye llamadas a funciones dentro de expresiones ni resuelve el destino.
- `loops`, `max_loop_depth`: bucles `DO` y máxima profundidad estructural. No son una estimación de complejidad temporal.
- Los ámbitos contienen ubicación, nombre cualificado, `implicit_none` efectivo y métricas propias que no acumulan las de rutinas internas.

Los cuerpos de interfaces y las definiciones de tipos derivados se excluyen de las métricas de implementaciones y variables locales. Los ámbitos de bloque de datos se incluyen en `scopes`, sin un contador agregado específico. No se calcula complejidad ciclomática ni nota global.

## Reglas

| Regla | Gravedad | Significado |
| --- | --- | --- |
| FA001 | warning | Un ámbito no tiene `IMPLICIT NONE` propio ni heredado del host local. Una asociación por `USE` no lo hereda. |
| FA002 | info | Se alcanza profundidad de cuatro bucles; sugiere revisar legibilidad y no afirma un problema de rendimiento. |
| FA100 | error | Sintaxis inválida o no soportada por el parser; no se puede distinguir de forma general entre ambas. |
| FA101 | warning | `INCLUDE` no expandido; se necesita contexto. |
| FA102 | warning | Preprocesado no evaluado. |
| FA103 | warning | Submódulo cuyo host externo no se resuelve todavía. |
| FA104 | error | Error interno o terminación inesperada del proceso de análisis. |
| FA105 | error | Tiempo de análisis agotado. |
| FA106 | error | Archivo omitido por tamaño, enlace simbólico o tipo de archivo. |
| FA107 | error | Error de lectura o codificación. |

## Estados y límites explícitos

`ok` significa que el análisis sintáctico se completó dentro del alcance documentado; puede contener avisos. `partial` identifica fuentes con inclusiones, preprocesado o submódulos pendientes de contexto. `failed` indica error de lectura/parser o tiempo agotado. `skipped` identifica archivos omitidos por límites o enlaces.

En archivos parciales no se publican métricas AST: `metrics` es `null` y `scopes` está vacío. Las líneas físicas siguen disponibles si se leyó la fuente. No se mezclan ramas `#if`, no se ejecuta un preprocesador y no se abren archivos incluidos, aunque existan o usen rutas absolutas. El adaptador utiliza `_next()` de fparser para evitar la apertura automática que realiza `next()`; cualquier cambio de versión necesita repetir sus pruebas.

El formato fijo sigue el lector estándar de fparser, incluida su interpretación de columnas; no se habilitan extensiones de longitud de línea. No se promete soporte completo de Fortran 2008/2018, OpenMP, extensiones de compilador, `ENTRY`, resolución de símbolos o semántica entre archivos. Las directivas OpenMP en comentarios no activan una configuración de compilación.

Solo se decodifica UTF-8 (con o sin BOM). La búsqueda excluye `.git`, `.venv`, `venv`, `node_modules`, `reference` y `__pycache__` y no recorre directorios simbólicos. Cada fuente se procesa secuencialmente en un proceso nuevo con tiempo limitado. Hay límite de archivos y tamaño de lectura, pero no una cuota estricta de memoria ni límite global de duración; el aislamiento de entradas de usuarios pertenece a la fase web.

## Siguiente validación

Probar modelos reales con permiso de sus propietarios y documentar qué configuraciones necesitan. Resolver inclusiones y preprocesado exige un diseño explícito de contexto y seguridad; no se debe añadir ejecución de scripts de compilación como atajo. La primera web puede consumir el contrato JSON y mostrar claramente estos estados sin ocultar las limitaciones.
