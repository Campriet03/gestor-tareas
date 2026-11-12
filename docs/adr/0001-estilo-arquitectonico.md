# ADR 0001: Estilo arquitectónico

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

El sistema es un gestor de tareas para equipos: usuarios, equipos, proyectos y
tareas, con notificaciones. Lo desarrollo yo solo y el plazo es de 2 semanas.
Los requisitos RNF-03, RNF-04 y RNF-05 (ver `docs/requisitos.md`) piden que el
sistema sea fácil de mantener, de probar y de ejecutar, y que los datos se
mantengan consistentes. No hay equipo de operaciones ni tráfico que justifique
escalar partes por separado.

## Decisión

Construir un **monolito en capas**: una sola aplicación backend con una única
base de datos, que expone una API REST (ADR 0005) y sirve también los archivos
del frontend. Se despliega y se prueba como una sola unidad.

## Alternativas consideradas

- **Microservicios:** Ventaja: cada servicio escala y se despliega por separado. Desventaja: exige varios despliegues, comunicación entre servicios y datos distribuidos, y con una sola persona y 2 semanas el tiempo se iría en infraestructura, además de complicar la consistencia que pide el RNF-05.

- **Backend como servicio (por ejemplo, Firebase):** Ventaja: menos código de servidor que escribir. Desventaja: depende de un proveedor externo, cuesta más demostrar el diseño propio y no encaja con el modelo relacional que elegí (ADR 0002).

## Consecuencias

- **Positivas:** es simple de construir, de probar y de ejecutar (un solo
  proceso y una sola base), y las transacciones mantienen la consistencia de los
  datos.

- **Negativas:** toda la aplicación escala y se despliega junta, y si el
  proyecto crece mucho el código podría volverse difícil de manejar.

- **Pendiente:** la organización interna del backend (ADR 0004) debe mantener
  los límites entre capas para poder separar partes más adelante si hace falta.
