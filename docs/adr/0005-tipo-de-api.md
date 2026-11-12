# ADR 0005: Tipo de API

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

El frontend necesita crear y consultar usuarios, equipos, proyectos y tareas
(RNF-02, ver `docs/requisitos.md`). Los datos son recursos con relaciones
claras y el plazo es de 2 semanas.

## Decisión

API **REST** con JSON, versionada bajo `/api/v1`. Recursos principales:

```
POST   /api/v1/auth/register | /auth/login
GET    /api/v1/teams
POST   /api/v1/teams
GET    /api/v1/teams/:id/projects
POST   /api/v1/teams/:id/projects
GET    /api/v1/projects/:id/tasks
POST   /api/v1/projects/:id/tasks
PATCH  /api/v1/tasks/:id
```

Se usan códigos HTTP estándar (200, 201, 400, 401, 403, 404) y un formato de
error uniforme.

## Alternativas consideradas

- **GraphQL:** Ventaja: el cliente pide exactamente los campos que necesita. Desventaja: requiere esquema, resolvers y manejo de rendimiento (N+1) que no compensan en un proyecto de este tamaño.

- **gRPC:** Ventaja: eficiente y con contrato estricto. Desventaja: poco práctico para un frontend web y fuera de mi experiencia.

## Consecuencias

- **Positivas:** es simple, fácil de probar con herramientas comunes y bien
  conocida por quien lea el repositorio.

- **Negativas:** puede haber más peticiones o datos de sobra según la pantalla.
  Se acepta para el alcance actual.
