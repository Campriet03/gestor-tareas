# ADR 0003: Autenticación

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

El sistema tiene usuarios que pertenecen a equipos y solo deben ver y
modificar lo de sus propios equipos (RNF-01, ver `docs/requisitos.md`). El
frontend y el backend están separados y se comunican por una API (ADR 0005).
El plazo es de 2 semanas.

## Decisión

- Registro e inicio de sesión con correo y contraseña.
- Las contraseñas se guardan con hash **scrypt** (función de Werkzeug, con sal
  aleatoria), nunca en texto plano.
- Al iniciar sesión, el backend entrega un **JWT** (HS256, librería PyJWT)
  firmado con una clave secreta (`JWT_SECRET`) y con expiración corta (1 hora).
- El cliente envía el token en la cabecera `Authorization: Bearer <token>`.
- La autorización se valida en el backend en cada petición: el usuario debe
  pertenecer al equipo del recurso, con rol de propietario o miembro.
  Si no pertenece, responde 403; si el recurso no existe, 404.

## Alternativas consideradas

- **Sesiones en el servidor (cookies):** Ventaja: se pueden invalidar al instante. Desventaja: requieren almacén de sesiones y configurar cookies entre dominios (CORS, CSRF), más trabajo para 2 semanas.

- **Proveedor externo (OAuth, Google, Auth0):** Ventaja: delega la seguridad en un servicio especializado. Desventaja: configuración y dependencia externa fuera del alcance del MVP.

## Consecuencias

- **Positivas:** el backend no guarda estado de sesión, es simple de implementar
  y funciona igual con cualquier cliente.

- **Negativas:** un JWT no se puede revocar antes de que expire. Se reduce el
  riesgo con expiración corta.

- **Pendiente:** tokens de refresco y recuperación de contraseña quedan en el
  roadmap. `JWT_SECRET` vive en `.env` y no se sube al repositorio.
