from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.models.database import Documents, EmbeddingStatus
from src.models.document_schemas import AddDocument, AddDocuments


def to_uuid(val: Union[UUID, str]) -> Optional[UUID]:
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None


class DocumentsService:
    async def get_document_by_id(
        self, id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Documents]:
        doc_uuid = to_uuid(id)
        if not doc_uuid:
            return None
        data = select(Documents).where(Documents.uid == doc_uuid)
        result = await session.execute(data)
        return result.scalar_one_or_none()

    # Backwards compatibility aliases
    get_Documents_by_id = get_document_by_id
    get_documeny_by_id = get_document_by_id

    async def get_documents_by_business_id(
        self,
        business_id: Optional[Union[UUID, str]] = None,
        session: Optional[AsyncSession] = None,
        buisness_id: Optional[Union[UUID, str]] = None,
    ) -> List[Documents]:
        b_id = business_id if business_id is not None else buisness_id
        b_uuid = to_uuid(b_id)
        if not b_uuid:
            return []
        data = select(Documents).where(Documents.business_id == b_uuid)
        result = await session.execute(data)
        return list(result.scalars().all())

    # Backwards compatibility aliases
    get_Documentss_by_business_id = get_documents_by_business_id
    get_Documents_by_buisness_id = get_documents_by_business_id

    async def get_documents_by_uploader(
        self, uploader_id: Union[UUID, str], session: AsyncSession
    ) -> List[Documents]:
        u_uuid = to_uuid(uploader_id)
        if not u_uuid:
            return []
        data = select(Documents).where(Documents.uploaded_by == u_uuid)
        result = await session.execute(data)
        return list(result.scalars().all())

    # Backwards compatibility aliases
    get_Documentss_by_uploader = get_documents_by_uploader
    get_Documents_by_uploader = get_documents_by_uploader

    async def add_document(
        self,
        document: Optional[AddDocument] = None,
        documents: Optional[AddDocument] = None,
        user_id: Optional[Union[UUID, str]] = None,
        buisness_id: Optional[Union[UUID, str]] = None,
        business_id: Optional[Union[UUID, str]] = None,
        session: Optional[AsyncSession] = None,
    ) -> Documents:
        doc_data = document if document is not None else documents
        b_id = business_id if business_id is not None else buisness_id
        b_uuid = to_uuid(b_id)
        u_uuid = to_uuid(user_id)

        # Serialize document chunks to list of dicts for JSONB storage
        serialized_chunks = None
        if doc_data and doc_data.document_chunks:
            serialized_chunks = []
            for chunk in doc_data.document_chunks:
                if hasattr(chunk, "model_dump"):
                    serialized_chunks.append(chunk.model_dump())
                elif hasattr(chunk, "dict"):
                    serialized_chunks.append(chunk.dict())
                elif isinstance(chunk, dict):
                    serialized_chunks.append(chunk)
                else:
                    serialized_chunks.append({"page_content": str(chunk), "metadata": {}})

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

    # Backwards compatibility alias
    add_Documents = add_document

    async def delete_document(
        self, document_id: Union[UUID, str], session: AsyncSession, Documents_id: Optional[Union[UUID, str]] = None
    ) -> Optional[Documents]:
        target_id = document_id if document_id is not None else Documents_id
        doc = await self.get_document_by_id(target_id, session)
        if doc:
            await session.delete(doc)
            await session.commit()
        return doc

    # Backwards compatibility alias
    delete_Documents = delete_document

    async def update_embedding_status(
        self,
        document_id: Optional[Union[UUID, str]] = None,
        status: EmbeddingStatus = EmbeddingStatus.pending,
        session: Optional[AsyncSession] = None,
        Documents_id: Optional[Union[UUID, str]] = None,
    ) -> Optional[Documents]:
        target_id = document_id if document_id is not None else Documents_id
        doc = await self.get_document_by_id(
            id=target_id,
            session=session,
        )

        if not doc:
            return None

        doc.embedding_status = status

        await session.commit()
        await session.refresh(doc)

        return doc


# Class and instance aliases
DocumentService = DocumentsService
document_service = DocumentsService()
