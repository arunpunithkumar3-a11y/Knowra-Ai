from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.questions import QuestionService


@pytest.fixture
def service():
    return QuestionService()


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def question():
    return MagicMock(
        uid=uuid4(),
        question_text="What are your operating hours?",
        business_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_get_questions_by_business_id_found(service, session, question):
    b_id = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [question]
    session.execute.return_value = result

    questions = await service.get_questions_by_business_id(session, b_id)

    assert len(questions) == 1
    assert questions[0] is question
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_questions_by_business_id_invalid(service, session):
    questions = await service.get_questions_by_business_id(session, "invalid-uuid")

    assert questions == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_questions_success(service, session):
    b_id = uuid4()

    created = await service.add_questions("How do I return an item?", session, b_id)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created)
    assert created.question_text == "How do I return an item?"
    assert created.business_id == b_id


@pytest.mark.asyncio
async def test_add_questions_empty_text(service, session):
    created = await service.add_questions("   ", session, uuid4())

    assert created is None
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_add_questions_invalid_business_id(service, session):
    created = await service.add_questions("Valid text?", session, "invalid-uuid")

    assert created is None
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_questions_by_range_found(service, session, question):
    b_id = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [question]
    session.execute.return_value = result

    questions = await service.get_questions_by_range(session, b_id, start=0, end=5)

    assert len(questions) == 1
    assert questions[0] is question
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_questions_by_range_invalid_id(service, session):
    questions = await service.get_questions_by_range(session, "invalid-uuid", start=0, end=5)

    assert questions == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_total_question_by_business_id_found(service, session):
    b_id = uuid4()
    result = MagicMock()
    result.scalar.return_value = 42
    session.execute.return_value = result

    count = await service.get_total_question_by_business_id(session, b_id)

    assert count == 42
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_total_question_by_business_id_invalid(service, session):
    count = await service.get_total_question_by_business_id(session, "invalid-uuid")

    assert count == 0
    session.execute.assert_not_awaited()
