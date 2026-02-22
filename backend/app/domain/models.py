from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import BaseModel, Field
import uuid

class DocumentState(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PROOF_OF_PAYMENT = "proof of payment"
    
class InvalidStateTransitionError(ValueError):
    pass

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_type: DocumentType
    amount: float = Field(gt=0, description="The amount must be greater than zero.")
    status: DocumentState = Field(default=DocumentState.DRAFT)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata_doc: Dict[str, Any] = Field(default_factory=dict)

    def submit_for_review(self) -> None:
        # Draft -> Pending
        if self.status != DocumentState.DRAFT:
            raise InvalidStateTransitionError(f"The document cannot be changed to {DocumentState.PENDING.value} status from {self.status.value} status. ")
        self.status = DocumentState.PENDING

    def approve(self) -> None:
        # Pending -> Approved
        if self.status != DocumentState.PENDING:
            raise InvalidStateTransitionError(f"The document must be in {DocumentState.PENDING.value} status in order to be approved.")
        self.status = DocumentState.APPROVED

    def reject(self) -> None:
        # Pending -> Rejected
        if self.status != DocumentState.PENDING:
            raise InvalidStateTransitionError(f"The document must be in {DocumentState.PENDING.value} status in order to be rejected.")
        self.status = DocumentState.REJECTED
