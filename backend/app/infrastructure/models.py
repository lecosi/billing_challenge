from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum, ARRAY
from sqlalchemy.types import TypeDecorator
from app.infrastructure.database import Base
from app.domain.models import DocumentState, DocumentType, JobStatus
import datetime


class StringList(TypeDecorator):
    """
    Tipo portable para listas de strings.
    - PostgreSQL → ARRAY(String)  (nativo, igual al comportamiento anterior)
    - Otros motores (SQLite) → JSON  (para tests sin PostgreSQL)
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value  # ambos tipos aceptan listas de Python directamente

    def process_result_value(self, value, dialect):
        return value if value is not None else []

class DocumentDB(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    invoice_type = Column(SQLEnum(DocumentType), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(SQLEnum(DocumentState), default=DocumentState.DRAFT, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    metadata_doc = Column(JSON, default=dict)

class BatchJobDB(Base):
    __tablename__ = "batch_jobs"

    id = Column(String, primary_key=True, index=True)
    document_ids = Column(StringList, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
