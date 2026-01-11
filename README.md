# Zelaya Sports Facturador

El repositorio está dividido en dos áreas principales:

- `frontend/`: aplicación Vite + React (Lovable) para la operación diaria. Usa un cliente axios central en `frontend/src/lib/api.ts` apuntando a `${VITE_API_URL}/api`.
- `backend/`: proyecto Django (`abogados_backend`) y documentación para la API y el modelo de datos PostgreSQL.

## Ejecutar el frontend

```bash
cd frontend
npm install
npm run dev
```

Configura un archivo `.env` en `frontend/` (ver `.env.example`) si necesitas sobreescribir `VITE_API_URL` (por defecto `http://localhost:8000`).

## Backend

```bash
cd backend
# crear y activar un entorno virtual (por ejemplo, python -m venv .venv && source .venv/bin/activate)
pip install -r requirements.txt
# configura las variables de entorno según .env.example
python manage.py migrate
python manage.py runserver
```

Tras actualizar los modelos de la app `api`, recuerda ejecutar:

```bash
python manage.py makemigrations api
python manage.py migrate
```

El backend expone un endpoint básico de salud en `/api/health/` que responde `{"status": "ok"}`.

## Prueba manual de override de precios

1. **Caso OK (sin override)**: crear una factura sin modificar el precio de los servicios → debe responder 201.
2. **Caso OK (override autorizado)**: desbloquear precio con el código válido, modificar el precio de un servicio y crear la factura → debe responder 201.
3. **Caso FAIL (override no autorizado)**: modificar el precio sin validar el código o con token expirado → debe responder 403 con detalle claro.

## Documentación del sistema

El análisis funcional, propuesta de modelo de datos en PostgreSQL (`abogados`, owner `jarvis`) y el boceto de endpoints REST están en [`backend/docs/system_overview.md`](backend/docs/system_overview.md).
