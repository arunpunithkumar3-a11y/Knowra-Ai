from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models.database import EmbeddingStatus
from src.services.document import DocumentService


@pytest.fixture
def service():
    return DocumentService()


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def document():
    return MagicMock(
        uid=uuid4(),
        business_id=uuid4(),
        uploaded_by=uuid4(),
        original_filename="sample.pdf",
        file_type="pdf",
        extracted_text="Sample text content",
        document_chunks=[],
        embedding_status=EmbeddingStatus.pending,
    )


@pytest.mark.asyncio
async def test_get_document_by_id_found(service, session, document):
    result = MagicMock()
    result.scalar_one_or_none.return_value = document
    session.execute.return_value = result

    found = await service.get_document_by_id(document.uid, session)

    assert found is document
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_document_by_id_string_uuid(service, session, document):
    result = MagicMock()
    result.scalar_one_or_none.return_value = document
    session.execute.return_value = result

    found = await service.get_document_by_id(str(document.uid), session)

    assert found is document
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_document_by_id_invalid_uuid(service, session):
    found = await service.get_document_by_id("invalid-uuid", session)

    assert found is None
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_document_by_id_not_found(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found = await service.get_document_by_id(uuid4(), session)

    assert found is None


@pytest.mark.asyncio
async def test_get_documents_by_business_id_found(service, session, document):
    b_id = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [document]
    session.execute.return_value = result

    documents = await service.get_documents_by_business_id(b_id, session)

    assert len(documents) == 1
    assert documents[0] is document


@pytest.mark.asyncio
async def test_get_documents_by_business_id_invalid(service, session):
    documents = await service.get_documents_by_business_id("invalid-uuid", session)

    assert documents == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_documents_by_uploader_found(service, session, document):
    u_id = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [document]
    session.execute.return_value = result

    documents = await service.get_documents_by_uploader(u_id, session)

    assert len(documents) == 1
    assert documents[0] is document


@pytest.mark.asyncio
async def test_get_documents_by_uploader_invalid(service, session):
    documents = await service.get_documents_by_uploader("invalid-uuid", session)

    assert documents == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_document_with_chunks(service, session):
    user_id = uuid4()
    business_id = uuid4()
    chunk_mock = MagicMock()
    chunk_mock.model_dump.return_value = {"page_content": "part 1", "metadata": {}}

    doc_data = MagicMock()
    doc_data.original_filename = "doc.pdf"
    doc_data.file_type = "pdf"
    doc_data.extracted_text = "full text"
    doc_data.embedding_status = EmbeddingStatus.pending
    doc_data.document_chunks = [chunk_mock]

    new_doc = await service.add_document(doc_data, user_id, business_id, session)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(new_doc)
    assert new_doc.original_filename == "doc.pdf"
    assert new_doc.document_chunks == [{"page_content": "part 1", "metadata": {}}]


@pytest.mark.asyncio
async def test_add_document_without_chunks(service, session):
    user_id = uuid4()
    business_id = uuid4()

    doc_data = MagicMock()
    doc_data.original_filename = "notes.txt"
    doc_data.file_type = "txt"
    doc_data.extracted_text = "plain notes"
    doc_data.embedding_status = EmbeddingStatus.pending
    doc_data.document_chunks = None

    new_doc = await service.add_document(doc_data, user_id, business_id, session)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    assert new_doc.document_chunks is None


@pytest.mark.asyncio
async def test_delete_document_found(service, session, document):
    service.get_document_by_id = AsyncMock(return_value=document)

    deleted = await service.delete_document(document.uid, session)

    assert deleted is document
    session.delete.assert_awaited_once_with(document)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_document_not_found(service, session):
    service.get_document_by_id = AsyncMock(return_value=None)

    deleted = await service.delete_document(uuid4(), session)

    assert deleted is None
    session.delete.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_embedding_status_found(service, session, document):
    service.get_document_by_id = AsyncMock(return_value=document)

    updated = await service.update_embedding_status(
        document.uid, EmbeddingStatus.completed, session
    )

    assert updated is document
    assert document.embedding_status == EmbeddingStatus.completed
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(document)


@pytest.mark.asyncio
async def test_update_embedding_status_not_found(service, session):
    service.get_document_by_id = AsyncMock(return_value=None)

    updated = await service.update_embedding_status(
        uuid4(), EmbeddingStatus.failed, session
    )

    assert updated is None
    session.commit.assert_not_awaited()
