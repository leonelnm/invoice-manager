## Desarrollo

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run invoice-manager init-db
uv run invoice-manager create-admin admin "Nombre" 'cambia-esta-contraseña'
uv run fastapi dev
```

La base de datos se guarda en `data/invoice_manager.db`. Cambia `INVOICE_SECRET_KEY` antes de usar la aplicación y define `INVOICE_SOURCE_SYSTEMS` con los nombres reales separados por comas. El formato provisional de numeración es `FAC-000001`; las decisiones de secuencia, año y formato siguen pendientes de la fase de validación del plan.

La aplicación tiene login, sesiones firmadas, CSRF, roles, gestión básica de usuarios, catálogo de orígenes, asignación transaccional, idempotencia, prevención de duplicados, historial filtrable y paginado, endpoint `/health` y migración Alembic inicial.
