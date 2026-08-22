from enum import Enum

from pydantic import BaseModel


class EmbeddingStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AddDocument(BaseModel):
    original_filename: str
    file_type: str
    extracted_text: str
    embedding_status: EmbeddingStatus
