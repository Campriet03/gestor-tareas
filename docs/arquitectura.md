# Arquitectura

Resumen visual de las decisiones de [`adr/`](adr/README.md).

## Componentes

```mermaid
flowchart LR
  B["Navegador<br/>HTML, CSS y JS"] -->|"REST + JSON<br/>Bearer JWT"| R["routes.py<br/>rutas y controladores"]
  R --> S["services.py<br/>reglas y permisos"]
  S --> P["repositories.py<br/>SQL"]
  P --> D["db.py<br/>adaptador"]
  D -->|producción| M[("MySQL 8.0<br/>Docker")]
  D -->|pruebas| Q[("SQLite<br/>en memoria")]
```

Cada capa solo habla con la siguiente (ADR 0004). El navegador consulta las
notificaciones cada 30 segundos (ADR 0006).

## Modelo de datos

```mermaid
erDiagram
  USERS ||--o{ TEAM_MEMBERS : "pertenece"
  TEAMS ||--o{ TEAM_MEMBERS : "tiene"
  TEAMS ||--o{ PROJECTS : "contiene"
  PROJECTS ||--o{ TASKS : "contiene"
  USERS ||--o{ TASKS : "es responsable de"
  USERS ||--o{ NOTIFICATIONS : "recibe"
  TEAMS ||--o{ TEAM_INVITATIONS : "genera"

  USERS {
    int id PK
    string name
    string email UK
    string password_hash
  }
  TEAMS {
    int id PK
    string name
    int owner_id FK
  }
  TEAM_MEMBERS {
    int team_id PK
    int user_id PK
    string role "owner o member"
  }
  TEAM_INVITATIONS {
    int id PK
    int team_id FK
    string email
    int invited_by FK
    string status "pending, accepted, declined"
  }
  PROJECTS {
    int id PK
    int team_id FK
    string name
    string description
  }
  TASKS {
    int id PK
    int project_id FK
    string title
    string status "todo, doing, done"
    int assignee_id FK
    int created_by FK
    date due_date
  }
  NOTIFICATIONS {
    int id PK
    int user_id FK
    string message
    bool is_read
  }
```

Las claves foráneas, las restricciones `CHECK` y las transacciones mantienen la
integridad de los datos (ADR 0002).

## Inicio de sesión y acceso a un recurso

```mermaid
sequenceDiagram
  participant U as Navegador
  participant A as API
  participant DB as MySQL
  U->>A: POST /auth/login (correo, contraseña)
  A->>DB: busca el usuario
  A->>A: verifica el hash scrypt
  A-->>U: JWT (1 hora)
  U->>A: GET /projects/7/tasks (Bearer JWT)
  A->>A: valida firma y expiración
  A->>DB: ¿el usuario pertenece al equipo del proyecto?
  alt pertenece
    A-->>U: 200 con las tareas
  else no pertenece
    A-->>U: 403
  end
```
