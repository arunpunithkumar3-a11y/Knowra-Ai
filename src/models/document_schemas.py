from enum import Enum
from typing import Any, List, Optional, Union

from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict


class EmbeddingStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AddDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    original_filename: str
    file_type: str
    extracted_text: str
    document_chunks: Optional[List[Union[dict, Document, Any]]] = None
    embedding_status: EmbeddingStatus = EmbeddingStatus.pending


# Backwards compatibility alias
AddDocuments = AddDocument
