from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=1000,
    )
    thread_id: str = Field(
        min_length=1,
        max_length=255,
    )


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
