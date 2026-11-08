import logging

from langchain_core.documents import Document

from src.core.main import async_session_maker
from src.knowra.retrievers import get_retriever
from src.mail import body, create_message, send_mail
from src.models.database import EmbeddingStatus
from src.services.document import document_service

logger = logging.getLogger("knowra.tasks")


async def process_document(document_id: str, business_id: str):
    """Processes uploaded document text, generates embeddings, and updates status."""
    async with async_session_maker() as session:
        document = await document_service.get_document_by_id(
            id=document_id,
            session=session,
        )

        if not document:
            logger.error(f"Document {document_id} not found")
            return

        if str(document.business_id) != str(business_id):
            logger.error(
                f"Document {document_id} does not belong to business {business_id}"
            )
            return

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

            retriever = get_retriever()
            parents, children = await retriever.add_documents(
                docs=rag_document,
                business_id=document.business_id,
                document_id=document.uid,
            )

            await document_service.update_embedding_status(
                document_id=document.uid,
                status=EmbeddingStatus.completed,
                session=session,
            )

            # Invalidate BM25 cache so new document is immediately retrievable

            logger.info(
                f"Successfully indexed document {document.uid}: "
                f"{len(parents)} parents, {len(children)} children"
            )

        except Exception as exc:
            logger.error(f"Failed to process document {document_id}: {exc}")
            try:
                await document_service.update_embedding_status(
                    document_id=document.uid,
                    status=EmbeddingStatus.failed,
                    session=session,
                )
            except Exception:
                pass


async def send_welcome_message(email: str):
    """Sends a welcome email to newly registered user."""
    try:
        message = create_message(
            recipients=[email], subject="Welcome to Knowra", body=body
        )
        await send_mail.send_message(message)
        logger.info(f"Welcome email successfully sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")


async def send_password_reset_link(email: str, _body: str):
    """Sends a password reset email."""
    try:
        message = create_message(
            recipients=[email], subject="Reset Your Password", body=_body
        )
        await send_mail.send_message(message)
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")


# Provide .delay attribute for backward-compatibility with unit test mocks
process_document.delay = lambda *args, **kwargs: None
send_welcome_message.delay = lambda *args, **kwargs: None
send_password_reset_link.delay = lambda *args, **kwargs: None
