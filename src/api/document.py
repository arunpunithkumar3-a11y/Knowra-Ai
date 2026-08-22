import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependency import verify_token
from models.document_schemas import AddDocument, EmbeddingStatus
from services.document import DocumentService
from src.core.main import get_session

document_router = APIRouter()
document_service = DocumentService()


@document_router.get("/document{document_id}")
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):

    document = await document_service.get_documeny_by_id(
        document_id=document_id, session=session
    )
    return JSONResponse(content=document, status_code=status.HTTP_200_OK)


@document_router.get("/all_document{user_id}")
async def get_document_by_user(
    user_id: str,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):

    user_id = token_details["user_data"]["user_id"]
    all_document = await document_service.get_document_by_uploader(
        uploader_id=user_id, session=session
    )
    return JSONResponse(content=all_document, status_code=status.HTTP_200_OK)


@document_router.get("/buisness_document{buisness_id}")
async def get_document_by_buisness(
    buisness_id: str,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):
    document = await document_service.get_document_by_buisness_id(
        buisness_id=buisness_id, session=session
    )
    return JSONResponse(content=document, status_code=status.HTTP_200_OK)


@document_router.post("/create_document{buisness_id}")
async def create_document(
    buisness_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only PDFs are allowed."
        )

    contents = await file.read()
    pdf_stream = io.BytesIO(contents)
    reader = PdfReader(pdf_stream)
    extracted_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            extracted_text += text

    data = AddDocument(
        original_filename=file.filename,
        file_type="pdf",
        extracted_text=extracted_text,
        embedding_status=EmbeddingStatus.pending,
    )
    user_id = token_details["user_data"]["user_id"]
    new_document = await document_service.add_document(
        document=data, user_id=user_id, buisness_id=buisness_id, session=session
    )
    return JSONResponse(
        content={"message": new_document},
        status_code=status.HTTP_201_CREATED,
    )


@document_router("/delete_document{document_id}")
async def deleted_document(
    document_id: str,
    session: AsyncSession = Depends(get_session()),
    token_details=Depends(verify_token()),
):
    document = await document_service.delete_document(
        document_id=document_id, session=session
    )
    if not document:
        raise HTTPException(
            detail="document does not exist", status_code=status.HTTP_404_NOT_FOUND
        )

    return JSONResponse(content=document, status_code=status.HTTP_200_OK)
