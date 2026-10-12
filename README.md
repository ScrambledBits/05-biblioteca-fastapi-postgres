# Biblioteca (FastAPI + PostgreSQL)

API REST para una biblioteca imaginaria: permite listar libros, agregar nuevos, prestarlos, devolverlos y borrarlos. Está construida con **FastAPI**, guarda los datos en **PostgreSQL** y gestiona sus dependencias con **uv**, el gestor de proyectos Python moderno. Incluye documentación interactiva generada automáticamente (Swagger UI).

> Proyecto con fines exclusivamente educativos. No tiene usuarios, autenticación ni control de concurrencia avanzado.

---

## Nivel y objetivos de aprendizaje

**Nivel:** intermedio.

Al dockerizar esta aplicación vas a practicar:

- Dockerizar un proyecto Python moderno basado en **`pyproject.toml` + `uv.lock`** (en lugar de `requirements.txt`).
- Traer un binario (uv) **desde otra imagen** sin instalarlo con un gestor de paquetes.
- Instalar dependencias de forma **reproducible** y **sin dependencias de desarrollo**.
- Usar un **build multi-etapa** para que la imagen final no contenga herramientas de construcción.
- Servir una app **ASGI** con Uvicorn.
- Configurar PostgreSQL con su imagen oficial y una **cadena de conexión** (`DATABASE_URL`).
- Usar **perfiles** de Compose para servicios opcionales (por ejemplo, pgAdmin).

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12 o superior (el archivo `.python-version` sugiere 3.13) |
| Framework web | FastAPI |
| Servidor ASGI | Uvicorn |
| Validación | Pydantic v2 (incluido con FastAPI) |
| Driver de base de datos | psycopg 3 (paquete `psycopg[binary]`, que ya incluye `libpq`) |
| Base de datos | PostgreSQL 16 o 17 |
| Gestor de dependencias | uv |

---

## Arquitectura

```
 Cliente HTTP ──▶  api (FastAPI + Uvicorn, puerto 8000)
 (navegador,          │   /docs  → Swagger UI
  curl, Postman)      │   /libros → recursos REST
                      │
                      │  TCP 5432 (protocolo PostgreSQL)
                      ▼
                    db (PostgreSQL)
                      └─ tabla "libros"
```

Al arrancar, la API (función `ciclo_de_vida` en `main.py`):

1. Se conecta a PostgreSQL usando `DATABASE_URL`.
2. Crea la tabla `libros` si no existe.
3. Si la tabla está vacía, inserta cuatro libros de ejemplo.

Si PostgreSQL **no está disponible** en ese momento, la app **falla al arrancar**.

---

## Estructura del proyecto

```
05-biblioteca-fastapi-postgres/
├── app/
│   ├── __init__.py      # Marca la carpeta como paquete Python
│   ├── main.py          # Rutas de FastAPI, modelos Pydantic y arranque
│   └── db.py            # Conexión a PostgreSQL, creación de tabla y datos iniciales
├── pyproject.toml       # Metadatos y dependencias del proyecto
├── uv.lock              # Versiones exactas de todas las dependencias (no editar a mano)
├── .python-version      # Versión de Python sugerida para uv
├── README.md
└── CHANGELOG.md
```

Detalles importantes:

- **`pyproject.toml`**: las dependencias de ejecución están en `[project].dependencies`. La herramienta de *linting* (`ruff`) está en el grupo de **desarrollo** `[dependency-groups].dev`, que **no** debería acabar en la imagen final.
- **`uv.lock`**: garantiza que todos instalen exactamente lo mismo. uv tiene opciones para **exigir** que el lockfile esté al día y para **no modificarlo**; investígalas.
- **`app/main.py`**
  - El objeto ASGI se llama `app` y vive en el módulo `app.main`. Ese dato es lo que necesita Uvicorn.
  - La ruta `/` devuelve el nombre del contenedor y el valor de `APP_ENV`, útil para comprobar que las variables llegan.
- **`app/db.py`**: abre una conexión por petición (sencillo, aunque no es lo más eficiente; un *pool* sería el siguiente paso).

---

## Variables de entorno

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql://biblioteca:biblioteca@localhost:5432/biblioteca` | Cadena de conexión: `postgresql://USUARIO:CLAVE@HOST:PUERTO/BASE`. |
| `APP_ENV` | `desarrollo` | Texto informativo devuelto por `/`. |

La imagen oficial de PostgreSQL usa sus propias variables para crear el usuario, la contraseña y la base de datos en el primer arranque (prefijo `POSTGRES_`). Deben ser coherentes con `DATABASE_URL`.

---

## API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Información de la app y del contenedor. |
| `GET` | `/health` | `200` si PostgreSQL responde; `503` si no. |
| `GET` | `/docs` | Documentación interactiva (Swagger UI). |
| `GET` | `/libros` | Lista todos los libros. Con `?disponibles=true`, solo los no prestados. |
| `GET` | `/libros/{id}` | Un libro; `404` si no existe. |
| `POST` | `/libros` | Crea un libro. Cuerpo: `{"titulo": "...", "autor": "...", "anio": 1949}`. `422` si los datos no son válidos. |
| `POST` | `/libros/{id}/prestamo` | Marca el libro como prestado; `409` si ya lo estaba. |
| `DELETE` | `/libros/{id}/prestamo` | Devuelve el libro; `409` si no estaba prestado. |
| `DELETE` | `/libros/{id}` | Borra el libro; `204` si se borró. |

---

## Ejecución local sin Docker (referencia)

1. Instala uv y ten un PostgreSQL local con un usuario y base de datos creados.
2. Sincroniza el entorno con uv (crea `.venv` e instala lo del lockfile).
3. Ejecuta Uvicorn a través de uv, indicando el objeto ASGI (`módulo:variable`), el host y el puerto.
4. Abre `/docs` en el navegador.

---

## Reto: dockerizar la aplicación

> Pistas, no soluciones.

### Parte 1: el `Dockerfile`

1. **Imagen base:** imagen oficial de Python (`slim`) con versión explícita compatible con `requires-python`.
2. **Obtener uv:** la documentación de uv explica cómo **copiar el binario** desde su imagen oficial publicada en un registro de contenedores. Usa una versión fija de uv, no `latest`.
3. **Primero dependencias, luego código:** copia `pyproject.toml` y `uv.lock`, instala **solo las dependencias** (sin el proyecto) y después copia `app/`. Investiga la opción de uv que instala dependencias sin instalar el proyecto en sí.
4. **Sin dependencias de desarrollo** y **con lockfile congelado**: busca las opciones correspondientes del comando de sincronización.
5. **Variables útiles de uv en Docker:** lee la guía de integración de uv con Docker; menciona variables para compilar *bytecode* y para el modo de enlace de la caché.
6. **Multi-etapa:** en una etapa construyes el entorno virtual (`.venv`) con uv; en la etapa final copias **solo** el `.venv` y el código. La imagen final **no necesita uv**.
7. **`PATH`:** si no usas uv en la etapa final, ¿cómo encuentra el sistema el ejecutable `uvicorn` que está dentro de `.venv`? (pista: agrega la carpeta `bin` del entorno virtual al `PATH`).
8. **Usuario sin privilegios**, **puerto** documentado y Uvicorn escuchando en `0.0.0.0`.
9. **`.dockerignore`:** excluye `.venv` local, cachés, `.git`… Un `.venv` creado en macOS o Windows **no funciona** dentro de un contenedor Linux.

### Parte 2: el `docker-compose.yml`

1. Servicios: **api** (tu imagen) y **db** (PostgreSQL oficial, versión explícita; compara las variantes `alpine` y Debian).
2. Variables `POSTGRES_*` para la base y `DATABASE_URL` para la API, con el **nombre del servicio** como host. Usa un archivo `.env` (ignorado por git) para la contraseña.
3. **Volumen con nombre** para los datos de PostgreSQL. Atención: a partir de PostgreSQL 18 la ruta recomendada de montaje cambió respecto a versiones anteriores. Lee la documentación de la imagen para la versión que elijas.
4. **Healthcheck** de la base usando la utilidad incluida en PostgreSQL que comprueba si el servidor acepta conexiones.
5. La API espera a que la base esté **sana**.
6. Agrega **pgAdmin** como servicio opcional usando un **perfil** de Compose, para que solo arranque cuando lo pidas explícitamente.
7. Publica solo el puerto de la API (y el de pgAdmin cuando su perfil esté activo).

### Criterios de aceptación

- [ ] `/docs` abre y permite probar todas las rutas.
- [ ] La lista inicial tiene 4 libros y los cambios **persisten** tras recrear los contenedores.
- [ ] La imagen final **no** incluye `ruff` ni el binario de uv.
- [ ] La imagen final pesa **menos de 100 MB más** que la imagen base de Python que elegiste (compara ambas en tu listado de imágenes).
- [ ] Cambiar solo código en `app/` y reconstruir **no** reinstala dependencias.
- [ ] pgAdmin **no** arranca por defecto; solo al activar su perfil.
- [ ] El proceso no corre como `root`.

### Retos extra

- Usa un **montaje de caché** de BuildKit para la caché de uv y mide la diferencia en tiempos de reconstrucción.
- Agrega un `compose.override.yml` de desarrollo con recarga automática de Uvicorn.
- Ejecuta varias réplicas de la API detrás de un proxy inverso.
- Cambia la imagen final a una *distroless* de Python y discute qué se gana y qué se pierde.

---

## Errores comunes

| Síntoma | Causa probable |
|---|---|
| `connection to server at "localhost"... failed` | `DATABASE_URL` no está definida o apunta a `localhost`. |
| `password authentication failed` | Credenciales distintas entre `POSTGRES_*` y `DATABASE_URL`, o volumen inicializado con otra contraseña. |
| `uvicorn: not found` | El `PATH` no incluye `.venv/bin`, o copiaste el `.venv` a otra ruta distinta de la original. |
| `The lockfile at uv.lock needs to be updated` | Editaste `pyproject.toml` sin regenerar `uv.lock`. |
| La API se cae al arrancar con todo nuevo | No espera a que PostgreSQL esté sano. |

---

## Referencias

- uv en Docker (guía oficial): <https://docs.astral.sh/uv/guides/integration/docker/>
- FastAPI en contenedores: <https://fastapi.tiangolo.com/deployment/docker/>
- Imagen oficial de PostgreSQL: <https://hub.docker.com/_/postgres>
- Imagen oficial de Python: <https://hub.docker.com/_/python>
- Perfiles de Compose: <https://docs.docker.com/compose/how-tos/profiles/>
- Caché de builds: <https://docs.docker.com/build/cache/optimize/>
