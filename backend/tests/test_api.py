"""
test_api.py — Integration tests for the HTTP API endpoints.

Uses FastAPI's TestClient backed by an in-memory SQLite database (see conftest.py).
Celery tasks are mocked with 'with patch(...)' inside each test body to avoid
argument-ordering conflicts between @patch and pytest class-based fixtures.
"""
import pytest
from unittest.mock import patch
from app.application.use_cases import DocumentUseCase
from app.infrastructure.repository import DocumentRepository
from app.domain.models import DocumentType, DocumentState

CELERY_TASK_PATH = "app.infrastructure.tasks.process_documents_task.delay"


# ================================================================
# POST /documents — Create a new billing document
# ================================================================

class TestCreateDocument:
    """Tests for the POST /documents endpoint."""

    def test_happy_path_create_invoice(self, client, headers, valid_doc_payload):
        """Creating a valid invoice returns 201 with all expected fields."""
        response = client.post("/documents", json=valid_doc_payload, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["invoice_type"] == "invoice"
        assert data["amount"] == 1500.50
        assert data["status"] == "draft"
        assert "id" in data
        assert "created_at" in data

    def test_create_receipt(self, client, headers):
        """A document with type 'receipt' is created successfully."""
        payload = {"invoice_type": "receipt", "amount": 200.0, "metadata": {}}
        response = client.post("/documents", json=payload, headers=headers)

        assert response.status_code == 201
        assert response.json()["invoice_type"] == "receipt"

    def test_create_proof_of_payment(self, client, headers):
        """A document with type 'proof of payment' is created successfully."""
        payload = {"invoice_type": "proof of payment", "amount": 999.99, "metadata": {}}
        response = client.post("/documents", json=payload, headers=headers)

        assert response.status_code == 201
        assert response.json()["invoice_type"] == "proof of payment"

    def test_create_document_with_metadata(self, client, headers):
        """Metadata fields provided in the request are persisted and returned."""
        payload = {
            "invoice_type": "invoice",
            "amount": 500.0,
            "metadata": {"client": "Acme Corp", "reference": "REF-001"},
        }
        response = client.post("/documents", json=payload, headers=headers)

        assert response.status_code == 201
        assert response.json()["metadata"]["client"] == "Acme Corp"

    def test_create_document_zero_amount_returns_422(self, client, headers):
        """Amount equal to zero is rejected with Unprocessable Entity."""
        payload = {"invoice_type": "invoice", "amount": 0, "metadata": {}}
        response = client.post("/documents", json=payload, headers=headers)
        assert response.status_code == 422

    def test_create_document_negative_amount_returns_422(self, client, headers):
        """Negative amounts are rejected with Unprocessable Entity."""
        payload = {"invoice_type": "invoice", "amount": -100, "metadata": {}}
        response = client.post("/documents", json=payload, headers=headers)
        assert response.status_code == 422

    def test_create_document_invalid_type_returns_422(self, client, headers):
        """An unrecognised invoice_type is rejected with Unprocessable Entity."""
        payload = {"invoice_type": "unknown_type", "amount": 100, "metadata": {}}
        response = client.post("/documents", json=payload, headers=headers)
        assert response.status_code == 422

    def test_create_document_missing_amount_returns_422(self, client, headers):
        """Omitting the required 'amount' field is rejected with Unprocessable Entity."""
        payload = {"invoice_type": "invoice"}
        response = client.post("/documents", json=payload, headers=headers)
        assert response.status_code == 422

    def test_create_document_without_api_key_returns_401(self, client, valid_doc_payload):
        """Requests without an API key are rejected with Unauthorized."""
        response = client.post("/documents", json=valid_doc_payload)
        assert response.status_code == 401

    def test_create_document_wrong_api_key_returns_401(self, client, valid_doc_payload):
        """Requests with an incorrect API key are rejected with Unauthorized."""
        response = client.post(
            "/documents",
            json=valid_doc_payload,
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401


# ================================================================
# GET /documents/{doc_id} — Retrieve a single document
# ================================================================

class TestGetDocument:
    """Tests for the GET /documents/{doc_id} endpoint."""

    def test_get_existing_document(self, client, headers, valid_doc_payload):
        """A document that was just created can be retrieved by its ID."""
        create_resp = client.post("/documents", json=valid_doc_payload, headers=headers)
        doc_id = create_resp.json()["id"]

        response = client.get(f"/documents/{doc_id}", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == doc_id

    def test_get_document_data_matches(self, client, headers, valid_doc_payload):
        """The retrieved document contains the same data that was submitted."""
        doc_id = client.post("/documents", json=valid_doc_payload, headers=headers).json()["id"]

        data = client.get(f"/documents/{doc_id}", headers=headers).json()
        assert data["amount"] == 1500.50
        assert data["invoice_type"] == "invoice"
        assert data["status"] == "draft"

    def test_get_nonexistent_document_returns_404(self, client, headers):
        """Requesting a document with an unknown ID returns Not Found."""
        response = client.get("/documents/non-existent-id", headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_document_without_api_key_returns_401(self, client):
        """Unauthenticated requests are rejected with Unauthorized."""
        response = client.get("/documents/any-id")
        assert response.status_code == 401


# ================================================================
# GET /documents — List and filter documents
# ================================================================

class TestListDocuments:
    """Tests for the GET /documents endpoint (listing and filtering)."""

    def _create_doc(self, client, headers, invoice_type="invoice", amount=100.0):
        """Helper: create and return a single document via the API."""
        payload = {"invoice_type": invoice_type, "amount": amount, "metadata": {}}
        return client.post("/documents", json=payload, headers=headers).json()

    def test_list_empty_returns_zero_total(self, client, headers):
        """An empty database returns total=0 and an empty items list."""
        response = client.get("/documents", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["items"] == []

    def test_list_returns_all_created_documents(self, client, headers):
        """All created documents are present in the listing response."""
        self._create_doc(client, headers)
        self._create_doc(client, headers, amount=200.0)

        data = client.get("/documents", headers=headers).json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_pagination_limit(self, client, headers):
        """The 'limit' query parameter caps the number of returned items."""
        for i in range(5):
            self._create_doc(client, headers, amount=float(i + 1) * 100)

        data = client.get("/documents?limit=2", headers=headers).json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_pagination_skip(self, client, headers):
        """The 'skip' query parameter offsets the result set correctly."""
        for i in range(5):
            self._create_doc(client, headers, amount=float(i + 1) * 100)

        data = client.get("/documents?skip=4&limit=10", headers=headers).json()
        assert data["total"] == 5
        assert len(data["items"]) == 1

    def test_filter_by_invoice_type(self, client, headers):
        """Filtering by invoice_type returns only documents of that type."""
        self._create_doc(client, headers, invoice_type="invoice")
        self._create_doc(client, headers, invoice_type="receipt")

        data = client.get("/documents?invoice_type=invoice", headers=headers).json()
        assert data["total"] == 1
        assert data["items"][0]["invoice_type"] == "invoice"

    def test_filter_by_min_amount(self, client, headers):
        """Filtering by min_amount excludes documents below the threshold."""
        self._create_doc(client, headers, amount=50.0)
        self._create_doc(client, headers, amount=500.0)

        data = client.get("/documents?min_amount=100", headers=headers).json()
        assert data["total"] == 1
        assert data["items"][0]["amount"] == 500.0

    def test_filter_by_max_amount(self, client, headers):
        """Filtering by max_amount excludes documents above the threshold."""
        self._create_doc(client, headers, amount=50.0)
        self._create_doc(client, headers, amount=500.0)

        data = client.get("/documents?max_amount=100", headers=headers).json()
        assert data["total"] == 1
        assert data["items"][0]["amount"] == 50.0

    def test_filter_by_status_draft(self, client, headers):
        """Filtering by status=draft returns only newly created documents."""
        self._create_doc(client, headers)

        data = client.get("/documents?status=draft", headers=headers).json()
        assert data["total"] == 1

    def test_limit_exceeds_max_returns_422(self, client, headers):
        """A limit value above the allowed maximum (100) is rejected."""
        response = client.get("/documents?limit=999", headers=headers)
        assert response.status_code == 422

    def test_negative_skip_returns_422(self, client, headers):
        """A negative skip value is rejected with Unprocessable Entity."""
        response = client.get("/documents?skip=-1", headers=headers)
        assert response.status_code == 422

    def test_list_without_api_key_returns_401(self, client):
        """Unauthenticated listing requests are rejected with Unauthorized."""
        response = client.get("/documents")
        assert response.status_code == 401

    def test_response_includes_pagination_metadata(self, client, headers):
        """The response body includes skip and limit pagination fields."""
        data = client.get("/documents?skip=0&limit=5", headers=headers).json()
        assert data["skip"] == 0
        assert data["limit"] == 5


# ================================================================
# POST /documents/batch/process — Submit a batch job
# ================================================================

class TestBatchProcess:
    """Tests for the POST /documents/batch/process endpoint."""

    def _create_draft_doc(self, client, headers):
        """Helper: create and return a document in DRAFT state."""
        payload = {"invoice_type": "invoice", "amount": 100.0, "metadata": {}}
        return client.post("/documents", json=payload, headers=headers).json()

    def test_batch_process_returns_202_and_job_id(self, client, headers):
        """A valid batch request returns Accepted with a job_id."""
        doc = self._create_draft_doc(client, headers)

        with patch(CELERY_TASK_PATH):
            response = client.post(
                "/documents/batch/process",
                json={"document_ids": [doc["id"]]},
                headers=headers,
            )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert "message" in data

    def test_batch_process_enqueues_celery_task(self, client, headers):
        """A successful batch request dispatches exactly one Celery task."""
        doc = self._create_draft_doc(client, headers)

        with patch(CELERY_TASK_PATH) as mock_delay:
            client.post(
                "/documents/batch/process",
                json={"document_ids": [doc["id"]]},
                headers=headers,
            )
            mock_delay.assert_called_once()

    def test_batch_process_multiple_documents(self, client, headers):
        """Multiple valid document IDs can be submitted in a single batch."""
        doc1 = self._create_draft_doc(client, headers)
        doc2 = self._create_draft_doc(client, headers)

        with patch(CELERY_TASK_PATH):
            response = client.post(
                "/documents/batch/process",
                json={"document_ids": [doc1["id"], doc2["id"]]},
                headers=headers,
            )

        assert response.status_code == 202

    def test_batch_process_document_moves_to_pending(self, client, headers):
        """After submitting a batch, included documents transition to PENDING status."""
        doc = self._create_draft_doc(client, headers)

        with patch(CELERY_TASK_PATH):
            client.post(
                "/documents/batch/process",
                json={"document_ids": [doc["id"]]},
                headers=headers,
            )

        updated = client.get(f"/documents/{doc['id']}", headers=headers).json()
        assert updated["status"] == "pending"

    def test_batch_process_unknown_document_returns_400(self, client, headers):
        """Submitting an ID that does not exist returns Bad Request."""
        response = client.post(
            "/documents/batch/process",
            json={"document_ids": ["id-does-not-exist"]},
            headers=headers,
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_batch_process_without_api_key_returns_401(self, client):
        """Unauthenticated batch requests are rejected with Unauthorized."""
        response = client.post(
            "/documents/batch/process",
            json={"document_ids": ["any"]},
        )
        assert response.status_code == 401


# ================================================================
# GET /jobs/{job_id} — Query a batch job status
# ================================================================

class TestGetJobStatus:
    """Tests for the GET /jobs/{job_id} endpoint."""

    def _create_job(self, client, headers):
        """Helper: create a document and submit a batch to obtain a valid job ID."""
        doc_payload = {"invoice_type": "invoice", "amount": 100.0, "metadata": {}}
        doc = client.post("/documents", json=doc_payload, headers=headers).json()

        with patch(CELERY_TASK_PATH):
            batch_resp = client.post(
                "/documents/batch/process",
                json={"document_ids": [doc["id"]]},
                headers=headers,
            )
        return batch_resp.json()["job_id"]

    def test_get_existing_job_returns_200(self, client, headers):
        """A job that was just created can be retrieved by its ID."""
        job_id = self._create_job(client, headers)

        response = client.get(f"/jobs/{job_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["status"] in ("pending", "processing", "completed", "failed")
        assert "document_ids" in data

    def test_get_job_contains_correct_document_ids(self, client, headers):
        """The job response lists the document IDs that were submitted."""
        doc_payload = {"invoice_type": "invoice", "amount": 100.0, "metadata": {}}
        doc_id = client.post("/documents", json=doc_payload, headers=headers).json()["id"]

        with patch(CELERY_TASK_PATH):
            job_id = client.post(
                "/documents/batch/process",
                json={"document_ids": [doc_id]},
                headers=headers,
            ).json()["job_id"]

        data = client.get(f"/jobs/{job_id}", headers=headers).json()
        assert doc_id in data["document_ids"]

    def test_get_nonexistent_job_returns_404(self, client, headers):
        """Requesting a job with an unknown ID returns Not Found."""
        response = client.get("/jobs/non-existent-job-id", headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_job_without_api_key_returns_401(self, client):
        """Unauthenticated job status requests are rejected with Unauthorized."""
        response = client.get("/jobs/any-id")
        assert response.status_code == 401


# ================================================================
# GET / — Health check
# ================================================================

class TestHealthCheck:
    """Tests for the root health-check endpoint."""

    def test_health_check_returns_200(self, client):
        """The health-check endpoint is reachable and returns OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_check_body(self, client):
        """The health-check response contains status='ok'."""
        data = client.get("/").json()
        assert data["status"] == "ok"


# ================================================================
# PATCH /documents/{doc_id} — HTTP integration tests
# ================================================================

class TestUpdateDocument:
    """Integration tests for the PATCH /documents/{doc_id} endpoint."""

    def _create_doc(self, client, headers, invoice_type="invoice", amount=500.0):
        """Helper: create a document and return the full JSON response."""
        payload = {"invoice_type": invoice_type, "amount": amount, "metadata": {}}
        return client.post("/documents", json=payload, headers=headers).json()

    # --- Happy paths ---

    def test_update_amount_returns_200(self, client, headers):
        """Patching only the amount returns 200 with the new amount."""
        doc = self._create_doc(client, headers)

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"amount": 9999.99},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["amount"] == 9999.99

    def test_update_invoice_type_returns_200(self, client, headers):
        """Patching only the invoice_type returns 200 with the new type."""
        doc = self._create_doc(client, headers, invoice_type="invoice")

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"invoice_type": "receipt"},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["invoice_type"] == "receipt"

    def test_update_metadata_returns_200(self, client, headers):
        """Patching only the metadata replaces it entirely and returns 200."""
        doc = self._create_doc(client, headers)

        new_meta = {"client": "Beta LLC", "reference": "REF-042"}
        response = client.patch(
            f"/documents/{doc['id']}",
            json={"metadata": new_meta},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["metadata"] == new_meta

    def test_update_multiple_fields_at_once(self, client, headers):
        """Patching multiple fields at once updates all of them correctly."""
        doc = self._create_doc(client, headers)

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"amount": 1234.56, "invoice_type": "proof of payment"},
            headers=headers,
        )

        data = response.json()
        assert response.status_code == 200
        assert data["amount"] == 1234.56
        assert data["invoice_type"] == "proof of payment"

    def test_update_preserves_untouched_fields(self, client, headers):
        """Fields not included in the PATCH body remain unchanged."""
        doc = self._create_doc(client, headers, invoice_type="receipt", amount=100.0)

        client.patch(
            f"/documents/{doc['id']}",
            json={"amount": 200.0},
            headers=headers,
        )

        updated = client.get(f"/documents/{doc['id']}", headers=headers).json()
        assert updated["invoice_type"] == "receipt"  # untouched
        assert updated["amount"] == 200.0             # updated

    def test_update_preserves_status(self, client, headers):
        """Status is not modified by PATCH — it stays in its current state."""
        doc = self._create_doc(client, headers)
        assert doc["status"] == "draft"

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"amount": 999.0},
            headers=headers,
        )

        assert response.json()["status"] == "draft"

    def test_update_persists_change(self, client, headers):
        """A subsequent GET returns the values written by the PATCH."""
        doc = self._create_doc(client, headers)

        client.patch(
            f"/documents/{doc['id']}",
            json={"amount": 7777.0},
            headers=headers,
        )

        fetched = client.get(f"/documents/{doc['id']}", headers=headers).json()
        assert fetched["amount"] == 7777.0

    def test_update_preserves_id_and_created_at(self, client, headers):
        """PATCH must not alter the document's id or created_at fields."""
        from datetime import datetime, timezone

        doc = self._create_doc(client, headers)

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"amount": 500.0},
            headers=headers,
        )

        data = response.json()
        assert data["id"] == doc["id"]
        # SQLite strips timezone info on round-trip, so one timestamp may be
        # naive and the other timezone-aware. Strip tzinfo and compare naively.
        original_ts = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        patched_ts = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        assert original_ts == patched_ts

    # --- Validation edge cases ---

    def test_update_empty_body_returns_422(self, client, headers):
        """An empty JSON object (no fields) is rejected as a no-op update."""
        doc = self._create_doc(client, headers)

        response = client.patch(
            f"/documents/{doc['id']}",
            json={},
            headers=headers,
        )

        assert response.status_code == 422

    def test_update_zero_amount_returns_422(self, client, headers):
        """An amount of 0 is rejected by field validation."""
        doc = self._create_doc(client, headers)

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"amount": 0},
            headers=headers,
        )

        assert response.status_code == 422

    def test_update_negative_amount_returns_422(self, client, headers):
        """A negative amount is rejected by field validation."""
        doc = self._create_doc(client, headers)

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"amount": -50},
            headers=headers,
        )

        assert response.status_code == 422

    def test_update_invalid_invoice_type_returns_422(self, client, headers):
        """An unrecognised invoice_type is rejected with Unprocessable Entity."""
        doc = self._create_doc(client, headers)

        response = client.patch(
            f"/documents/{doc['id']}",
            json={"invoice_type": "unknown_type"},
            headers=headers,
        )

        assert response.status_code == 422

    # --- 404 ---

    def test_update_nonexistent_document_returns_404(self, client, headers):
        """Patching an unknown document ID returns Not Found."""
        response = client.patch(
            "/documents/does-not-exist",
            json={"amount": 100.0},
            headers=headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    # --- Authentication ---

    def test_update_without_api_key_returns_401(self, client):
        """Requests without an API key are rejected with Unauthorized."""
        response = client.patch("/documents/any-id", json={"amount": 100.0})
        assert response.status_code == 401

    def test_update_wrong_api_key_returns_401(self, client):
        """Requests with an incorrect API key are rejected with Unauthorized."""
        response = client.patch(
            "/documents/any-id",
            json={"amount": 100.0},
            headers={"X-API-Key": "totally-wrong-key"},
        )
        assert response.status_code == 401


# ================================================================
# DocumentUseCase.update_document — unit tests
# ================================================================

class TestUpdateDocumentUseCase:
    """Unit tests for DocumentUseCase.update_document (via real SQLite repo)."""

    @pytest.fixture
    def use_case(self, db_session):
        """Provides a DocumentUseCase backed by the in-memory SQLite session."""
        return DocumentUseCase(DocumentRepository(db_session))

    @pytest.fixture
    def existing_doc(self, use_case):
        """Creates a persisted DRAFT document for use in update tests."""
        return use_case.create_document(
            invoice_type=DocumentType.INVOICE,
            amount=300.0,
            metadata_doc={"original": True},
        )

    def test_update_amount(self, use_case, existing_doc):
        """update_document changes the amount and returns the updated document."""
        updated = use_case.update_document(existing_doc.id, amount=9999.0)
        assert updated is not None
        assert updated.amount == 9999.0

    def test_update_invoice_type(self, use_case, existing_doc):
        """update_document changes the invoice_type correctly."""
        updated = use_case.update_document(
            existing_doc.id, invoice_type=DocumentType.RECEIPT
        )
        assert updated.invoice_type == DocumentType.RECEIPT

    def test_update_metadata(self, use_case, existing_doc):
        """update_document replaces the metadata entirely."""
        new_meta = {"client": "New Client", "ref": "XYZ"}
        updated = use_case.update_document(existing_doc.id, metadata_doc=new_meta)
        assert updated.metadata_doc == new_meta

    def test_partial_update_does_not_change_other_fields(self, use_case, existing_doc):
        """Updating only the amount leaves invoice_type and metadata unchanged."""
        updated = use_case.update_document(existing_doc.id, amount=1.0)
        assert updated.invoice_type == existing_doc.invoice_type
        assert updated.metadata_doc == existing_doc.metadata_doc

    def test_update_returns_none_for_unknown_id(self, use_case):
        """update_document returns None when the document does not exist."""
        result = use_case.update_document("non-existent-id", amount=100.0)
        assert result is None

    def test_update_does_not_change_status(self, use_case, existing_doc):
        """update_document must never alter the status field."""
        updated = use_case.update_document(existing_doc.id, amount=50.0)
        assert updated.status == DocumentState.DRAFT
