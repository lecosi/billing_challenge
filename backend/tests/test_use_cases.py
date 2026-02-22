"""
test_use_cases.py — Application layer tests (use cases).

Uses real repositories backed by an in-memory SQLite database (via conftest.py fixtures).
Celery tasks are mocked with 'with patch(...)' to avoid requiring a live broker.
"""
import pytest
from unittest.mock import patch

from app.application.use_cases import DocumentUseCase, BatchJobUseCase
from app.infrastructure.repository import DocumentRepository, JobRepository
from app.domain.models import DocumentType, DocumentState

CELERY_TASK_PATH = "app.infrastructure.tasks.process_documents_task.delay"


# ================================================================
# DocumentUseCase
# ================================================================

class TestDocumentUseCase:
    """Tests for DocumentUseCase methods: create, retrieve, and search."""

    @pytest.fixture
    def use_case(self, db_session):
        """Provides a DocumentUseCase instance backed by the test SQLite session."""
        return DocumentUseCase(DocumentRepository(db_session))

    def test_create_document_returns_document_with_id(self, use_case):
        """create_document returns a persisted Document with a generated ID and DRAFT status."""
        doc = use_case.create_document(invoice_type=DocumentType.INVOICE, amount=500.0)
        assert doc.id is not None
        assert doc.status == DocumentState.DRAFT
        assert doc.amount == 500.0

    def test_create_document_with_metadata(self, use_case):
        """Metadata passed to create_document is stored and returned unchanged."""
        doc = use_case.create_document(
            invoice_type=DocumentType.RECEIPT,
            amount=200.0,
            metadata_doc={"client": "Acme Corp"},
        )
        assert doc.metadata_doc == {"client": "Acme Corp"}

    def test_create_document_none_metadata_defaults_to_empty_dict(self, use_case):
        """Passing None for metadata_doc results in an empty dict being stored."""
        doc = use_case.create_document(
            invoice_type=DocumentType.INVOICE,
            amount=100.0,
            metadata_doc=None,
        )
        assert doc.metadata_doc == {}

    def test_get_document_returns_saved_document(self, use_case):
        """get_document retrieves the same document that was previously created."""
        created = use_case.create_document(invoice_type=DocumentType.INVOICE, amount=100.0)
        found = use_case.get_document(created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_document_returns_none_for_unknown_id(self, use_case):
        """get_document returns None when the provided ID does not exist."""
        result = use_case.get_document("non-existent-id")
        assert result is None

    def test_search_returns_all_documents(self, use_case):
        """search_documents with no filters returns all records and the correct total."""
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=100.0)
        use_case.create_document(invoice_type=DocumentType.RECEIPT, amount=200.0)

        docs, total = use_case.search_documents(skip=0, limit=10)
        assert total == 2
        assert len(docs) == 2

    def test_search_filter_by_invoice_type(self, use_case):
        """Filtering by invoice_type returns only documents of that type."""
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=100.0)
        use_case.create_document(invoice_type=DocumentType.RECEIPT, amount=200.0)

        docs, total = use_case.search_documents(skip=0, limit=10, invoice_type=DocumentType.INVOICE)
        assert total == 1
        assert docs[0].invoice_type == DocumentType.INVOICE

    def test_search_filter_by_status(self, use_case):
        """Filtering by status=DRAFT returns all newly created documents."""
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=100.0)
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=200.0)

        docs, total = use_case.search_documents(skip=0, limit=10, status=DocumentState.DRAFT)
        assert total == 2

    def test_search_filter_by_min_amount(self, use_case):
        """Filtering by min_amount excludes documents with lower amounts."""
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=50.0)
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=500.0)

        docs, total = use_case.search_documents(skip=0, limit=10, min_amount=100.0)
        assert total == 1
        assert docs[0].amount == 500.0

    def test_search_filter_by_max_amount(self, use_case):
        """Filtering by max_amount excludes documents with higher amounts."""
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=50.0)
        use_case.create_document(invoice_type=DocumentType.INVOICE, amount=500.0)

        docs, total = use_case.search_documents(skip=0, limit=10, max_amount=100.0)
        assert total == 1
        assert docs[0].amount == 50.0

    def test_search_pagination_skip(self, use_case):
        """The skip parameter offsets the result window; total count is unaffected."""
        for i in range(5):
            use_case.create_document(invoice_type=DocumentType.INVOICE, amount=float(i + 1) * 100)

        docs, total = use_case.search_documents(skip=3, limit=10)
        assert total == 5
        assert len(docs) == 2

    def test_search_pagination_limit(self, use_case):
        """The limit parameter caps the number of returned items; total count is unaffected."""
        for i in range(5):
            use_case.create_document(invoice_type=DocumentType.INVOICE, amount=float(i + 1) * 100)

        docs, total = use_case.search_documents(skip=0, limit=2)
        assert total == 5
        assert len(docs) == 2

    def test_search_empty_db_returns_zero(self, use_case):
        """Searching an empty database returns an empty list and total=0."""
        docs, total = use_case.search_documents(skip=0, limit=10)
        assert total == 0
        assert docs == []


# ================================================================
# BatchJobUseCase
# ================================================================

class TestBatchJobUseCase:
    """Tests for BatchJobUseCase methods: batch creation and job status retrieval."""

    @pytest.fixture
    def repos(self, db_session):
        """Provides both repositories sharing the SAME SQLite session to ensure consistency."""
        return JobRepository(db_session), DocumentRepository(db_session)

    @pytest.fixture
    def use_case(self, repos):
        """Provides a BatchJobUseCase instance backed by the shared test session."""
        job_repo, doc_repo = repos
        return BatchJobUseCase(job_repo=job_repo, doc_repo=doc_repo)

    @pytest.fixture
    def draft_document(self, repos):
        """Creates and persists a DRAFT document for use in batch tests."""
        _, doc_repo = repos
        return DocumentUseCase(doc_repo).create_document(
            invoice_type=DocumentType.INVOICE, amount=300.0
        )

    def test_create_batch_process_returns_job(self, use_case, draft_document):
        """create_batch_process returns a BatchJob with a generated ID."""
        with patch(CELERY_TASK_PATH):
            job = use_case.create_batch_process([draft_document.id])
        assert job is not None
        assert job.id is not None

    def test_create_batch_process_enqueues_celery_task(self, use_case, draft_document):
        """create_batch_process dispatches exactly one Celery task with the job ID."""
        with patch(CELERY_TASK_PATH) as mock_delay:
            job = use_case.create_batch_process([draft_document.id])
            mock_delay.assert_called_once_with(job.id)

    def test_create_batch_process_changes_doc_to_pending(self, use_case, draft_document, repos):
        """Documents included in the batch transition to PENDING status."""
        with patch(CELERY_TASK_PATH):
            use_case.create_batch_process([draft_document.id])

        _, doc_repo = repos
        updated_doc = doc_repo.get_by_id(draft_document.id)
        assert updated_doc.status == DocumentState.PENDING

    def test_create_batch_process_raises_for_unknown_document(self, use_case):
        """Submitting an unknown document ID raises ValueError with 'not found'."""
        with pytest.raises(ValueError, match="not found"):
            with patch(CELERY_TASK_PATH):
                use_case.create_batch_process(["id-does-not-exist"])

    def test_create_batch_does_not_enqueue_if_doc_not_found(self, use_case):
        """No Celery task is dispatched when a document ID is not found."""
        with patch(CELERY_TASK_PATH) as mock_delay:
            with pytest.raises(ValueError):
                use_case.create_batch_process(["bad-id"])
            mock_delay.assert_not_called()

    def test_get_job_status_returns_existing_job(self, use_case, draft_document):
        """get_job_status retrieves the same job that was previously created."""
        with patch(CELERY_TASK_PATH):
            job = use_case.create_batch_process([draft_document.id])

        found = use_case.get_job_status(job.id)
        assert found is not None
        assert found.id == job.id

    def test_get_job_status_returns_none_for_unknown_id(self, use_case):
        """get_job_status returns None when the provided job ID does not exist."""
        result = use_case.get_job_status("non-existent-job-id")
        assert result is None
