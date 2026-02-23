# Billing API & Frontend Challenge

Bienvenido al repositorio de mi solución para el challenge de facturación. En este repo vas a encontrar un sistema de gestión documental completo (Backend en FastAPI + Worker en Celery + Frontend en React) que se encarga de manejar el ciclo de vida de los documentos a través de procesos asíncronos.

## Arquitectura y Decisiones

Traté de mantener la arquitectura lo más simple posible para el requerimiento, pero escalable en caso de que crezca. Principalmente, usé:

- **Backend:** Python + FastAPI. Cumple muy bien con el manejo rápido de validación de datos usando Pydantic. Use Inyección de Dependencias para separar la capa de transporte (rutas/API) de la capa lógica (casos de uso) y base de datos.
- **Async Workers (Celery + Redis):** Quería evitar bloquear el event loop principal de la API. Usé Celery para delegar la carga pesada de procesar lote de facturas por debajo de la mesa y Redis como broker y backend de resultados.
- **Persistencia:** PostgreSQL vía SQLAlchemy manejando el modelo de documentos.
- **Frontend:** React estructurado de forma minimalista. El foco fue resolver el polling de estados asíncronos correctamente (usando hooks para no dejar memory leaks tras recibir estados terminales) y construir una UI limpia. (Se que mi front no es muy estructurado, no me juzgen jaja)
- **Infraestructura y Deploy:** `docker-compose` para orquestar los 5 contenedores de forma aislada. Adicionalmente, creé un proxy reverso con Nginx en el contenedor frontend que resuelve todo el ruteo interno (evitando problemas de CORS u origenes cruzados).
- **Seguridad:** Agregué un Rate Limiter manual de ventana deslizante en FastAPI (usando caché de Redis) para blindar el endpoint si hay spikes, configurado a nivel global. Sumado a una validación estática de `X-API-Key`.

## Requisitos Previos

Solo necesitan tener instalado:
- **Docker** y **Docker Compose V2** 

## ¿Cómo levantar todo el proyecto?

Desde la carpeta raíz del proyecto, simplemente corre:

```bash
docker compose up --build -d
```

Ya está. Docker se encargará de descargar las imágenes (Postgres, Redis, Python, Nginx) compilar el backend, hacer el buildeo del bundle en React y levantar todo.

### ¿Dónde puedo verlo?

- **Frontend (Web App):** http://localhost
- **Backend (API Docs / Swagger):** http://localhost:8000/docs o http://localhost/api/docs
- **Doc Request (Postman - Bruno)** `./request_api_doc.json`

> *El frontend expone su puerto por el 80 (default http). Las peticiones que hace a `/api/*` las intercepta el proxy de Nginx de manera automática hacia el backend de FastAPI.*

## Testing local y CI/CD

Dejé configurado un pipeline básico usando __GitHub Actions__ que ejecuta la suite entera de tests unitarios y de integración (`pytest`). 

Pueden correrlos en local (asumiendo que existe un venv de Python configurado):

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

> **Detalle del test de Rate Limit:** El rate limiter está construido para tener "graceful degradation", por ende los tests usan un mock de Redis para no necesitar una instancia corriendo a la fuerza durante la integración continua.

## ¿Qué cosas se podrían mejorar a futuro?

Por tiempos, evité sobre-ingenieria de algunas funcionalidades, pero si pasáramos esto a un ambiente real haría un par de ajustes:
1. Agregar [Alembic] para el versionamiento y migración limpia de la base de datos (hoy el ORM crea todo on-the-fly en su inicio).
2. Para el front, implementar WebSockets en lugar de *HTTP Long Polling* reduciría latencias y tráfico al backend si el batch pasa a ser masivo.
3. El frontend no cuenta con tests completos, incluir Cypress o Jest.
