# Migraciones de API: corrección de grafo

## Qué faltaba
El grafo de migraciones del app `api` referenciaba migraciones base ausentes
(`0004_invoice_dte_fields` y `0005_invoice_credit_note_fields`). Esto causaba
`NodeNotFoundError` al construir el grafo.

## Qué se cambió
- Se añadieron migraciones *stub*:
  - `api/migrations/0004_invoice_dte_fields.py`
  - `api/migrations/0005_invoice_credit_note_fields.py`
- Ambas están vacías (`operations = []`) y solo restauran el grafo.

## Cómo migrar
1. Revisar el plan:
   - `python manage.py showmigrations api`
   - `python manage.py migrate --plan`
2. Aplicar migraciones:
   - `python manage.py migrate`

## Verificación
- Iniciar el servidor: `python manage.py runserver 127.0.0.1:8007`
- Confirmar que no aparece `NodeNotFoundError` al iniciar.

## Nota
Si faltan campos reales en la base de datos, crear una migración nueva
(por ejemplo `0010_add_missing_invoice_fields.py`) con `AddField`, pero
no incluir cambios destructivos en los stubs.
