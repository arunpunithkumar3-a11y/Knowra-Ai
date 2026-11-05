from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.feature import get_cluster_feature, get_total_questions
from src.exceptions import AuthenticationError, ValidationError


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


@pytest.mark.asyncio
async def test_get_total_questions_success(session, token_details):
    b_id = uuid4()
    with patch("src.api.feature.question_service.get_total_question_by_business_id", new=AsyncMock(return_value=15)):
        res = await get_total_questions(str(b_id), session, token_details)

    assert res == {"message": 15, "total_questions": 15}


@pytest.mark.asyncio
async def test_get_total_questions_unauthenticated(session):
    with pytest.raises(AuthenticationError):
        await get_total_questions(str(uuid4()), session, {})


@pytest.mark.asyncio
async def test_get_total_questions_invalid_uuid(session, token_details):
    with pytest.raises(ValidationError):
        await get_total_questions("bad-uuid", session, token_details)


@pytest.mark.asyncio
async def test_get_cluster_feature_zero_questions(session, token_details):
    b_id = uuid4()
    with patch("src.api.feature.question_service.get_total_question_by_business_id", new=AsyncMock(return_value=0)):
        with pytest.raises(ValidationError):
            await get_cluster_feature(str(b_id), 1, 10, session, token_details)


@pytest.mark.asyncio
async def test_get_cluster_feature_invalid_range(session, token_details):
    b_id = uuid4()
    with patch("src.api.feature.question_service.get_total_question_by_business_id", new=AsyncMock(return_value=20)):
        with pytest.raises(ValidationError):
            await get_cluster_feature(str(b_id), 0, 10, session, token_details)

        with pytest.raises(ValidationError):
            await get_cluster_feature(str(b_id), 10, 5, session, token_details)

        with pytest.raises(ValidationError):
            await get_cluster_feature(str(b_id), 1, 105, session, token_details)

        with pytest.raises(ValidationError):
            await get_cluster_feature(str(b_id), 1, 25, session, token_details)


@pytest.mark.asyncio
async def test_get_cluster_feature_success(session, token_details):
    b_id = uuid4()
    q_mock = MagicMock(question_text="How to cancel?")

    with patch("src.api.feature.question_service.get_total_question_by_business_id", new=AsyncMock(return_value=10)), \
         patch("src.api.feature.question_service.get_questions_by_range", new=AsyncMock(return_value=[q_mock])), \
         patch("src.api.feature.analyse", new=AsyncMock(return_value=[{"topic": "Cancellation"}])):
        res = await get_cluster_feature(str(b_id), 1, 5, session, token_details)

    assert "message" in res
