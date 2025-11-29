# Cuska-OnOffice

El repositorio ahora está organizado en dos áreas principales:

- `frontend/`: aplicación Vite + React (Lovable) existente para la operación diaria.
- `backend/`: carpeta reservada para la futura API Django + PostgreSQL, con documentación previa en `backend/docs/`.

## Ejecutar el frontend

```bash
cd frontend
npm install
npm run dev
```

Los archivos originales del proyecto React viven dentro de `frontend/`, incluyendo `src/`, `public/`, configuraciones de Vite/Tailwind y bloqueos de dependencias.

## Planificación del backend

El análisis funcional actual, propuesta de modelo de datos (base `policydb`, usuario `jarvis`) y el boceto de endpoints REST están documentados en [`backend/docs/system_overview.md`](backend/docs/system_overview.md).

Todavía no se ha creado el proyecto Django ni la base de datos; esta etapa es únicamente de diseño y organización.
