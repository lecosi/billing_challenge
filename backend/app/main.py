from fastapi import FastAPI
from app.infrastructure.database import engine, Base
from app.api.routers import router
from app.infrastructure.models import DocumentDB

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Duppla API - Facturacion",
    description="API REST para procesar facturas",
    version="1.0.0"
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "nitido"}