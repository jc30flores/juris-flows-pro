# Panorama del sistema Relite-Group

## Descripción general del sistema
Relite-Group es una plataforma para la gestión integral de una oficina jurídica. El objetivo es centralizar operaciones de facturación electrónica (DTE), servicios jurídicos, clientes, gastos y usuarios internos. Los módulos clave son:

- **Facturación electrónica / DTE**: emisión y seguimiento de documentos fiscales (CF, CCF, etc.). Permite registrar método de pago, estado del DTE y totales.
- **Servicios jurídicos**: catálogo de servicios con código, categoría y precio base; control de si el servicio es imponible y si está activo.
- **Clientes**: registro de personas naturales y jurídicas con identificadores fiscales (DUI, NIT), teléfonos y correos. Se distingue el tipo fiscal (CF, CCF, SX).
- **Gastos**: control de gastos internos por proveedor, fecha y total.
- **Usuarios y roles**: administración de usuarios internos (admin, contador, colaborador) y estado activo.

Flujo de uso esperado:
1. Registrar servicios y categorías básicas, indicando precio base e imponible.
2. Registrar clientes (persona o empresa) con datos fiscales y de contacto.
3. Emitir una factura/DTE en el módulo de facturación seleccionando cliente, servicios y método de pago; seguir estado del DTE.
4. Controlar gastos de la oficina registrando proveedor, fecha y total; exportar reportes cuando aplique.
5. Gestionar usuarios y roles internos para controlar accesos.

## Módulos y pantallas del frontend actual
Basado en `frontend/src/`, el frontend incluye las siguientes pantallas principales:

- **Facturador (POS)** (`/pos`): listado de DTE recientes con número, fecha, cliente, tipo (CF/CCF), método de pago, estado DTE y total. Acciones: crear nueva factura (modal), filtrar por rango rápido (hoy/semana/mes), buscar por número o cliente, exportar, ver detalles.
- **Servicios** (`/servicios`): tabla con código, nombre del servicio, categoría, precio base y estado (activo/inactivo). Acciones: activar modo edición, crear servicio, crear categoría, editar servicio al hacer clic en una fila.
- **Clientes** (`/clientes`): tabla y tarjetas con nombre/razón social, nombre comercial, tipo fiscal, DUI/NIT, teléfono y correo. Acciones: activar modo edición, crear nuevo cliente, editar cliente al seleccionar una fila o tarjeta, búsqueda por nombre/DUI/NIT.
- **Gastos** (`/gastos`): tabla y tarjetas con nombre del gasto, proveedor, fecha y total. Acciones: crear gasto, ver detalle del gasto, filtros rápidos por fecha, búsqueda y exportar.
- **Usuarios** (`/usuarios`): tabla y tarjetas con nombre, rol (ADMIN, COLABORADOR, CONTADOR) y estado activo. Acciones: crear nuevo usuario y preparar edición.
- **No encontrado**: pantalla de fallback para rutas inexistentes.

## Entidades de dominio y relaciones
A partir del comportamiento del frontend se infieren las siguientes entidades y vínculos:

- **Cliente**: nombre/razón social (texto), nombre comercial opcional (texto), tipo fiscal (enum CF/CCF/SX), DUI (texto), NIT (texto), NRC (texto), teléfono (texto), correo (texto), tipo de persona (enum persona/empresa/otro).
- **Servicio**: código (texto), nombre (texto), categoría (referencia a `CategoriaServicio`), precio base (numérico), imponible (booleano), activo (booleano), descripción opcional (texto).
- **CategoriaServicio**: nombre (texto), descripción (texto opcional), estado activo (booleano).
- **Factura o DocumentoFiscal (DTE)**: número (texto), fecha de emisión (fecha), cliente (FK a `Cliente`), tipo fiscal (enum CF/CCF/otros), método de pago (FK a `MetodoPago`), estado DTE (FK a `EstadoDTE`), total (numérico), moneda (texto), referencia a usuario creador (FK `Usuario`).
- **DetalleFactura / LineaServicio**: factura (FK `DocumentoFiscal`), servicio (FK `Servicio`), cantidad (numérico), precio unitario (numérico), subtotal/impuestos calculados (numérico), notas (texto opcional).
- **MetodoPago**: nombre (texto), requiere referencia (booleano), estado activo (booleano).
- **EstadoDTE**: nombre (texto, ej. Aprobado/Pendiente/Rechazado), código interno (texto), color o prioridad opcional.
- **Gasto**: nombre (texto), proveedor (texto), fecha (fecha), total (numérico), categoría opcional (texto o FK futura), usuario registrador (FK `Usuario`).
- **Usuario**: nombre (texto), email (texto), rol (FK `Rol`), contraseña/credenciales (gestionadas en backend), activo (booleano), timestamps de auditoría.
- **Rol**: nombre (texto, ej. ADMIN, COLABORADOR, CONTADOR), permisos (JSON o many-to-many futura).

Relaciones principales:
- Un **DocumentoFiscal** pertenece a un **Cliente**, tiene muchas **LineasServicio**, un **MetodoPago**, un **EstadoDTE** y es creado por un **Usuario**.
- Una **LineaServicio** referencia un **Servicio** y pertenece a un **DocumentoFiscal**.
- Un **Servicio** pertenece a una **CategoriaServicio**.
- Un **Gasto** puede registrar el **Usuario** que lo creó.
- Un **Usuario** pertenece a un **Rol**.

## Propuesta inicial de modelo de datos para PostgreSQL (base `abogados`)
La base de datos local se llamará `abogados` y el owner será el usuario de PostgreSQL `jarvis`. Más adelante se parametrizarán las credenciales con variables de entorno (`DB_NAME=abogados`, `DB_USER=jarvis`, `DB_PASSWORD=...`). Aún no se crea la base ni migraciones; esto es solo el diseño conceptual.

Tablas sugeridas:

- **clients**
  - id (serial, PK)
  - name (varchar(180))
  - trade_name (varchar(180), nullable)
  - fiscal_type (varchar(10))
  - dui (varchar(20), nullable)
  - nit (varchar(25), nullable)
  - nrc (varchar(25), nullable)
  - phone (varchar(25), nullable)
  - email (varchar(180), nullable)
  - client_type (varchar(20), default 'persona')
  - created_at (timestamp with time zone, default now())
  - updated_at (timestamp with time zone, default now())

- **service_categories**
  - id (serial, PK)
  - name (varchar(150))
  - description (text, nullable)
  - is_active (boolean, default true)
  - created_at / updated_at (timestamptz)

- **services**
  - id (serial, PK)
  - code (varchar(50))
  - name (varchar(200))
  - category_id (integer, FK -> service_categories.id)
  - base_price (numeric(12,2))
  - taxable (boolean, default true)
  - is_active (boolean, default true)
  - description (text, nullable)
  - created_at / updated_at (timestamptz)

- **payment_methods**
  - id (serial, PK)
  - name (varchar(80))
  - requires_reference (boolean, default false)
  - is_active (boolean, default true)

- **dte_statuses**
  - id (serial, PK)
  - name (varchar(60))
  - code (varchar(20))
  - color (varchar(30), nullable)

- **invoices** (o `documents`)
  - id (serial, PK)
  - number (varchar(60))
  - issue_date (date)
  - client_id (integer, FK -> clients.id)
  - fiscal_type (varchar(10))
  - payment_method_id (integer, FK -> payment_methods.id)
  - status_id (integer, FK -> dte_statuses.id)
  - currency (varchar(10), default 'USD')
  - total (numeric(12,2))
  - created_by_id (integer, FK -> users.id)
  - created_at / updated_at (timestamptz)

- **invoice_items**
  - id (serial, PK)
  - invoice_id (integer, FK -> invoices.id)
  - service_id (integer, FK -> services.id)
  - quantity (numeric(10,2))
  - unit_price (numeric(12,2))
  - subtotal (numeric(12,2))
  - tax_amount (numeric(12,2), default 0)
  - total (numeric(12,2))
  - notes (text, nullable)

- **expenses**
  - id (serial, PK)
  - name (varchar(180))
  - vendor (varchar(180))
  - expense_date (date)
  - total (numeric(12,2))
  - created_by_id (integer, FK -> users.id)
  - created_at / updated_at (timestamptz)

- **roles**
  - id (serial, PK)
  - name (varchar(50))
  - description (text, nullable)

- **users**
  - id (serial, PK)
  - full_name (varchar(180))
  - email (varchar(180) unique)
  - password_hash (text)
  - role_id (integer, FK -> roles.id)
  - is_active (boolean, default true)
  - last_login (timestamp with time zone, nullable)
  - created_at / updated_at (timestamptz)

## Diseño de API REST para el futuro backend en Django
Endpoints pensados para Django + Django REST Framework; el frontend podrá consumirlos con `fetch` o `axios`.

- **Clientes** `/api/clients/`
  - GET lista con filtros por nombre, tipo fiscal, DUI/NIT.
  - POST crear cliente.
  - GET `/api/clients/{id}/` obtener detalle.
  - PUT/PATCH `/api/clients/{id}/` actualizar.
  - DELETE `/api/clients/{id}/` desactivar/eliminar.

- **Servicios** `/api/services/`
  - GET lista con filtros por categoría, estado activo, texto de búsqueda.
  - POST crear servicio.
  - GET `/api/services/{id}/` detalle.
  - PUT/PATCH `/api/services/{id}/` actualizar.
  - DELETE `/api/services/{id}/` desactivar.

- **Categorías de servicio** `/api/service-categories/`
  - CRUD completo, con filtros por estado.

- **Facturación / DTE** `/api/invoices/`
  - GET lista con filtros por fecha, cliente, tipo fiscal, estado DTE y método de pago.
  - POST crear factura con items.
  - GET `/api/invoices/{id}/` detalle (incluye items y estado DTE).
  - PUT/PATCH `/api/invoices/{id}/` actualizar encabezado/estado.
  - DELETE `/api/invoices/{id}/` (opcional: anular o marcar cancelada).
  - Acciones adicionales futuras: `/api/invoices/{id}/export`, `/api/invoices/{id}/send-email`.

- **Gastos** `/api/expenses/`
  - GET lista con filtros por fecha, proveedor, rango de totales.
  - POST crear gasto.
  - GET `/api/expenses/{id}/` detalle.
  - PUT/PATCH `/api/expenses/{id}/` actualizar.
  - DELETE `/api/expenses/{id}/` eliminar/anular.

- **Usuarios y auth**
  - `/api/users/` (GET lista, POST crear, PUT/PATCH/DELETE por id) con filtros por rol/estado.
  - `/api/roles/` (CRUD básico).
  - `/api/auth/login` (POST credenciales, retorna token o sesión).
  - `/api/auth/logout` (POST o DELETE token).
  - `/api/auth/me` (GET perfil autenticado).

## Siguientes pasos
- Completar la configuración del proyecto Django en `backend/` apuntándolo a la base `abogados` en PostgreSQL y creando apps por dominio (facturación, clientes, etc.).
- Implementar modelos en Django basados en las tablas propuestas y preparar migraciones.
- Configurar viewsets/routers DRF para los endpoints definidos, aplicando filtros y paginación.
- Actualizar el frontend para consumir los endpoints con `fetch` o `axios` de manera progresiva.
- Mantener variables de entorno para credenciales de base de datos y configuración de despliegue.

> Nota: el proyecto base `abogados_backend` ya existe, pero aún no se han creado apps ni migraciones específicas; este documento sigue siendo de análisis y diseño previo.
