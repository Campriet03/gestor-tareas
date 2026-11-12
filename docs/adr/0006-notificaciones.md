# ADR 0006: Notificaciones

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

El RF-08 (ver `docs/requisitos.md`) pide avisar a los usuarios de eventos como
una tarea asignada o una invitación a un equipo. Trabajo solo y el plazo es de
2 semanas.

## Decisión

Guardar las notificaciones en una tabla de MySQL y que el frontend las
consulte periódicamente (**polling**) cada 30 segundos con
`GET /api/v1/notifications`. Cada notificación tiene un estado leída o no
leída.

## Alternativas consideradas

- **WebSockets:** Ventaja: avisos inmediatos. Desventaja: requiere conexiones persistentes y manejo de reconexión.

- **Server-Sent Events (SSE):** Ventaja: más simple que WebSockets para avisos del servidor al cliente. Desventaja: sigue necesitando conexiones abiertas y manejo de autenticación distinto al resto de la API.

## Consecuencias

- **Positivas:** reutiliza la API REST y la autenticación existentes, sin
  infraestructura nueva.

- **Negativas:** hay un retraso de hasta 30 segundos y peticiones periódicas
  aunque no haya novedades.

- **Evolución:** si hace falta tiempo real, se puede pasar a SSE sin cambiar el
  modelo de datos.
