from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.models.database import Document
from src.models.document_schemas import AddDocument


class DocumentService:
    async def get_documeny_by_id(self, id: str, session: AsyncSession) -> Optional[Document]:
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
        self, document: AddDocument, session: AsyncSession
    ) -> Document:
        data = document.model_dump(exclude_unset=True)
        new_document = Document(**data)
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
