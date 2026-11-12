# Requisitos

Sistema: **Gestor de Tareas**, aplicación web para que equipos organicen
proyectos y tareas. Autor: Camilo Prieto. Fecha: 2026-11-11.

Cada requisito tiene un código que se cita en los [ADR](adr/README.md) y una
forma concreta de verificarlo. Las pruebas están en `backend/tests/`.

## Alcance

**Incluye:** cuentas de usuario, equipos con roles, invitaciones, proyectos,
tareas con responsable y fecha límite, tablero por estado y notificaciones.

**No incluye:** recuperación de contraseña, edición o eliminación de equipos y
proyectos, comentarios o archivos adjuntos en tareas, notificaciones en tiempo
real ni aplicación móvil nativa.

## Requisitos funcionales

| Código | Requisito | Criterio de aceptación | Verificado por |
|--------|-----------|------------------------|----------------|
| RF-01 | Registro e inicio de sesión | Una persona crea una cuenta con nombre, correo y contraseña (mínimo 8 caracteres) e inicia sesión. No se aceptan correos repetidos ni credenciales incorrectas. | `AuthTests` |
| RF-02 | Gestión de equipos | Un usuario crea equipos y queda como propietario. Ve solo sus equipos y la lista de miembros de cada uno. | `TeamTests.test_create_and_list_teams_are_private`, `test_team_name_required` |
| RF-03 | Invitaciones | El propietario invita por correo a una persona registrada. Esa persona acepta o rechaza. Al aceptar pasa a ser miembro. No se duplican invitaciones ni se invita a quien ya pertenece. | `TeamTests.test_invitation_flow`, `test_decline_does_not_add_member`, `test_invitation_rules` |
| RF-04 | Gestión de proyectos | Cualquier miembro crea y lista los proyectos de su equipo. | `ProjectAndTaskTests.test_projects` |
| RF-05 | Gestión de tareas | Un miembro crea, edita y elimina tareas con título, descripción, estado y fecha límite. Solo el propietario o quien creó la tarea puede eliminarla. | `test_task_crud`, `test_task_validation`, `test_delete_permissions` |
| RF-06 | Asignación de tareas | Una tarea se asigna a un miembro del equipo o se deja sin asignar. No se puede asignar a alguien de fuera. | `test_task_validation`, `test_assignment_creates_notification_and_clears_with_null` |
| RF-07 | Seguimiento por estado | Las tareas tienen estado Por hacer, En progreso o Hecha, se mueven en un tablero y se filtran por estado. Las vencidas se resaltan. | `test_status_filter`, `test_task_crud` y prueba manual del tablero |
| RF-08 | Notificaciones | Se avisa al usuario cuando lo invitan a un equipo o le asignan una tarea, y al propietario cuando responden su invitación. Se marcan como leídas de una en una o todas. | `NotificationTests`, `test_invitation_flow`, `test_assignment_creates_notification_and_clears_with_null` |

## Requisitos no funcionales

| Código | Categoría | Requisito | Verificación |
|--------|-----------|-----------|--------------|
| RNF-01 | Seguridad | Las contraseñas se guardan con hash, nunca en texto plano. Las rutas privadas exigen un token válido y vigente. Un usuario solo accede a los datos de sus equipos (403 si no pertenece). | `test_password_is_hashed`, `test_protected_routes_need_valid_token`, `test_outsider_cannot_touch_team_data` |
| RNF-02 | Rendimiento | Las consultas frecuentes (tareas por proyecto, notificaciones por usuario, invitaciones por correo) usan claves e índices, sin recorrer tablas completas. | Revisión de `schema.mysql.sql`. No se hicieron pruebas de carga. |
| RNF-03 | Mantenibilidad | El backend se organiza en capas con responsabilidades separadas y se prueba de forma automática. | Estructura de `backend/app` y 28 pruebas |
| RNF-04 | Portabilidad | Cualquiera clona el repositorio y lo ejecuta con Docker, un archivo `.env` y pocos comandos. Los cambios se verifican en integración continua. | `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml` |
| RNF-05 | Integridad de datos | Los datos relacionados se mantienen consistentes mediante claves foráneas, restricciones de valores válidos y transacciones. | `test_sqlite_transaction_rolls_back`, restricciones de `schema.mysql.sql` |
| RNF-06 | Usabilidad | La interfaz funciona en escritorio y móvil, se maneja con teclado y los controles tienen etiquetas accesibles. | Capturas en `docs/img/` y prueba de navegador |

## Restricciones

- Plazo de 2 semanas y una sola persona (ADR 0001).
- Base de datos relacional MySQL 8.0 (ADR 0002).
- Sin servicios de pago ni dependencias externas en ejecución.

## Trazabilidad con las decisiones

| Requisito | Decisión que lo atiende |
|-----------|-------------------------|
| RNF-01 | ADR 0003 (autenticación), ADR 0004 (permisos en los servicios) |
| RNF-02 | ADR 0002 (base de datos), ADR 0005 (API REST) |
| RNF-03 | ADR 0001 (monolito), ADR 0004 (capas), ADR 0007 (pruebas) |
| RNF-04 | ADR 0001, ADR 0007 (Docker y CI) |
| RNF-05 | ADR 0001, ADR 0002 (base relacional) |
| RF-08 | ADR 0006 (notificaciones por consulta periódica) |
