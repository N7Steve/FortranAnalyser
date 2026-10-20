# Corpus de validación

Estos ejemplos sintéticos se han escrito para este repositorio y se distribuyen bajo la licencia del proyecto. No contienen modelos ni datos de terceros. Son representativos de estructuras del lenguaje, no de un modelo científico completo.

`project/` es un proyecto de ejemplo de dos archivos para el recorrido de consola:

| Archivo | Resultado esperado |
| --- | --- |
| `modern.f90` | 1 módulo, 1 subrutina, 1 función, 6 declaraciones, 12 entidades declaradas, 2 bucles, profundidad máxima 2 y 1 `CALL`; `IMPLICIT NONE` heredado por las rutinas, sin hallazgos. |
| `legacy.f` | 1 subrutina, 1 declaración con 3 entidades, 2 bucles con etiqueta terminal compartida, profundidad 2; aviso FA001 por ausencia de `IMPLICIT NONE`. |

El resto de casos se define directamente en las pruebas para mantener cada entrada junto a su expectativa: comentarios, continuaciones, `END` sin nombre, ámbitos, interfaces, tipos derivados, preprocesado, inclusiones, sintaxis inválida y límites de ejecución.

Queda pendiente contrastar el motor con modelos reales aportados por sus propietarios antes de afirmar compatibilidad con esos proyectos.
