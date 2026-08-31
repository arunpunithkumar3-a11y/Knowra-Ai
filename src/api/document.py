import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependency import verify_token
from src.core.main import get_session
from src.knowra.retrievers import retriever
from src.models.document_schemas import AddDocument, EmbeddingStatus
from src.services.business import BusinessService
from src.services.document import DocumentService
from src.tasks.document_tasks import process_document

document_router = APIRouter()
document_service = DocumentService()
business_service = BusinessService()
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=200)

MAX_PDF_PAGES = 10


def _parse_uuid(value: str, field_name: str = "ID") -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format",
        )


@document_router.get("/document/{document_id}")
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    u_uuid = _parse_uuid(user_id, "user ID")
    doc_uuid = _parse_uuid(document_id, "document ID")
    document = await document_service.get_document_by_id(id=doc_uuid, session=session)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Verify ownership
    business = await business_service.get_business_by_id(
        business_id=document.business_id, session=session
    )
    if not business or (business.owner_id != u_uuid and document.uploaded_by != u_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this document",
        )
    return document


@document_router.get("/all_document")
async def get_document_by_user(
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    u_uuid = _parse_uuid(user_id, "user ID")
    all_document = await document_service.get_documents_by_uploader(
        uploader_id=u_uuid, session=session
    )
    return all_document


@document_router.get("/business_document/{business_id}")
async def get_document_by_business(
    business_id: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    u_uuid = _parse_uuid(user_id, "user ID")
    b_uuid = _parse_uuid(business_id, "business ID")

    business = await business_service.get_business_by_id(
        business_id=b_uuid, session=session
    )
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )
    if business.owner_id != u_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this business's documents",
        )

    documents = await document_service.get_documents_by_business_id(
        business_id=b_uuid, session=session
    )
    return documents


@document_router.post(
    "/create_document/{business_id}", status_code=status.HTTP_201_CREATED
)
async def create_document(
    business_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    u_uuid = _parse_uuid(user_id, "user ID")
    b_uuid = _parse_uuid(business_id, "business ID")

    # Verify that the business exists and belongs to current user
    business = await business_service.get_business_by_id(
        business_id=b_uuid, session=session
    )
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )
    if business.owner_id != u_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload documents to this business",
        )

    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDFs are allowed.",
        )

    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )
        if not contents.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file structure",
            )
        pdf_stream = io.BytesIO(contents)
        reader = PdfReader(pdf_stream)
        num_pages = len(reader.pages)
        if num_pages == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF contains no pages",
            )
        if num_pages > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF exceeds the maximum limit of {MAX_PDF_PAGES} pages (uploaded PDF has {num_pages} pages)",
            )
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process PDF file: {str(e)}",
        )
    splitted_docs = splitter.create_documents([extracted_text])
    data = AddDocument(
        original_filename=file.filename,
        file_type="pdf",
        document_chunks=splitted_docs,
        extracted_text=extracted_text,
        embedding_status=EmbeddingStatus.pending,
    )
    new_document = await document_service.add_document(
        document=data, user_id=u_uuid, business_id=b_uuid, session=session
    )
    process_document.delay(
        document_id=str(new_document.uid),
        business_id=str(b_uuid),
    )
    return JSONResponse(
        content={
            "message": "Document created successfully",
            "document_id": str(new_document.uid),
        },
        status_code=status.HTTP_201_CREATED,
    )


@document_router.delete("/delete_document/{document_id}")
async def deleted_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    u_uuid = _parse_uuid(user_id, "user ID")
    doc_uuid = _parse_uuid(document_id, "document ID")

    existing_doc = await document_service.get_document_by_id(
        id=doc_uuid, session=session
    )
    if not existing_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    business = await business_service.get_business_by_id(
        business_id=existing_doc.business_id, session=session
    )
    if not business or (business.owner_id != u_uuid and existing_doc.uploaded_by != u_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this document",
        )

    document = await document_service.delete_document(
        document_id=doc_uuid, session=session
    )

    # Clean up vector database points
    retriever.delete_document_vectors(
        business_id=existing_doc.business_id,
        document_id=existing_doc.uid,
    )

    return {"message": "Document deleted successfully", "document_id": str(doc_uuid)}
