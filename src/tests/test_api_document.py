from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.document import (
    deleted_document,
    get_document,
    get_document_by_business,
    get_document_by_user,
)
from src.exceptions import AuthorizationError, NotFoundError


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    return mock_session


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def token_details(user_id):
    return {"user_data": {"user_id": str(user_id)}}


@pytest.fixture
def business(user_id):
    return MagicMock(
        uid=uuid4(),
        owner_id=user_id,
        business_name="Test Corp",
    )


@pytest.fixture
def document(user_id, business):
    return MagicMock(
        uid=uuid4(),
        business_id=business.uid,
        uploaded_by=user_id,
        original_filename="manual.pdf",
    )


@pytest.mark.asyncio
async def test_get_document_success(session, token_details, business, document):
    with patch("src.api.document.document_service.get_document_by_id", new=AsyncMock(return_value=document)), \
         patch("src.api.document.business_service.get_business_by_id", new=AsyncMock(return_value=business)):
        res = await get_document(str(document.uid), session, token_details)

    assert res is document


@pytest.mark.asyncio
async def test_get_document_not_found(session, token_details):
    with patch("src.api.document.document_service.get_document_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await get_document(str(uuid4()), session, token_details)


@pytest.mark.asyncio
async def test_get_document_unauthorized(session, token_details, document):
    other_business = MagicMock(owner_id=uuid4())
    document.uploaded_by = uuid4()

    with patch("src.api.document.document_service.get_document_by_id", new=AsyncMock(return_value=document)), \
         patch("src.api.document.business_service.get_business_by_id", new=AsyncMock(return_value=other_business)):
        with pytest.raises(AuthorizationError):
            await get_document(str(document.uid), session, token_details)


@pytest.mark.asyncio
async def test_get_document_by_user(session, token_details, document):
    with patch("src.api.document.document_service.get_documents_by_uploader", new=AsyncMock(return_value=[document])):
        res = await get_document_by_user(session, token_details)

    assert res == [document]


@pytest.mark.asyncio
async def test_get_document_by_business_success(session, token_details, business, document):
    with patch("src.api.document.business_service.get_business_by_id", new=AsyncMock(return_value=business)), \
         patch("src.api.document.document_service.get_documents_by_business_id", new=AsyncMock(return_value=[document])):
        res = await get_document_by_business(str(business.uid), session, token_details)

    assert res == [document]


@pytest.mark.asyncio
async def test_get_document_by_business_not_found(session, token_details):
    with patch("src.api.document.business_service.get_business_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await get_document_by_business(str(uuid4()), session, token_details)


@pytest.mark.asyncio
async def test_deleted_document_success(session, token_details, business, document):
    with patch("src.api.document.document_service.get_document_by_id", new=AsyncMock(return_value=document)), \
         patch("src.api.document.business_service.get_business_by_id", new=AsyncMock(return_value=business)), \
         patch("src.api.document.document_service.delete_document", new=AsyncMock()), \
         patch("src.api.document.retriever.delete_document_vectors"):
        res = await deleted_document(str(document.uid), session, token_details)

    assert res["message"] == "Document deleted successfully"


@pytest.mark.asyncio
async def test_deleted_document_not_found(session, token_details):
    with patch("src.api.document.document_service.get_document_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await deleted_document(str(uuid4()), session, token_details)
