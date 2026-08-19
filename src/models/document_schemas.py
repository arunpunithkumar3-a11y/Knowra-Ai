from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AddDocument(BaseModel):
    business_id: UUID
    uploaded_by: Optional[UUID] = None
    original_filename: str
    file_type: str
    extracted_text: Optional[str] = None
