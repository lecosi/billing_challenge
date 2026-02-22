import time
import random
from app.infrastructure.celery_config import celery_app
from app.infrastructure.database import SessionLocal
from app.infrastructure.repository import DocumentRepository, JobRepository

@celery_app.task(name="process_documents_task")
def process_documents_task(job_id: str):
    db = SessionLocal()
    job_repo = JobRepository(db)
    doc_repo = DocumentRepository(db)

    try:
        job = job_repo.get_by_id(job_id)
        if not job:
            return
            
        job.start_processing()
        job_repo.save(job)

        sleep_time = random.uniform(5, 10)
        time.sleep(sleep_time) # its only for requirements in challenge

        # TODO (so that we can see approved and rejected items in the test).
        for doc_id in job.document_ids:
            doc = doc_repo.get_by_id(doc_id)
            if doc:
                # We simulate business logic: 80% are approved, 20% are rejected.
                if random.random() > 0.2:
                    doc.approve()  # PENDING -> APPROVED
                else:
                    doc.reject()   # PENDING -> REJECTED
                doc_repo.save(doc)

        job.mark_as_completed()
        job_repo.save(job)

    except Exception as e:
        if 'job' in locals() and job:
            job.mark_as_failed(str(e))
            job_repo.save(job)
    finally:
        db.close()