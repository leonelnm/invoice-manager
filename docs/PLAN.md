# Invoice Manager — Plan del proyecto

## 1. Visión

Invoice Manager será una aplicación web interna para centralizar la asignación y consulta de números de factura asociados a partes de trabajo recibidos desde dos sistemas externos.

La oficina cuenta con tres trabajadoras. Actualmente consultan una carpeta compartida para localizar la última factura y continuar manualmente la numeración. La aplicación sustituirá ese procedimiento por un servicio centralizado, evitando colisiones cuando varias personas trabajan al mismo tiempo.

El MVP no pretende generar documentos fiscales ni sustituir los sistemas que reciben los partes. Su responsabilidad inicial es asignar un número, asociarlo al origen y al identificador del parte, y conservar un historial consultable.

## 2. Objetivos

- Asignar el siguiente número disponible bajo demanda.
- Identificar el sistema de origen y el identificador del parte.
- Evitar números duplicados ante solicitudes simultáneas.
- Evitar registrar dos veces el mismo parte.
- Mostrar una confirmación inmediata.
- Consultar el historial mediante filtros y paginación.
- Registrar qué trabajadora realizó la asignación y cuándo.
- Mantener una aplicación sencilla de desplegar y mantener.

## 3. Fuera de alcance del MVP

- Crear o maquetar facturas PDF.
- Gestionar clientes, aseguradoras, conceptos, importes o impuestos.
- Integrarse con los dos sistemas externos.
- Reservar números o gestionar borradores.
- Anular, rectificar o eliminar registros.
- Enviar facturas por correo.
- Integrarse con AEAT o VERI*FACTU.
- Incorporar una SPA desde el primer día.

La aplicación asigna numeración; esto no implica por sí mismo que emita una factura fiscal válida. El alcance deberá confirmarse con la propietaria.

## 4. Stack tecnológico propuesto

| Capa | Tecnología |
|---|---|
| Lenguaje | Python |
| Backend | FastAPI |
| HTML | Jinja2 |
| Interacciones | HTMX |
| Persistencia | SQLite |
| ORM | SQLAlchemy 2.x |
| Migraciones | Alembic |
| Validación | Pydantic |
| Servidor ASGI | Uvicorn |
| Proxy inverso | Nginx, si procede |
| Pruebas | pytest + HTTPX |

La primera versión será un monolito web renderizado en servidor. No requiere Node.js en producción ni una API REST separada para que funcione HTMX.

## 5. Arquitectura

    Navegadores de las tres trabajadoras
                    |
                  HTTP
                    |
             Nginx (opcional)
                    |
              Uvicorn / ASGI
                    |
                 FastAPI
               /         \
        Rutas web       API futura
        HTML/HTMX       JSON
               \         /
             Casos de uso
                    |
               Repositorios
                    |
                SQLAlchemy
                    |
                  SQLite

Las rutas web y las futuras rutas JSON deben reutilizar los mismos casos de uso. La lógica de numeración no debe estar dentro de los controladores ni depender de Jinja2 o HTMX.

### Estructura orientativa

    app/
      main.py
      config.py
      dependencies.py
      domain/
      application/
        invoices/
          create_invoice.py
          search_invoices.py
        users/
      infrastructure/
        persistence/
          models/
          repositories/
          database.py
      web/
        routes/
        templates/
      static/
        css/
    migrations/
    tests/
      unit/
      integration/
    docs/
    data/
    pyproject.toml
    alembic.ini
    .env.example

La estructura debe crecer según las necesidades reales. No crear capas vacías ni abstracciones genéricas sin un caso de uso.

## 6. Usuarios y permisos

### Trabajadora
- Iniciar y cerrar sesión.
- Generar un número para un parte.
- Consultar y filtrar el historial.

### Administradora
- Todas las funciones de trabajadora.
- Crear y desactivar usuarios.
- Restablecer contraseñas.
- Consultar el historial completo.

En el MVP bastan dos roles sencillos. Cada trabajadora debe tener una cuenta individual.

## 7. Flujo principal

1. La trabajadora inicia sesión.
2. Selecciona uno de los dos sistemas de origen.
3. Introduce el identificador del parte.
4. Pulsa «Generar número de factura».
5. El backend valida los datos.
6. Comprueba si ya existe una asignación para ese sistema e identificador.
7. Si ya existe, devuelve el número anterior sin consumir otro.
8. Si no existe, asigna el siguiente número y persiste el registro dentro de una única transacción.
9. La pantalla muestra el número asignado y una confirmación.
10. El registro aparece en el historial.

No existen reservas ni estados intermedios en el flujo inicial.

## 8. Modelo de datos propuesto

### users
- id
- username, único
- password_hash
- display_name
- is_active
- is_admin
- created_at
- updated_at

### source_systems
- id
- code, único y estable
- name
- is_active

### invoice_sequences
- id
- series
- fiscal_year, si aplica
- last_number

La combinación que identifique una secuencia debe tener una restricción UNIQUE.

### invoices
- id
- sequence_id
- sequence_number
- invoice_number
- source_system_id
- report_id
- created_by
- created_at

Restricciones importantes:
- UNIQUE(sequence_id, sequence_number).
- UNIQUE(source_system_id, report_id), si se confirma que un parte solo puede generar una factura.
- UNIQUE(invoice_number), si el formato es globalmente único.
- Claves foráneas hacia secuencia, origen y usuario.
- Índices para número, identificador de parte, origen y fecha.

El identificador del parte se almacenará como texto para conservar ceros iniciales y admitir formatos alfanuméricos.

## 9. Numeración y concurrencia

La numeración no se calculará leyendo el último registro del historial. Se mantendrá un contador persistido.

La operación de creación debe ser atómica:

1. Comenzar una transacción de escritura.
2. Comprobar si ya existe el parte para el origen seleccionado.
3. Si existe, devolver el registro existente sin incrementar el contador.
4. Obtener el siguiente valor de la secuencia.
5. Incrementar el contador.
6. Insertar el registro asociado al usuario.
7. Confirmar la transacción.

Si falla cualquier paso, la transacción debe revertirse. Las restricciones UNIQUE actúan como protección adicional.

SQLite permite múltiples lectores, pero serializa las escrituras. Para tres trabajadoras y una aplicación de este tamaño es suficiente si el fichero de base de datos reside en el disco local del servidor. Configurar WAL, foreign_keys y busy_timeout según la estrategia de conexión elegida.

No colocar la base de datos SQLite en una carpeta compartida SMB/NFS ni en una unidad de red.

### Reintentos y doble clic

La restricción única sobre origen + identificador del parte evita generar dos números por un doble clic o reintento de red. Si el registro ya existe, la aplicación muestra el número previamente asignado.

Si se confirma que un parte puede producir más de una factura, esta regla deberá rediseñarse antes de implementar.

### Numeración existente

Antes del piloto se debe verificar el último número realmente emitido en cada secuencia. No asumir que el último archivo visible en la carpeta compartida representa necesariamente el último número válido.

No permitir borrar registros ni reutilizar automáticamente números consumidos.

## 10. Pantallas

### Login
- Usuario.
- Contraseña.
- Mensajes de error genéricos.

### Generar número
- Selector de sistema de origen.
- Campo de identificador del parte.
- Botón de generación.
- Resultado con número, origen, parte, fecha y confirmación.

### Historial
Filtros:
- Número de factura.
- Identificador del parte.
- Sistema de origen.
- Trabajadora.
- Fecha desde y hasta.

Columnas:
- Número.
- Sistema de origen.
- Identificador del parte.
- Trabajadora.
- Fecha de creación.

Orden descendente por fecha, paginación en backend y filtros conservados al cambiar de página.

### Administración
- Listado de usuarios.
- Alta de usuario.
- Activar/desactivar.
- Restablecer contraseña.

## 11. Rutas web iniciales

| Método | Ruta | Uso |
|---|---|---|
| GET | /login | Mostrar login |
| POST | /login | Autenticar |
| POST | /logout | Cerrar sesión |
| GET | / | Formulario principal |
| POST | /invoices | Asignar número |
| GET | /invoices | Historial y filtros |
| GET | /invoices/{id} | Detalle |
| GET | /admin/users | Gestión de usuarios |
| POST | /admin/users | Crear usuario |
| POST | /admin/users/{id}/deactivate | Desactivar usuario |

HTMX enviará formularios y recibirá fragmentos HTML. Las operaciones que modifican datos utilizarán POST y protección CSRF.

## 12. Evolución futura a SPA

Si la aplicación crece, se puede incorporar una SPA sin reescribir la lógica de negocio:

1. Añadir endpoints versionados, por ejemplo /api/v1/invoices.
2. Definir contratos Pydantic y respuestas JSON.
3. Incorporar Svelte, React o Angular.
4. Reutilizar los mismos casos de uso, repositorios y base de datos.
5. Mantener Jinja2/HTMX durante una transición o retirarlos cuando la SPA los sustituya.

No implementar ahora dos interfaces. La condición importante es mantener las rutas web como adaptadores finos y aislar los casos de uso.

## 13. Seguridad

- Cuentas individuales.
- Contraseñas con hash adecuado, por ejemplo Argon2id.
- Sesiones con cookies HttpOnly y SameSite.
- Cookie Secure cuando se utilice HTTPS.
- Protección CSRF.
- Regenerar sesión al autenticar e invalidarla al cerrar sesión.
- Limitar intentos de login.
- Validar entradas en servidor.
- No confiar en el usuario enviado por el navegador: obtenerlo de la sesión.
- No mostrar trazas ni errores SQL al usuario.
- No guardar secretos en Git.
- Mantener dependencias y sistema operativo actualizados.

## 14. Despliegue

La decisión entre servidor local y VPS queda pendiente de la reunión.

### Servidor local
- Un equipo Linux que permanezca encendido.
- IP local estable o reserva DHCP.
- FastAPI/Uvicorn como servicio.
- Nginx opcional.
- Acceso desde los tres navegadores de la red local.
- Copias de seguridad en otro dispositivo o destino.

Ventaja principal: funciona dentro de la oficina aunque se caiga Internet. Si el servidor se apaga, la aplicación deja de estar disponible.

### VPS
- VPS Linux pequeña.
- FastAPI/Uvicorn.
- Nginx y HTTPS.
- Firewall y actualizaciones.
- SQLite en disco local de la VPS.
- Copias de seguridad fuera de la VPS.

Ventaja principal: no requiere hardware local y permite acceso remoto autorizado. Depende de Internet.

Una instancia de 1 vCPU y 1 GB de RAM es un punto de partida razonable para tres usuarias; se revisará según el uso real. No hacen falta Redis, Kubernetes ni PostgreSQL en el MVP.

La aplicación debe poder ejecutarse en ambos entornos sin cambios de código.

## 15. Copias de seguridad y mantenimiento

- Programar copias automáticas al menos diarias.
- Utilizar SQLite Backup API o un mecanismo consistente compatible con WAL.
- No copiar solamente el archivo principal de una base activa y asumir que la copia es consistente.
- Guardar copias fuera del disco de producción.
- Definir retención y permisos.
- Probar restauraciones periódicamente.
- Separar datos persistentes del código desplegado.
- Ejecutar migraciones Alembic durante las actualizaciones.
- Mantener un procedimiento de rollback.
- Registrar errores y eventos importantes sin almacenar secretos.

## 16. Plan de implementación

### Fase 0 — Validación
- [ ] Confirmar nombres de los dos sistemas.
- [ ] Confirmar formato de los identificadores.
- [ ] Confirmar si el identificador puede repetirse entre sistemas.
- [ ] Confirmar si un parte puede generar más de una factura.
- [ ] Confirmar secuencia única o independiente por sistema.
- [ ] Confirmar formato de número y reinicio anual.
- [ ] Verificar el último número realmente emitido.
- [ ] Confirmar quién administra usuarios.
- [ ] Confirmar acceso solo desde oficina o también remoto.
- [ ] Confirmar si solo asigna número o si esperan emitir el documento fiscal.

### Fase 1 — Base
- [ ] Crear proyecto Python y dependencias.
- [ ] Configurar FastAPI, SQLAlchemy y SQLite.
- [ ] Configurar Alembic.
- [ ] Configurar variables de entorno.
- [ ] Añadir logging, endpoint de salud y pruebas.
- [ ] Verificar arranque y migraciones.

### Fase 2 — Autenticación
- [ ] Modelo y migración de usuarios.
- [ ] Inicialización segura de primera administradora.
- [ ] Login y logout.
- [ ] Sesiones y protección CSRF.
- [ ] Protección de rutas.
- [ ] Gestión básica de usuarios.
- [ ] Pruebas de permisos y sesiones.

### Fase 3 — Numeración
- [ ] Catálogo de sistemas de origen.
- [ ] Modelo de secuencias y registros.
- [ ] Restricciones únicas e índices.
- [ ] Inicialización del contador.
- [ ] Caso de uso transaccional.
- [ ] Prevención de duplicados.
- [ ] Formulario Jinja2/HTMX.
- [ ] Confirmación y errores de usuario.

### Fase 4 — Historial
- [ ] Búsqueda por número.
- [ ] Búsqueda por identificador.
- [ ] Filtro por sistema.
- [ ] Filtro por trabajadora y fechas.
- [ ] Paginación en backend.
- [ ] Tabla y detalle.
- [ ] Pruebas de filtros y paginación.

### Fase 5 — Pruebas
- [ ] Pruebas unitarias.
- [ ] Pruebas de integración.
- [ ] Solicitudes concurrentes.
- [ ] Doble envío del mismo parte.
- [ ] Rollback ante errores.
- [ ] Pruebas de autorización.
- [ ] Restauración de copia de seguridad.

### Fase 6 — Piloto
- [ ] Elegir servidor local o VPS.
- [ ] Configurar servicio, red y HTTPS si corresponde.
- [ ] Crear usuarios.
- [ ] Cargar secuencia inicial verificada.
- [ ] Configurar y probar backups.
- [ ] Probar desde los tres ordenadores.
- [ ] Formar a las trabajadoras.
- [ ] Definir procedimiento de contingencia.

### Fase 7 — Evolución opcional
- [ ] Exportación CSV/Excel.
- [ ] Integración con sistemas de partes.
- [ ] Generación documental.
- [ ] API JSON versionada.
- [ ] SPA.
- [ ] PostgreSQL si las necesidades futuras lo justifican.
- [ ] Funcionalidades fiscales tras análisis específico.

## 17. Criterios de aceptación del MVP

- Una usuaria autenticada puede seleccionar origen e introducir un identificador.
- La aplicación asigna y persiste un número.
- Dos solicitudes concurrentes nunca reciben el mismo número.
- Repetir el mismo parte no consume otro número.
- Cada asignación registra usuaria y fecha.
- El historial permite buscar por número, parte y origen.
- El historial pagina en backend.
- Las rutas privadas rechazan usuarios no autenticados.
- La aplicación puede reiniciarse sin perder datos.
- Se puede realizar y restaurar una copia de seguridad.

## 18. Decisiones pendientes de confirmar

| Tema | Estado |
|---|---|
| Nombres de los sistemas de origen | Pendiente |
| Secuencia compartida o independiente | Pendiente |
| Formato exacto del número | Pendiente |
| Reinicio anual | Pendiente |
| Un parte puede tener varias facturas | Pendiente |
| Último número válido de cada secuencia | Pendiente |
| Acceso solo local o remoto | Pendiente |
| Servidor local o VPS | Pendiente |
| Administración de usuarios | Pendiente |
| Emisión de documento fiscal o solo asignación | Pendiente |

## 19. Principios de desarrollo

1. Resolver el flujo real antes de ampliar el alcance.
2. Mantener una única fuente central de numeración.
3. No asignar números en el navegador.
4. No permitir borrado o reutilización automática.
5. Mantener transacción y registro en una misma operación.
6. Separar lógica de negocio y presentación.
7. Elegir la solución operativa más sencilla que cumpla las necesidades.
8. No anticipar una SPA, microservicios ni una base de datos más compleja sin necesidad.
