from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.domain.models import DocumentState, DocumentType, JobStatus


class DocumentCreate(BaseModel):
    """Payload to create a new billing document."""

    invoice_type: DocumentType = Field(
        ...,
        description="Type of billing document",
        examples=["invoice"],
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Document amount — must be greater than zero",
        examples=[1500.50],
    )
    metadata_doc: Dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata",
        description="Optional free-form metadata to attach to the document",
        examples=[{"client": "Acme Corp", "reference": "REF-001"}],
    )



class DocumentUpdate(BaseModel):
    """Payload for partially updating a billing document.

    All fields are optional — only the fields provided will be changed.
    Status is intentionally excluded: use the batch/process endpoint
    to drive state transitions through the state machine.
    """

    model_config = ConfigDict(populate_by_name=True)

    invoice_type: Optional[DocumentType] = Field(
        default=None,
        description="New document type (replaces current type)",
        examples=["receipt"],
    )
    amount: Optional[float] = Field(
        default=None,
        gt=0,
        description="New amount — must be greater than zero if provided",
        examples=[2000.00],
    )
    metadata_doc: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="metadata",
        description="New metadata object (replaces current metadata entirely)",
        examples=[{"client": "Beta LLC", "reference": "REF-002"}],
    )

    @model_validator(mode="after")
    def at_least_one_field(self) -> "DocumentUpdate":
        """Reject a payload where every field is None (no-op update)."""
        if self.invoice_type is None and self.amount is None and self.metadata_doc is None:
            raise ValueError("At least one field must be provided for an update.")
        return self



class DocumentResponse(BaseModel):
    """Full representation of a billing document."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Unique document identifier (UUID)")
    invoice_type: DocumentType = Field(description="Type of billing document")
    amount: float = Field(description="Document amount")
    status: DocumentState = Field(description="Current document status in the workflow")
    created_at: datetime = Field(description="UTC timestamp when the document was created")
    metadata_doc: Dict[str, Any] = Field(
        alias="metadata",
        description="Free-form metadata attached to the document",
    )


class PaginatedDocumentResponse(BaseModel):
    """Paginated list of billing documents."""

    items: List[DocumentResponse] = Field(description="Documents on the current page")
    total: int = Field(description="Total number of documents matching the applied filters")
    skip: int = Field(description="Number of records skipped (offset)")
    limit: int = Field(description="Maximum number of records returned per page")


class BatchProcessRequest(BaseModel):
    """Request body for submitting a batch processing job."""

    document_ids: List[str] = Field(
        ...,
        description="List of document IDs to process",
        examples=[["uuid-1", "uuid-2"]],
    )


class BatchProcessResponse(BaseModel):
    """Response returned when a batch job is successfully accepted."""

    job_id: str = Field(description="Unique identifier of the created batch job")
    message: str = Field(description="Human-readable confirmation message")


class JobResponse(BaseModel):
    """Full representation of a batch processing job."""

    id: str = Field(description="Unique job identifier (UUID)")
    document_ids: List[str] = Field(description="IDs of the documents included in this job")
    status: JobStatus = Field(description="Current job status: pending | processing | completed | failed")
    created_at: datetime = Field(description="UTC timestamp when the job was created")
    completed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the job finished (null if still running)",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if the job failed (null otherwise)",
    )
