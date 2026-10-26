from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.models.database import Documents, EmbeddingStatus
from src.models.document_schemas import AddDocument


def to_uuid(val: Union[UUID, str, None]) -> Optional[UUID]:
    if not val:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None


class DocumentService:
    async def get_document_by_id(
        self, id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Documents]:
        doc_uuid = to_uuid(id)
        if not doc_uuid:
            return None
        result = await session.execute(select(Documents).where(Documents.uid == doc_uuid))
        return result.scalar_one_or_none()

    async def get_documents_by_business_id(
        self,
        business_id: Union[UUID, str],
        session: AsyncSession,
        **kwargs,
    ) -> List[Documents]:
        b_uuid = to_uuid(business_id or kwargs.get("buisness_id"))
        if not b_uuid:
            return []
        result = await session.execute(
            select(Documents).where(Documents.business_id == b_uuid)
        )
        return list(result.scalars().all())

    # Backwards compatibility and intuitive aliases
    get_documents_by_business = get_documents_by_business_id

    async def get_documents_by_uploader(
        self, uploader_id: Union[UUID, str], session: AsyncSession
    ) -> List[Documents]:
        u_uuid = to_uuid(uploader_id)
        if not u_uuid:
            return []
        result = await session.execute(
            select(Documents).where(Documents.uploaded_by == u_uuid)
        )
        return list(result.scalars().all())

    async def add_document(
        self,
        document: AddDocument,
        user_id: Union[UUID, str],
        business_id: Union[UUID, str],
        session: AsyncSession,
        **kwargs,
    ) -> Documents:
        doc_data = document or kwargs.get("documents")
        b_uuid = to_uuid(business_id or kwargs.get("buisness_id"))
        u_uuid = to_uuid(user_id)

        serialized_chunks = None
        if doc_data and doc_data.document_chunks:
            serialized_chunks = [
                chunk.model_dump()
                if hasattr(chunk, "model_dump")
                else chunk
                if isinstance(chunk, dict)
                else {"page_content": str(chunk), "metadata": {}}
                for chunk in doc_data.document_chunks
            ]

        new_document = Documents(
            business_id=b_uuid,
            uploaded_by=u_uuid,
            original_filename=doc_data.original_filename if doc_data else "",
            document_chunks=serialized_chunks,
            file_type=doc_data.file_type if doc_data else "pdf",
            extracted_text=doc_data.extracted_text if doc_data else None,
            embedding_status=doc_data.embedding_status if doc_data else EmbeddingStatus.pending,
        )
        session.add(new_document)
        await session.commit()
        await session.refresh(new_document)
        return new_document

    async def delete_document(
        self,
        document_id: Union[UUID, str],
        session: AsyncSession,
        **kwargs,
    ) -> Optional[Documents]:
        doc_uuid = to_uuid(document_id or kwargs.get("Documents_id"))
        doc = await self.get_document_by_id(doc_uuid, session)
        if doc:
            await session.delete(doc)
            await session.commit()
        return doc

    async def update_embedding_status(
        self,
        document_id: Union[UUID, str],
        status: EmbeddingStatus,
        session: AsyncSession,
        **kwargs,
    ) -> Optional[Documents]:
        doc_uuid = to_uuid(document_id or kwargs.get("Documents_id"))
        doc = await self.get_document_by_id(id=doc_uuid, session=session)
        if not doc:
            return None

        doc.embedding_status = status
        await session.commit()
        await session.refresh(doc)
        return doc


# Class and instance aliases
DocumentsService = DocumentService
document_service = DocumentService()
