from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.api.schemas import (
    DocumentCreate, DocumentResponse, PaginatedDocumentResponse,
    BatchProcessRequest, JobResponse, BatchProcessResponse, DocumentUpdate
)
from app.application.use_cases import DocumentUseCase, BatchJobUseCase
from app.domain.models import DocumentType, DocumentState
from app.api.dependencies import get_document_use_case, get_batch_job_use_case
from app.api.auth import get_api_key, rate_limiter

router = APIRouter(
    dependencies=[Depends(get_api_key), Depends(rate_limiter)],
    responses={401: {"description": "Invalid or missing API key"}},
)


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=201,
    summary="Create a billing document",
    description=(
        "Creates a new billing document in **DRAFT** status. "
        "The document must include a valid `invoice_type` and an `amount` greater than zero. "
        "Optional `metadata` can be attached as a free-form JSON object."
    ),
    responses={
        201: {"description": "Document created successfully"},
        422: {"description": "Validation error — invalid payload"},
    },
    tags=["Documents"],
)
def create_document(
    doc_in: DocumentCreate,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    new_doc = use_case.create_document(
        invoice_type=doc_in.invoice_type,
        amount=doc_in.amount,
        metadata_doc=doc_in.metadata_doc,
    )
    return new_doc


@router.get(
    "/documents",
    response_model=PaginatedDocumentResponse,
    summary="List and filter billing documents",
    description=(
        "Returns a paginated list of billing documents. "
        "Results can be filtered by `invoice_type`, `status`, amount range, and creation date range. "
        "Documents are returned in descending order by creation date."
    ),
    responses={
        200: {"description": "Paginated list of documents"},
        422: {"description": "Validation error — invalid query parameter"},
    },
    tags=["Documents"],
)
def list_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip (offset)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return (max 100)"),
    invoice_type: Optional[DocumentType] = Query(None, description="Filter by document type"),
    status: Optional[DocumentState] = Query(None, description="Filter by document status"),
    min_amount: Optional[float] = Query(None, description="Filter documents with amount >= this value"),
    max_amount: Optional[float] = Query(None, description="Filter documents with amount <= this value"),
    start_date: Optional[datetime] = Query(None, description="Filter documents created on or after this datetime (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter documents created on or before this datetime (ISO 8601)"),
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    documents, total = use_case.search_documents(
        skip=skip, limit=limit,
        invoice_type=invoice_type, status=status,
        min_amount=min_amount, max_amount=max_amount,
        start_date=start_date, end_date=end_date,
    )
    return {"items": documents, "total": total, "skip": skip, "limit": limit}


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Retrieve a document by ID",
    description="Returns the full details of a single billing document identified by its UUID.",
    responses={
        200: {"description": "Document found"},
        404: {"description": "Document not found"},
    },
    tags=["Documents"],
)
def get_document(
    doc_id: str,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    doc = use_case.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Partially update a billing document",
    description=(
        "Updates one or more fields of an existing billing document. "
        "Only the fields provided in the request body will be changed — omitted fields remain untouched. "
        "**Status cannot be changed via this endpoint**: use `POST /documents/batch/process` "
        "to drive state transitions through the state machine."
    ),
    responses={
        200: {"description": "Document updated successfully"},
        404: {"description": "Document not found"},
        422: {"description": "Validation error — invalid payload or empty body"},
    },
    tags=["Documents"],
)
def update_document(
    doc_id: str,
    doc_in: DocumentUpdate,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    updated = use_case.update_document(
        doc_id=doc_id,
        invoice_type=doc_in.invoice_type,
        amount=doc_in.amount,
        metadata_doc=doc_in.metadata_doc,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Document not found")
    return updated


@router.post(
    "/documents/batch/process",
    response_model=BatchProcessResponse,
    status_code=202,
    summary="Submit a batch processing job",
    description=(
        "Submits a list of DRAFT document IDs for asynchronous batch processing. "
        "Each document transitions to **PENDING** status immediately. "
        "A background worker will then **approve** or **reject** each document. "
        "Returns a `job_id` that can be used to track the processing status."
    ),
    responses={
        202: {"description": "Batch job accepted and enqueued"},
        400: {"description": "One or more document IDs were not found"},
    },
    tags=["Batch"],
)
def process_documents_batch(
    request: BatchProcessRequest,
    use_case: BatchJobUseCase = Depends(get_batch_job_use_case),
):
    try:
        job = use_case.create_batch_process(request.document_ids)
        return {"job_id": job.id, "message": "Batch processing started successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get batch job status",
    description=(
        "Returns the current status and metadata of a batch processing job. "
        "Possible statuses: `pending`, `processing`, `completed`, `failed`. "
        "When the job finishes, `completed_at` is populated. "
        "On failure, `error_message` contains the reason."
    ),
    responses={
        200: {"description": "Job found"},
        404: {"description": "Job not found"},
    },
    tags=["Batch"],
)
def get_job_status(
    job_id: str,
    use_case: BatchJobUseCase = Depends(get_batch_job_use_case),
):
    job = use_case.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job