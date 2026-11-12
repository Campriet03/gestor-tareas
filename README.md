# Gestor de Tareas

Aplicación web para que equipos organicen su trabajo: crear equipos, invitar
personas, gestionar proyectos y mover tareas en un tablero (Por hacer → En
progreso → Hecha), con notificaciones de invitaciones y asignaciones.

![CI](https://github.com/Campriet03/gestor-tareas/actions/workflows/ci.yml/badge.svg)

## Capturas

| Tablero de tareas | Vista móvil |
|---|---|
| ![Tablero](docs/img/tablero.png) | <img src="docs/img/tablero-movil.png" alt="Vista móvil" width="260"> |

## Funcionalidades

- Registro e inicio de sesión (contraseñas con hash scrypt, sesión con JWT).
- Equipos con roles de **propietario** y **miembro**; solo se ve lo de los
  equipos propios.
- Invitaciones por correo: la persona acepta o rechaza desde la app.
- Proyectos por equipo y tablero de tareas con responsable y fecha límite
  (las vencidas se resaltan).
- Notificaciones (invitaciones, asignaciones) con consulta periódica cada 30 s.
- Requisitos completos en [`docs/requisitos.md`](docs/requisitos.md) y diagramas
  de arquitectura en [`docs/arquitectura.md`](docs/arquitectura.md).

## Stack

| Capa | Tecnología |
|------|------------|
| Frontend | HTML, CSS y JavaScript sin dependencias |
| Backend | Python 3.12 y Flask, en capas (rutas → servicios → repositorios) |
| API | REST con JSON bajo `/api/v1` |
| Autenticación | JWT (PyJWT) y scrypt (Werkzeug) |
| Base de datos | MySQL 8.0 en Docker (SQLite solo para pruebas rápidas) |
| Pruebas / CI | `unittest` y GitHub Actions |

## Puesta en marcha

Requisitos: Git, Python 3.12+ y Docker Desktop.

```powershell
git clone https://github.com/Campriet03/gestor-tareas.git
cd gestor-tareas
Copy-Item .env.example .env
```

Edita `.env`: define las contraseñas de la base y un `JWT_SECRET` largo y
aleatorio (sin espacios, comillas, `$` ni `#`). Luego:

```powershell
docker compose up -d                          # MySQL 8.0
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
python -m app.init_db                         # crea las tablas
python -m app.seed                            # opcional: datos de ejemplo
python run.py                                 # http://127.0.0.1:5000
```

Con los datos de ejemplo puedes entrar como `ana@demo.com` o `luis@demo.com`
(contraseña `demo-1234`).

MySQL solo lee las credenciales en el primer arranque. Si las cambias después,
recrea el volumen con `docker compose down -v` (borra los datos).

## Pruebas

```powershell
cd backend
python -m unittest discover -s tests -v       # 28 pruebas, SQLite en memoria
```

Cubren autenticación, permisos entre equipos, invitaciones, proyectos, tareas,
notificaciones y el adaptador de base de datos.

Contra MySQL real (con el contenedor levantado):

```powershell
$env:TEST_DATABASE_URL = "mysql://app:TU_CLAVE@127.0.0.1:3306/gestor_tareas"
python -m unittest discover -s tests -v
```

Las pruebas borran el contenido de las tablas: no las apuntes a una base con
datos que quieras conservar. Usa una base distinta para pruebas.

## API

Todas las rutas (salvo registro, login y salud) exigen
`Authorization: Bearer <token>`. Los errores tienen la forma
`{"error": {"code": "...", "message": "..."}}`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/register`, `/auth/login` | Crear cuenta / iniciar sesión |
| GET | `/auth/me` | Usuario actual |
| GET, POST | `/teams` | Mis equipos / crear equipo |
| GET | `/teams/:id` | Detalle y miembros |
| POST | `/teams/:id/invitations` | Invitar por correo (propietario) |
| GET | `/invitations` | Mis invitaciones pendientes |
| POST | `/invitations/:id/accept`, `/decline` | Responder invitación |
| GET, POST | `/teams/:id/projects` | Proyectos del equipo |
| GET | `/projects/:id` | Detalle de proyecto |
| GET, POST | `/projects/:id/tasks` | Tareas (`?status=todo\|doing\|done`) / crear |
| PATCH, DELETE | `/tasks/:id` | Editar / eliminar tarea |
| GET | `/notifications` | Notificaciones y cantidad sin leer |
| POST | `/notifications/:id/read`, `/read-all` | Marcar como leídas |
| GET | `/health` | Estado del servicio |

## Estructura

```
gestor-tareas/
├── backend/
│   ├── app/            rutas, servicios, repositorios, db, auth
│   ├── db/             schema.mysql.sql (real) y schema.sqlite.sql (pruebas)
│   ├── tests/          pruebas de integración
│   └── run.py
├── frontend/           index.html, styles.css, app.js
├── docs/               requisitos, arquitectura, ADR y capturas
├── docker-compose.yml  MySQL 8.0
└── .github/workflows/  CI
```

## Decisiones de arquitectura

Documentadas en [`docs/adr`](docs/adr/README.md): monolito (0001), MySQL en
Docker (0002), JWT (0003), backend en capas (0004), API REST (0005),
notificaciones por consulta periódica (0006) y pruebas con CI (0007).

## Limitaciones conocidas

- Los JWT no se pueden revocar antes de expirar (duran 1 hora; ver ADR 0003).
- No hay recuperación de contraseña ni tokens de refresco.
- Las notificaciones llegan con hasta 30 s de retraso (ADR 0006).
- No hay edición ni eliminación de equipos y proyectos.
- No se aplican límites de intentos de inicio de sesión.
- Sin sistema de migraciones: el esquema se aplica con `app.init_db`.

## Roadmap

- [ ] Migraciones de base de datos
- [ ] Tokens de refresco y recuperación de contraseña
- [ ] Edición y eliminación de equipos y proyectos
- [ ] Notificaciones en tiempo real (SSE)
- [ ] Contenedor para el backend

## Autor

**Camilo Alejandro Prieto Villarreal**
GitHub: [@Campriet03](https://github.com/Campriet03)

## Licencia

[MIT](LICENSE)
