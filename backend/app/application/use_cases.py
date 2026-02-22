from typing import List, Optional, Tuple, Dict, Any

from app.domain.models import Document, DocumentType, BatchJob
from app.infrastructure.repository import DocumentRepository, JobRepository
from app.infrastructure.tasks import process_documents_task

class DocumentUseCase:
    def __init__(self, repository: DocumentRepository):
        self.repo = repository

    def create_document(self, invoice_type: DocumentType, amount: float, metadata_doc: Dict[str, Any] = None) -> Document:
        new_doc = Document(
            invoice_type=invoice_type, 
            amount=amount, 
            metadata_doc=metadata_doc or {}
        )
        return self.repo.save(new_doc)

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self.repo.get_by_id(doc_id)

    def search_documents(
        self, skip: int, limit: int, **filters
    ) -> Tuple[List[Document], int]:
        return self.repo.search(skip=skip, limit=limit, **filters)

class BatchJobUseCase:
    def __init__(self, job_repo: JobRepository, doc_repo: DocumentRepository):
        self.job_repo = job_repo
        self.doc_repo = doc_repo

    def create_batch_process(self, document_ids: List[str]) -> BatchJob:
        docs_to_process = []
    
        for doc_id in document_ids:
            doc = self.doc_repo.get_by_id(doc_id)
            if not doc:
                raise ValueError(f"Document with ID {doc_id} not found.")

            doc.submit_for_review()
            docs_to_process.append(doc)

        for doc in docs_to_process:
            self.doc_repo.save(doc)

        new_job = BatchJob(document_ids=document_ids)
        saved_job = self.job_repo.save(new_job)

        process_documents_task.delay(saved_job.id)

        return saved_job

    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        return self.job_repo.get_by_id(job_id)