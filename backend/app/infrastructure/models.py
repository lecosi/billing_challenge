from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum
from app.infrastructure.database import Base
from app.domain.models import DocumentState, DocumentType
import datetime

class DocumentDB(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    invoice_type = Column(SQLEnum(DocumentType), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(SQLEnum(DocumentState), default=DocumentState.DRAFT, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    metadata_doc = Column(JSON, default=dict)
