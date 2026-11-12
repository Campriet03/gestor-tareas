# ADR 0004: Organización del backend

- **Estado:** Aceptado
- **Fecha:** 2026-11-11
- **Decide:** Camilo Prieto

## Contexto

El backend es un monolito (ADR 0001) que lo mantiene una sola persona. Debe
ser fácil de probar y de mantener (RNF-03, ver `docs/requisitos.md`), y las
reglas de acceso por equipo (RNF-01) no deben repetirse en cada endpoint.

## Decisión

Organizar el backend en capas, donde cada una solo habla con la siguiente:

```
routes/controllers → services → repositories → base de datos
```

- **Routes/controllers** (`app/routes.py`): definen las URL, exigen el token y
  comprueban que el cuerpo sea JSON. Un controlador solo llama a un service.
- **Services** (`app/services.py`): validan datos y contienen las reglas de
  negocio y los permisos (por ejemplo, quién puede eliminar una tarea).
- **Repositories** (`app/repositories.py`): son los únicos que escriben SQL.
- **Database** (`app/db.py`): adaptador con una interfaz común para MySQL
  (producción) y SQLite (pruebas rápidas).

Se fusionan rutas y controladores en un solo archivo porque en Flask una
función de vista cumple ambos papeles y separarlos solo añadía archivos.

Los errores se lanzan desde los services y un único manejador central los
convierte en respuestas HTTP.

## Alternativas consideradas

- **Controladores con SQL directo:** Ventaja: menos archivos, más rápido al inicio. Desventaja: la lógica y el SQL se mezclan, y probar o cambiar algo se vuelve costoso.

- **Arquitectura hexagonal:** Ventaja: aislamiento total del dominio. Desventaja: demasiada ceremonia para un proyecto de 2 semanas.

## Consecuencias

- **Positivas:** la lógica se prueba sin base de datos (ADR 0007), y cambiar el
  acceso a datos solo toca los repositories.

- **Negativas:** más archivos y algo de código repetitivo entre capas.