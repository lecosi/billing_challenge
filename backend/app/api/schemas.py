from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.domain.models import DocumentState, DocumentType, JobStatus

class DocumentCreate(BaseModel):
    invoice_type: DocumentType
    amount: float = Field(gt=0, description="El monto debe ser mayor a cero")
    metadata_doc: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

class DocumentResponse(BaseModel):
    id: str
    invoice_type: DocumentType
    amount: float
    status: DocumentState
    created_at: datetime
    metadata_doc: Dict[str, Any] = Field(alias="metadata")

    class Config:
        populate_by_name = True

class PaginatedDocumentResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    skip: int
    limit: int

class BatchProcessRequest(BaseModel):
    document_ids: List[str]

class JobResponse(BaseModel):
    id: str
    document_ids: List[str]
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
