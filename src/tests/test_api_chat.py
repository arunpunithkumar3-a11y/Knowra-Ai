from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.chat import chat, clear_chat_history, get_chat_history, widget_chat
from src.exceptions import AuthorizationError, NotFoundError
from src.models.chat_schemas import ChatRequest


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
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
        business_name="Chat Business",
        description="Business for chatbot tests",
        public_key="pk_chatbiz",
    )


@pytest.mark.asyncio
async def test_chat_business_not_found(session, token_details):
    data = ChatRequest(message="Hello", thread_id="t1")
    with patch("src.api.chat.business_service.get_business_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await chat(str(uuid4()), data, token_details, session)


@pytest.mark.asyncio
async def test_chat_unauthorized(session, token_details, business):
    business.owner_id = uuid4()
    data = ChatRequest(message="Hello", thread_id="t1")
    with patch("src.api.chat.business_service.get_business_by_id", new=AsyncMock(return_value=business)):
        with pytest.raises(AuthorizationError):
            await chat(str(business.uid), data, token_details, session)


@pytest.mark.asyncio
async def test_chat_success(session, token_details, business):
    data = ChatRequest(message="Hello", thread_id="t1")
    with patch("src.api.chat.business_service.get_business_by_id", new=AsyncMock(return_value=business)), \
         patch("src.api.chat.classifier.predict", return_value=["no"]), \
         patch("src.api.chat.stream_chat", return_value=AsyncMock()):
        response = await chat(str(business.uid), data, token_details, session)

    assert response.status_code == 200
    assert response.media_type == "text/event-stream"


@pytest.mark.asyncio
async def test_widget_chat_not_found(session):
    data = ChatRequest(message="Hello", thread_id="t1")
    with patch("src.api.chat.business_service.get_business_by_public_key", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await widget_chat("invalid_key", data, session)


@pytest.mark.asyncio
async def test_widget_chat_success(session, business):
    data = ChatRequest(message="Hello", thread_id="t1")
    with patch("src.api.chat.business_service.get_business_by_public_key", new=AsyncMock(return_value=business)), \
         patch("src.api.chat.classifier.predict", return_value=["no"]), \
         patch("src.api.chat.stream_chat", return_value=AsyncMock()):
        response = await widget_chat("pk_chatbiz", data, session)

    assert response.status_code == 200
    assert response.media_type == "text/event-stream"


@pytest.mark.asyncio
async def test_get_chat_history_empty():
    with patch("src.knowra.agent.graph.get_compiled_graph", new=AsyncMock(side_effect=Exception("no graph"))):
        res = await get_chat_history("t123")

    assert res["thread_id"] == "t123"
    assert res["total_messages"] == 0
    assert res["messages"] == []


@pytest.mark.asyncio
async def test_clear_chat_history_success():
    mock_checkpointer = MagicMock()
    mock_checkpointer.adelete_thread = AsyncMock()

    with patch("src.core.postgres.get_checkpointer", new=AsyncMock(return_value=mock_checkpointer)):
        res = await clear_chat_history("t123")

    assert res["status"] == "success"
    mock_checkpointer.adelete_thread.assert_awaited_once_with("t123")
