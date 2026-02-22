from fastapi import Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.repository import DocumentRepository
from app.application.use_cases import DocumentUseCase

def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)

def get_document_use_case(repo: DocumentRepository = Depends(get_document_repository)) -> DocumentUseCase:
    return DocumentUseCase(repo)