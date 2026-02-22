"""
test_domain.py — Unit tests for domain models.

These tests exercise pure business logic and require no database or HTTP client.
They validate state machine transitions, field constraints, and default values
directly on the Pydantic domain models.
"""
import pytest
from pydantic import ValidationError

from app.domain.models import (
    Document,
    DocumentType,
    DocumentState,
    BatchJob,
    JobStatus,
    InvalidStateTransitionError,
)


# ================================================================
# Document — creation and field defaults
# ================================================================

class TestDocumentCreation:
    """Tests for Document instantiation, default values, and field constraints."""

    def test_default_status_is_draft(self):
        """A newly created document always starts in DRAFT status."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        assert doc.status == DocumentState.DRAFT

    def test_id_is_generated_automatically(self):
        """An ID is auto-generated as a UUID4 string (36 characters)."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        assert doc.id is not None
        assert len(doc.id) == 36

    def test_two_documents_have_different_ids(self):
        """Each document instance receives a unique identifier."""
        doc1 = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc2 = Document(invoice_type=DocumentType.INVOICE, amount=200)
        assert doc1.id != doc2.id

    def test_amount_must_be_greater_than_zero(self):
        """An amount of exactly zero is rejected by field validation."""
        with pytest.raises(ValidationError):
            Document(invoice_type=DocumentType.INVOICE, amount=0)

    def test_negative_amount_raises_validation_error(self):
        """Negative amounts are rejected by field validation."""
        with pytest.raises(ValidationError):
            Document(invoice_type=DocumentType.INVOICE, amount=-50)

    def test_metadata_defaults_to_empty_dict(self):
        """When no metadata is provided, it defaults to an empty dictionary."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        assert doc.metadata_doc == {}

    def test_all_document_types_are_valid(self):
        """Every member of DocumentType can be used to create a document."""
        for doc_type in DocumentType:
            doc = Document(invoice_type=doc_type, amount=1)
            assert doc.invoice_type == doc_type


# ================================================================
# Document — state machine transitions
# ================================================================

class TestDocumentStateTransitions:
    """Tests for the state machine methods on Document."""

    # --- submit_for_review: DRAFT → PENDING ---

    def test_submit_for_review_from_draft(self):
        """A DRAFT document transitions to PENDING after submit_for_review."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        assert doc.status == DocumentState.PENDING

    def test_submit_for_review_from_pending_raises(self):
        """Calling submit_for_review on a PENDING document is invalid."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        with pytest.raises(InvalidStateTransitionError):
            doc.submit_for_review()

    def test_submit_for_review_from_approved_raises(self):
        """Calling submit_for_review on an APPROVED document is invalid."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        doc.approve()
        with pytest.raises(InvalidStateTransitionError):
            doc.submit_for_review()

    def test_submit_for_review_from_rejected_raises(self):
        """Calling submit_for_review on a REJECTED document is invalid."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        doc.reject()
        with pytest.raises(InvalidStateTransitionError):
            doc.submit_for_review()

    # --- approve: PENDING → APPROVED ---

    def test_approve_from_pending(self):
        """A PENDING document transitions to APPROVED after approve."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        doc.approve()
        assert doc.status == DocumentState.APPROVED

    def test_approve_from_draft_raises(self):
        """Approving a DRAFT document raises InvalidStateTransitionError."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            doc.approve()
        assert "The document must be in pending status" in str(exc_info.value)

    def test_approve_from_approved_raises(self):
        """Approving an already APPROVED document raises InvalidStateTransitionError."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        doc.approve()
        with pytest.raises(InvalidStateTransitionError):
            doc.approve()

    # --- reject: PENDING → REJECTED ---

    def test_reject_from_pending(self):
        """A PENDING document transitions to REJECTED after reject."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        doc.reject()
        assert doc.status == DocumentState.REJECTED

    def test_reject_from_draft_raises(self):
        """Rejecting a DRAFT document raises InvalidStateTransitionError."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        with pytest.raises(InvalidStateTransitionError):
            doc.reject()

    def test_reject_from_approved_raises(self):
        """Rejecting an APPROVED document raises InvalidStateTransitionError."""
        doc = Document(invoice_type=DocumentType.INVOICE, amount=100)
        doc.submit_for_review()
        doc.approve()
        with pytest.raises(InvalidStateTransitionError):
            doc.reject()


# ================================================================
# BatchJob — status lifecycle
# ================================================================

class TestBatchJob:
    """Tests for BatchJob status transitions and field defaults."""

    def test_default_status_is_pending(self):
        """A newly created batch job starts in PENDING status."""
        job = BatchJob(document_ids=["id-1", "id-2"])
        assert job.status == JobStatus.PENDING

    def test_start_processing(self):
        """start_processing transitions the job to PROCESSING status."""
        job = BatchJob(document_ids=["id-1"])
        job.start_processing()
        assert job.status == JobStatus.PROCESSING

    def test_mark_as_completed(self):
        """mark_as_completed sets status to COMPLETED and records completed_at."""
        job = BatchJob(document_ids=["id-1"])
        job.start_processing()
        job.mark_as_completed()
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None

    def test_mark_as_failed(self):
        """mark_as_failed sets status to FAILED, records the error and completed_at."""
        job = BatchJob(document_ids=["id-1"])
        job.start_processing()
        job.mark_as_failed("Timeout error")
        assert job.status == JobStatus.FAILED
        assert job.error_message == "Timeout error"
        assert job.completed_at is not None

    def test_completed_at_is_none_by_default(self):
        """A new batch job has no completion timestamp."""
        job = BatchJob(document_ids=["id-1"])
        assert job.completed_at is None

    def test_document_ids_are_stored(self):
        """All submitted document IDs are stored on the batch job."""
        ids = ["abc", "def", "ghi"]
        job = BatchJob(document_ids=ids)
        assert job.document_ids == ids
