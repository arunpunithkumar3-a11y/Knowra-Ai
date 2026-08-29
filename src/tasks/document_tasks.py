import asyncio

from celery import Celery
from langchain_core.documents import Document

from src.knowra.retrievers import retriever
from src.config import configure
from src.core.main import get_session
from src.models.database import EmbeddingStatus
from src.services.document import document_service

# ============================================================
# RAG RETRIEVER
# ============================================================


# ============================================================
# SERVICES
# ============================================================


# ============================================================
# CELERY
# ============================================================

celery_app = Celery(
    "knowra",
    broker=configure.REDIS_URL,
    backend=configure.REDIS_URL,
)


# ============================================================
# DOCUMENT PROCESSING
# ============================================================


async def _process_document(
    document_id: str,
    business_id: str,
):
    async with get_session() as session:
        # ----------------------------------------------------
        # Fetch document
        # ----------------------------------------------------

        document = await document_service.get_document_by_id(
            id=document_id,
            session=session,
        )

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # ----------------------------------------------------
        # Tenant validation
        # ----------------------------------------------------

        if str(document.business_id) != str(business_id):
            raise ValueError("Document does not belong to this business")

        # ----------------------------------------------------
        # Mark as processing
        # ----------------------------------------------------

        await document_service.update_embedding_status(
            document_id=document.uid,
            status=EmbeddingStatus.processing,
            session=session,
        )

        try:
            # ------------------------------------------------
            # Validate extracted text
            # ------------------------------------------------

            if not document.extracted_text:
                raise ValueError(f"Document {document.uid} contains no extracted text")

            # ------------------------------------------------
            # Convert database document → LangChain document
            # ------------------------------------------------

            rag_document = Document(
                page_content=document.extracted_text,
                metadata={
                    "business_id": str(document.business_id),
                    "document_id": str(document.uid),
                    "source": document.original_filename,
                },
            )

            # ------------------------------------------------
            # Parent-child + sentence-window ingestion
            # ------------------------------------------------

            parents, children = retriever.add_documents(
                docs=rag_document,
                business_id=document.business_id,
                document_id=document.uid,
            )

            # ------------------------------------------------
            # Mark completed
            # ------------------------------------------------

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
            # IMPORTANT:
            #
            # We DON'T mark the document as failed here.
            #
            # Celery may retry this task.
            # The document should remain "processing"
            # while retries are happening.
            #
            raise


# ============================================================
# CELERY TASK
# ============================================================


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
        # ----------------------------------------------------
        # Check whether Celery still has retries available
        # ----------------------------------------------------

        if self.request.retries >= self.max_retries:
            # All retries exhausted.
            #
            # We need a NEW database session here because
            # the session used inside _process_document()
            # has already been closed.

            async def mark_failed():

                async with get_session() as session:
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

        # Re-raise so Celery knows the task failed
        # and performs its retry logic.
        raise exc
