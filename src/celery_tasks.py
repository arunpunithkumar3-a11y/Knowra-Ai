import asyncio

from celery import Celery
from langchain_core.documents import Document

from src.config import configure
from src.core.main import async_session_maker
from src.knowra.retrievers import retriever
from src.mail import body, create_message, send_mail
from src.models.database import EmbeddingStatus
from src.services.document import document_service

celery_app = Celery(
    "knowra",
    broker=configure.REDIS_URL,
    backend=configure.REDIS_URL,
)


async def _process_document(
    document_id: str,
    business_id: str,
):
    async with async_session_maker() as session:
        document = await document_service.get_document_by_id(
            id=document_id,
            session=session,
        )

        if not document:
            raise ValueError(f"Document {document_id} not found")

        if str(document.business_id) != str(business_id):
            raise ValueError("Document does not belong to this business")

        await document_service.update_embedding_status(
            document_id=document.uid,
            status=EmbeddingStatus.processing,
            session=session,
        )

        try:
            if not document.extracted_text:
                raise ValueError(f"Document {document.uid} contains no extracted text")

            rag_document = Document(
                page_content=document.extracted_text,
                metadata={
                    "business_id": str(document.business_id),
                    "document_id": str(document.uid),
                    "source": document.original_filename,
                },
            )

            parents, children = retriever.add_documents(
                docs=rag_document,
                business_id=document.business_id,
                document_id=document.uid,
            )

            await document_service.update_embedding_status(
                document_id=document.uid,
                status=EmbeddingStatus.completed,
                session=session,
            )

            print(
                f"Successfully indexed document "
                f"{document.uid}: "
                f"{len(parents)} parents, "
                f"{len(children)} children"
            )

        except Exception:
            raise


@celery_app.task(
    bind=True,
    name="process_document",
    # Retry configuration
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    # Reliability
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document(
    self,
    document_id: str,
    business_id: str,
):
    """
    Celery entry point for document ingestion.

    Flow:

        pending
           ↓
        processing
           ↓
        RAG ingestion
           ↓
        completed

    If ingestion fails:

        processing
           ↓
        Celery retry
           ↓
        processing
           ↓
        ...

    After all retries fail, the task is considered failed.
    """

    try:
        asyncio.run(
            _process_document(
                document_id=document_id,
                business_id=business_id,
            )
        )

    except Exception as exc:
        if self.request.retries >= self.max_retries:

            async def mark_failed():

                async with async_session_maker() as session:
                    document = await document_service.get_document_by_id(
                        id=document_id,
                        session=session,
                    )

                    if document:
                        await document_service.update_embedding_status(
                            document_id=document.uid,
                            status=EmbeddingStatus.failed,
                            session=session,
                        )

            asyncio.run(mark_failed())

        raise exc


async def _send_welcome_message(email: str):
    message = create_message(recipents=[email], subject="Welcome to Knowra", body=body)
    await send_mail(message)


@celery_app.task(
    bind=True,
    name="send_welcome_message",
    # Retry configuration
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    # Reliability
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_welcome_message(self,email: str):
    """
    Celery entry point for sending welcome email.

    This task is not critical, so we don't retry on failure.
    """

    asyncio.run(_send_welcome_message(email=email))
