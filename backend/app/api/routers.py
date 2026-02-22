from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.api.schemas import (
    DocumentCreate, DocumentResponse, PaginatedDocumentResponse,
    BatchProcessRequest, JobResponse
)
from app.application.use_cases import DocumentUseCase, BatchJobUseCase
from app.domain.models import DocumentType, DocumentState
from app.api.dependencies import get_document_use_case, get_batch_job_use_case
from app.api.auth import get_api_key

router = APIRouter(dependencies=[Depends(get_api_key)])

@router.post("/documents", response_model=DocumentResponse, status_code=201)
def create_document(
    doc_in: DocumentCreate,
    use_case: DocumentUseCase = Depends(get_document_use_case)
):
    new_doc = use_case.create_document(
        invoice_type=doc_in.invoice_type,
        amount=doc_in.amount,
        metadata_doc=doc_in.metadata_doc
    )
    return new_doc

@router.get("/documents", response_model=PaginatedDocumentResponse)
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    invoice_type: Optional[DocumentType] = None,
    status: Optional[DocumentState] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    use_case: DocumentUseCase = Depends(get_document_use_case)
):
    documents, total = use_case.search_documents(
        skip=skip, limit=limit,
        invoice_type=invoice_type, status=status,
        min_amount=min_amount, max_amount=max_amount,
        start_date=start_date, end_date=end_date
    )
    return {"items": documents, "total": total, "skip": skip, "limit": limit}

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str, use_case: DocumentUseCase = Depends(get_document_use_case)):
    doc = use_case.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/documents/batch/process", response_model=dict, status_code=202)
def process_documents_batch(
    request: BatchProcessRequest,
    use_case: BatchJobUseCase = Depends(get_batch_job_use_case)
):
    try:
        job = use_case.create_batch_process(request.document_ids)
        return {"job_id": job.id, "message": "Batch processing started successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, use_case: BatchJobUseCase = Depends(get_batch_job_use_case)):
    job = use_case.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job