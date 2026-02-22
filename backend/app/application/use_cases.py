from typing import List, Optional, Tuple, Dict, Any

from app.domain.models import Document, DocumentType
from app.infrastructure.repository import DocumentRepository

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