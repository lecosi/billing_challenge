from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.infrastructure.database as db_module
from app.infrastructure.database import Base
from app.api.routers import router
from app.infrastructure.models import DocumentDB

Base.metadata.create_all(bind=db_module.engine)

openapi_tags = [
    {
        "name": "Documents",
        "description": (
            "Operations for managing billing documents. "
            "A document follows the state machine: **DRAFT → PENDING → APPROVED / REJECTED**."
        ),
    },
    {
        "name": "Batch",
        "description": (
            "Operations for submitting and tracking asynchronous batch processing jobs. "
            "Batch jobs are processed in the background via Celery workers."
        ),
    },
]

app = FastAPI(
    title="Billing API",
    description=(
        "REST API for managing and processing billing documents.\n\n"
        "## Authentication\n"
        "All endpoints require an `X-API-Key` header with a valid API key.\n\n"
        "## Document Lifecycle\n"
        "| Status | Description |\n"
        "|--------|-------------|\n"
        "| `draft` | Newly created document, not yet submitted |\n"
        "| `pending` | Submitted for review via a batch job |\n"
        "| `approved` | Approved by the processing worker |\n"
        "| `rejected` | Rejected by the processing worker |\n\n"
        "## Batch Processing\n"
        "Use `POST /documents/batch/process` to submit DRAFT documents for review. "
        "The endpoint returns a `job_id` — poll `GET /jobs/{job_id}` to track progress."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
    contact={
        "name": "Duppla Engineering",
        "email": "engineering@duppla.com",
    },
    license_info={
        "name": "MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA fallback
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"], summary="Health check", include_in_schema=True)
def health_check():
    """Returns a simple status message to confirm the API is running."""
    return {"status": "ok", "message": "nitido"}