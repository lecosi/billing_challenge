from fastapi import Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.repository import DocumentRepository, JobRepository
from app.application.use_cases import DocumentUseCase, BatchJobUseCase

def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)

def get_job_repository(db: Session = Depends(get_db)) -> JobRepository:
    return JobRepository(db)

def get_document_use_case(repo: DocumentRepository = Depends(get_document_repository)) -> DocumentUseCase:
    return DocumentUseCase(repo)

def get_batch_job_use_case(
    job_repo: JobRepository = Depends(get_job_repository),
    doc_repo: DocumentRepository = Depends(get_document_repository)
) -> BatchJobUseCase:
    return BatchJobUseCase(job_repo, doc_repo)