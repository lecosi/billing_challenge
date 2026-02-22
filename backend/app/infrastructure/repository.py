from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Tuple
from datetime import datetime

from app.domain.models import Document, DocumentState, DocumentType
from app.infrastructure.models import DocumentDB

class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, document: Document) -> Document:
        db_doc = self.db.query(DocumentDB).filter(DocumentDB.id == document.id).first()
        
        if not db_doc:
            db_doc = DocumentDB(
                id=document.id,
                invoice_type=document.invoice_type,
                amount=document.amount,
                status=document.status,
                created_at=document.created_at,
                metadata_doc=document.metadata_doc
            )
            self.db.add(db_doc)
        else:
            db_doc.invoice_type = document.invoice_type
            db_doc.amount = document.amount
            db_doc.status = document.status
            db_doc.metadata_doc = document.metadata_doc
            
        self.db.commit()
        return document

    def get_by_id(self, doc_id: str) -> Optional[Document]:
        db_doc = self.db.query(DocumentDB).filter(DocumentDB.id == doc_id).first()
        if not db_doc:
            return None
            
        return Document(
            id=db_doc.id,
            invoice_type=db_doc.invoice_type,
            amount=db_doc.amount,
            status=db_doc.status,
            created_at=db_doc.created_at,
            metadata_doc=db_doc.metadata_doc
        )

    def search(
        self, 
        skip: int = 0, 
        limit: int = 10,
        invoice_type: Optional[DocumentType] = None,
        status: Optional[DocumentState] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[Document], int]:
        query = self.db.query(DocumentDB)

        if invoice_type:
            query = query.filter(DocumentDB.invoice_type == invoice_type)
        if status:
            query = query.filter(DocumentDB.status == status)
        if min_amount is not None:
            query = query.filter(DocumentDB.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(DocumentDB.amount <= max_amount)
        if start_date:
            query = query.filter(DocumentDB.created_at >= start_date)
        if end_date:
            query = query.filter(DocumentDB.created_at <= end_date)

        total = query.count()
        
        db_docs = query.order_by(desc(DocumentDB.created_at)).offset(skip).limit(limit).all()
    
        documents = [
            Document(
                id=doc.id, 
                invoice_type=doc.invoice_type, 
                amount=doc.amount, 
                status=doc.status, 
                created_at=doc.created_at, 
                metadata_doc=doc.metadata_doc
            ) for doc in db_docs
        ]
        
        return documents, total