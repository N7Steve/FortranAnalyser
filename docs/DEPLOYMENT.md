> Estado actual: no hay cuotas de subida, extracción, fuentes, duración, cola o informes en la aplicación. Los Compose tampoco fijan cuotas de CPU/RAM/procesos. La web sigue enviando bloques de 8 MiB por compatibilidad con proxies; esto no limita el tamaño total. `/api/config` anuncia `max_upload_bytes: null`. Los valores numéricos de límites en las notas de diagnóstico siguientes describen versiones anteriores. Véase [comportamiento actual](WEB.md).

# Docker y TrueNAS

La imagen incluye Python, motor, API y web compilada con tipografías locales. Node y uv solo se usan durante la construcción. La referencia Java, los datos y las herramientas de desarrollo no forman parte de la imagen final.

## TrueNAS: pegar el YAML y construir desde Git

Archivo: [`deploy/truenas.yaml`](../deploy/truenas.yaml).

1. Usar TrueNAS con Apps basadas en Docker Compose (24.10 o posterior), pool de aplicaciones configurado y acceso a Internet para descargar Git y dependencias.
2. El YAML descarga el contenido publicado en `main` desde GitHub. El repositorio debe ser accesible sin autenticación desde el constructor.
3. Abrir **Apps → Discover Apps → Install via YAML**, indicar un nombre como `fortran-analyser` y pegar el archivo completo.
4. Guardar y esperar la construcción. No necesita un clon previo ni acceso al socket Docker desde la aplicación.
5. Acceder a **`http://IP_DEL_TRUENAS:8890/`**. Si el puerto está ocupado, cambiar solo el `8890` de `8890:8000`.

El contexto `https://github.com/N7Steve/FortranAnalyser.git#main` descarga `main` y utiliza su Dockerfile raíz. La sintaxis de fragmento Git mantiene compatibilidad con versiones anteriores de Compose. `pull_policy: build` solicita la construcción; no se referencia ninguna imagen publicada inexistente.

Referencias oficiales: [TrueNAS: aplicaciones personalizadas y construcción con Dockerfile](https://apps.truenas.com/managing-apps/installing-custom-apps/), [Compose: contexto Git](https://docs.docker.com/reference/compose-file/build/#context), [Docker: descarga de repositorios](https://docs.docker.com/build/concepts/context/#git-repositories). La interfaz y la versión de Compose del NAS pueden variar; las pruebas locales de Docker no equivalen a una instalación en vuestro TrueNAS concreto.

## Datos y permisos

El volumen `analyses` está montado en `/data`. Conserva fuentes extraídas, metadatos e informes al reiniciar o recrear el contenedor. No se conserva el ZIP original. **No eliminar el volumen al actualizar.**

Para usar un dataset propio, crear por ejemplo `/mnt/TU_POOL/apps/fortran-analyser`, conceder lectura/escritura al UID/GID **568:568** y sustituir `analyses:/data` por el bloque de montaje comentado en el YAML. `create_host_path: false` impide crear silenciosamente una ruta incorrecta. No cambiar recursivamente los permisos de un dataset compartido con otras aplicaciones.

El proceso arranca como 568:568, con raíz de solo lectura. Escribe en `/data` y en áreas temporales del contenedor; `/tmp` usa tmpfs sin un tamaño fijo configurado por el Compose. La imagen prepara los permisos del volumen Docker, pero no modifica los de un dataset del NAS. Si falta permiso, el servicio falla al arrancar.

Cada identificador reside en `/data/analyses/{id}` y contiene un `.analysis.json` con escritura mediante reemplazo atómico. Se restauran resultados al reiniciar. Trabajos interrumpidos se marcan fallidos y sus fuentes incompletas se limpian, sin reejecución automática. Registros corruptos o ajenos se ignoran y no se borran.

La API `GET /api/analyses` lista los identificadores conservados; `DELETE /api/analyses/{id}` elimina un trabajo terminado y sus fuentes. Se mantienen ocho resultados como máximo. La pestaña recuerda su último identificador; un nuevo análisis sustituye al anterior. Esta persistencia no incorpora todavía comparaciones ni un historial visual con SQLite.

## Configuración

| Variable | Valor de la imagen | Uso |
| --- | --- | --- |
| `FORTRAN_BIND_HOST` | `0.0.0.0` | Escucha dentro del contenedor. |
| `FORTRAN_PORT` | `8000` | Puerto interno; ajustar también el mapeo si se cambia. |
| `FORTRAN_ALLOWED_HOSTS` | `*` | Permite acceder por la IP o DNS del NAS. Se puede restringir con una lista como `192.168.1.20,truenas.local`. Localhost sigue permitido para la comprobación de salud. |
| `FORTRAN_DATA_DIR` | `/data` | Activa persistencia. Sin esta variable, el arranque local usa datos temporales. |
| `FORTRAN_FRONTEND_DIR` | `/app/frontend` | Web compilada incluida en la imagen. |

El YAML no fija cuotas de RAM, CPU ni procesos. Mantener **una instancia y un trabajador HTTP** por directorio de datos. La aplicación no impone cuotas de carga o análisis.

La aplicación es para una red de confianza, sin cuentas ni separación entre usuarios: el puerto publicado da acceso a las fuentes e informes. Para acceso desde Internet haría falta autenticación y HTTPS, no incluidos en este despliegue.

## Docker local

```sh
docker compose up -d --build --wait
docker compose ps
docker compose logs --tail=100
```

Abrir `http://localhost:8890/`. El Compose local admite `FORTRAN_HOST_PORT` para cambiarlo. El YAML de TrueNAS es independiente de archivos `.env`: se editan sus valores directamente.

Para detener sin borrar datos, usar `docker compose down`. `docker compose down --volumes` borra también los datos y no debe usarse para una actualización normal.

## Actualizaciones

Reiniciar el contenedor no descarga cambios de Git. Hay que reconstruir con el contexto actualizado. En TrueNAS, usar la edición/reimplementación que vuelva a construir la app; los nombres exactos dependen de la versión. El botón dedicado a actualizar imágenes publicadas no es el flujo de esta aplicación construida desde código.

Para una instalación gestionada directamente por Compose:

```sh
docker compose -f deploy/truenas.yaml build --pull
docker compose -f deploy/truenas.yaml up -d --no-build --wait
```

No ejecutar un segundo proyecto Compose sobre una aplicación ya creada desde la interfaz de TrueNAS: tendría otro nombre de proyecto y otro volumen. Gestionar esa instalación desde TrueNAS.

Para fijar una versión o volver a otra anterior, sustituir `#main` por un SHA completo publicado y reconstruir, conservando el volumen. Python y npm usan lockfiles. Las etiquetas de las imágenes base reciben actualizaciones; sus digest se pueden fijar en el Dockerfile de una versión concreta si se necesita congelarlas también.

## Verificación

```sh
docker compose config --quiet
docker compose -f deploy/truenas.yaml config --quiet
docker build --target test -t fortran-analyser-tests .
python scripts/smoke_container.py
```

La etapa `test` ejecuta las pruebas Python en Linux, sin añadir sus dependencias a la imagen final. La prueba de contenedor crea un proyecto Compose propio, comprueba web, API, ejemplo, descarga, permisos y recreación con datos conservados. Elimina solo los recursos sintéticos de esa prueba al terminar. Necesita Docker y un puerto libre; admite `--port` para cambiar el de prueba.


### Espacio para cargas grandes

No hay un máximo de subida o expansión en la aplicación. Los comprimidos y temporales se guardan en el volumen de análisis. El espacio requerido depende del tamaño del archivo, su contenido expandido, las cargas en cola y los informes retenidos. El Compose no limita la memoria o CPU. Los proxies externos mantienen sus propias restricciones; la web envía bloques de 8 MiB para reducir el tamaño de cada petición sin limitar el archivo completo.


### HTTP 413 y discrepancias entre web y API

La etiqueta `0.2.0` se ha mantenido en varias entregas y no distingue sus capacidades. La barra de progreso pertenece al frontend: no confirma que la API o el proxy tengan el mismo límite.

Abrir `/api/config` en el mismo origen y comprobar `max_upload_bytes`: esta versión informa `null` (sin cuota). Las entregas anteriores pueden no incluir ese campo; su ausencia no permite determinar por sí sola qué límite tienen. Un mensaje JSON que diga «10 MB» indica que la petición alcanza un servidor con el límite antiguo. Un 413 sin JSON puede proceder de un servidor HTTP o un proxy; comprobar la respuesta y comparar el dominio con el acceso directo a `http://IP_DEL_TRUENAS:8890`.

En un despliegue Compose local, desde el directorio del repositorio: `git pull --ff-only`, `docker compose build --pull --no-cache` y `docker compose up -d --force-recreate`. En Apps de TrueNAS, reconstruir desde el contexto Git actual y recrear la aplicación conservando el volumen. Reiniciar el contenedor existente no reconstruye su imagen. Un proxy externo requiere ajustar su propio límite; la aplicación no puede modificarlo.


### Construcción coherente de web y backend

La caché de uv para paquetes locales podía reutilizar un wheel antiguo al cambiar solo `backend/`, conservando la versión 0.2.0. El Dockerfile ahora limpia exclusivamente ese paquete antes de instalarlo y `tool.uv.cache-keys` incorpora sus fuentes. Las pruebas de la imagen se ejecutan directamente con el intérprete instalado, sin que `uv run` lo sustituya por una instalación editable; se comparan los archivos Python del wheel con el checkout.

La API directa de la instalación comunicada devolvió HTTP 413 con «El archivo supera los 10 MB.» aunque su web ya tenía progreso: queda confirmado un backend con límite antiguo. La reutilización de caché es una causa compatible, sin acceso para inspeccionar el contenedor remoto. Tras reconstruir, `/api/config` debe informar `max_upload_bytes: null` y `upload_chunk_bytes: 8388608`.

La web usa ahora peticiones independientes de hasta 8 MiB (`POST /api/uploads`, `PUT /api/uploads/{id}?offset=...`, `POST /api/uploads/{id}/complete?size=...`), para evitar enviar archivos grandes en una sola petición a Cloudflare. El orden y tamaño total se verifican en disco. Cancelar borra la carga temporal; no hay caducidad automática de reservas por tiempo. Las cargas abandonadas pueden eliminarse desde la lista de análisis. No hay cuotas de tamaño de archivo, cantidad de entradas o fuentes ni duración de análisis.
