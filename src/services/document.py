from typing import Optional

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.models.database import Document
from src.models.document_schemas import AddDocument


class DocumentService:
    async def get_documeny_by_id(
        self, id: str, session: AsyncSession
    ) -> Optional[Document]:
        data = select(Document).where(Document.uid == id)
        result = await session.execute(data)
        return result.scalar_one_or_none()

    async def get_document_by_buisness_id(
        self, buisness_id: str, session: AsyncSession
    ) -> Optional[Document]:
        data = select(Document).where(Document.business_id == buisness_id)
        result = await session.execute(data)
        return result.scalar_one_or_none()

    async def get_document_by_uploader(
        self, uploader_id: str, session: AsyncSession
    ) -> Optional[Document]:
        data = select(Document).where(Document.uploaded_by == uploader_id)
        result = await session.execute(data)
        return result.scalar_one_or_none()

    async def add_document(
        self,
        document: AddDocument,
        user_id: str,
        buisness_id: str,
        session: AsyncSession,
    ) -> Document:
        new_document = Document(
            buisness_id=buisness_id,
            uploaded_by=user_id,
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
        self, document_id: str, session: AsyncSession
    ) -> Optional[Document]:
        document = await self.get_documeny_by_id(document_id, session)
        if document:
            await session.delete(document)
            await session.commit()
        return document
