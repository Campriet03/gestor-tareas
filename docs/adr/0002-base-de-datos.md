# ADR 0002: Base de datos

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

Los datos del sistema son usuarios, equipos, proyectos y tareas, y se
relacionan entre sí: un usuario pertenece a varios equipos, un equipo tiene
varios proyectos y cada proyecto tiene varias tareas asignadas a usuarios.
Son relaciones de uno a muchos y de muchos a muchos, con claves foráneas.

Los requisitos RNF-02 y RNF-05 (ver `docs/requisitos.md`) piden consultas
eficientes e integridad de los datos. Ya conozco MySQL y el plazo es de
2 semanas, trabajando una sola persona.

## Decisión

Usar **MySQL 8.0** como base de datos relacional, ejecutada en un contenedor
Docker con la imagen oficial `mysql:8.0`.

## Alternativas consideradas

- **PostgreSQL:** Ventaja: más funciones avanzadas (tipos de datos, consultas complejas). Desventaja: no lo conozco, y en 2 semanas aprenderlo compite con el tiempo de construir las funciones.

- **MongoDB:** Ventaja: esquema flexible, útil si los datos cambian mucho de forma. Desventaja: mis datos son muy relacionales y MongoDB no impone claves foráneas, así que la integridad del RNF-05 dependería de mi código.

## Consecuencias

- **Positivas:**
  - No pierdo tiempo aprendiendo la herramienta.
  - Las claves foráneas y las transacciones protegen la integridad de los datos.
  - Con Docker la versión queda fija (8.0) y el entorno se levanta con un solo
    comando. Uso MySQL real, no MariaDB como ocurriría con XAMPP.

- **Negativas:**
  - Renuncio a algunas funciones de PostgreSQL; no las necesito en este alcance.
  - Debo tener Docker Desktop instalado para trabajar.

- **Pendiente:** la gestión de cambios en las tablas (migraciones) se decidirá
  en un ADR aparte.
