# ADR 0007: Pruebas y entorno

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

El proyecto lo desarrollo yo solo y quiero que se pueda levantar en otra
máquina con pocos comandos (por ejemplo, un evaluador que clone el
repositorio). También quiero detectar errores antes de subir cambios, porque
una falla en permisos o autenticación afectaría todo el sistema. Esto responde
a los RNF-01, RNF-03 y RNF-04 (ver `docs/requisitos.md`).

## Decisión

- **Entorno:** la base de datos corre con Docker Compose (`mysql:8.0`) y las
  configuraciones se leen desde `.env`, con `.env.example` como guía. El
  esquema se crea con `python -m app.init_db`.
- **Pruebas:** pruebas de integración de la API (`backend/tests`) que cubren
  autenticación, permisos entre equipos, invitaciones, tareas y notificaciones.
  Por defecto corren sobre SQLite en memoria (rápidas, sin Docker). Con la
  variable `TEST_DATABASE_URL` corren contra MySQL real.
- **Integración continua:** GitHub Actions ejecuta las pruebas en cada push y
  pull request hacia `main`, en dos trabajos: SQLite y MySQL 8.0 (contenedor de
  servicio). Así el motor real se verifica en cada cambio.

## Alternativas consideradas

- **Probar solo a mano:** Ventaja: no cuesta tiempo al inicio. Desventaja: los
  errores aparecen tarde y se repiten.

- **Contenedores para todo el sistema (backend y frontend):** Ventaja: entorno
  idéntico en todas partes. Desventaja: configuración extra que no aporta al
  MVP; se deja para después.

## Consecuencias

- **Positivas:** entorno reproducible con `docker compose up -d` y cambios
  verificados automáticamente antes de integrarse. El esquema de MySQL 8.0 se
  aplicó sin errores en un contenedor real, y los índices de las consultas
  frecuentes se comprobaron con `EXPLAIN`.

- **Negativas:** escribir pruebas consume tiempo del plazo, por lo que se
  priorizan los flujos críticos. SQLite y MySQL tienen diferencias de dialecto,
  por eso el trabajo de MySQL en la CI es obligatorio y no opcional. El backend
  y el frontend se ejecutan fuera de Docker, así que hay que instalar las
  dependencias de Python con `pip install -r requirements.txt`.