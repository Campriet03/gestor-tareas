# ADR 0000: Registrar las decisiones de arquitectura

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

El proyecto exige decisiones técnicas importantes (base de datos,
autenticación, tipo de API, organización del código) en un plazo de 2 semanas y
con una sola persona. Si no se escribe el porqué de cada una, se olvida con el
tiempo. Además, el repositorio forma parte de mi portafolio y quien lo lea debe
poder entender por qué se eligió cada cosa y qué se descartó.

## Decisión

Documentar cada decisión importante en un ADR dentro de `docs/adr/`, un archivo
por decisión, numerado y con este formato: Estado, Fecha, Decide, Contexto,
Decisión, Alternativas consideradas y Consecuencias.

- Los estados posibles son Propuesto, Aceptado, Rechazado y Reemplazado por
  ADR N.
- Se escribe al tomar la decisión, antes de implementarla.
- Un ADR aceptado no se reescribe: si la decisión cambia, se crea uno nuevo y el
  anterior pasa a "Reemplazado por".
- Los requisitos se citan por su código (RF-xx, RNF-xx) y están en
  `docs/requisitos.md`.

## Alternativas consideradas

- **Un documento único o una wiki:** Ventaja: es rápido de escribir. Desventaja: se desordena, no se versiona junto al código y es difícil ver cómo cambiaron las decisiones.

- **No documentar:** Ventaja: no cuesta tiempo. Desventaja: se pierde el motivo de cada decisión y cualquier cambio posterior se hace a ciegas.

## Consecuencias

- **Positivas:** el historial queda versionado con Git junto al código, y
  cualquier persona entiende el porqué del diseño sin preguntarme.

- **Negativas:** exige disciplina y algo de tiempo extra en cada decisión.

- **Pendiente:** revisar los ADR afectados si cambian los requisitos.
