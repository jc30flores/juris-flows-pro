# Migraciones de API: corrección de grafo

## Qué faltaba
En el historial de migraciones del app `api` faltaba una migración intermedia que introdujera
campos nuevos y el modelo `DTERecord`. Esto provocaba errores al construir el grafo de
migraciones cuando el entorno tenía referencias a migraciones posteriores.

## Qué se cambió
- Se añadió `api/migrations/0004_invoice_dte_fields.py` para:
  - incorporar campos faltantes en `Client` e `Invoice`.
  - crear el modelo `DTERecord` con sus índices.
  - alinear el modelo `StaffUser` con sus campos actuales, migrando `email` a `username`.

## Cómo migrar
1. Revisar el plan:
   - `python manage.py showmigrations api`
   - `python manage.py migrate --plan`
2. Aplicar migraciones:
   - `python manage.py migrate`

## Verificación
- Iniciar el servidor: `python manage.py runserver 127.0.0.1:8007`
- Confirmar que no aparece `NodeNotFoundError` al iniciar.
