from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.models.database import Document
from src.models.document_schemas import AddDocument


def to_uuid(val: Union[UUID, str]) -> Optional[UUID]:
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None


class DocumentService:
    async def get_document_by_id(
        self, id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Document]:
        doc_uuid = to_uuid(id)
        if not doc_uuid:
            return None
        data = select(Document).where(Document.uid == doc_uuid)
        result = await session.execute(data)
        return result.scalar_one_or_none()

    # Backwards compatibility alias
    get_documeny_by_id = get_document_by_id

    async def get_documents_by_business_id(
        self, buisness_id: Union[UUID, str], session: AsyncSession
    ) -> List[Document]:
        b_uuid = to_uuid(buisness_id)
        if not b_uuid:
            return []
        data = select(Document).where(Document.business_id == b_uuid)
        result = await session.execute(data)
        return list(result.scalars().all())

    # Backwards compatibility alias
    get_document_by_buisness_id = get_documents_by_business_id

    async def get_documents_by_uploader(
        self, uploader_id: Union[UUID, str], session: AsyncSession
    ) -> List[Document]:
        u_uuid = to_uuid(uploader_id)
        if not u_uuid:
            return []
        data = select(Document).where(Document.uploaded_by == u_uuid)
        result = await session.execute(data)
        return list(result.scalars().all())

    # Backwards compatibility alias
    get_document_by_uploader = get_documents_by_uploader

    async def add_document(
        self,
        document: AddDocument,
        user_id: Union[UUID, str],
        buisness_id: Optional[Union[UUID, str]] = None,
        business_id: Optional[Union[UUID, str]] = None,
        session: Optional[AsyncSession] = None,
    ) -> Document:
        b_id = business_id if business_id is not None else buisness_id
        b_uuid = to_uuid(b_id)
        u_uuid = to_uuid(user_id)

        new_document = Document(
            business_id=b_uuid,
            uploaded_by=u_uuid,
            original_filename=document.original_filename,
            file_type=document.file_type,
            extracted_text=document.extracted_text,
            embedding_status=document.embedding_status,
        )
        session.add(new_document)
        await session.commit()
        await session.refresh(new_document)
        return new_document

    async def delete_document(
        self, document_id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Document]:
        document = await self.get_document_by_id(document_id, session)
        if document:
            await session.delete(document)
            await session.commit()
        return document
