import logging
import uuid
from typing import List, Union

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from src.config import configure, reranker
from src.core.main import async_session_maker
from src.knowra.retrievers import retriever, rrf
from src.services.document import document_service

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Multi-Tenant Conversational RAG Pipeline:
    - Isolated Dense Sentence-Window Vector Search per tenant/business_id (Chroma + NVIDIA Embeddings)
    - Isolated Sparse Keyword Search per tenant/business_id (BM25 Retriever over windowed chunks)
    - Reciprocal Rank Fusion (RRF)
    - Cross-Encoder Reranking (NVIDIA Reranker)
    - Grounded Conversational Generation (NVIDIA Nemotron LLM)
    """

    def __init__(self, reranker):
        self.reranker = reranker

    async def retrieve_ranked_context(
        self,
        query: str,
        business_id: Union[str, uuid.UUID] = "default_business",
    ) -> List[Document]:
        """Retrieves and reranks relevant context strictly for the specified business_id."""
        biz_key = str(business_id)
        k_d = configure.DENSE_K
        k_s = configure.SPARSE_K
        top_n = configure.TOP_K_RERANK

        # Dense Sentence-Window Retrieval
        dense_docs = retriever.retrieve(query=query, business_id=biz_key, k=k_d)
        sparse_docs: List[Document] = []

        try:
            async with async_session_maker() as session:
                doc = await document_service.get_documents_by_business_id(
                    business_id=business_id, session=session
                )
            if doc:
                doc_list = doc if isinstance(doc, list) else [doc]
                lc_docs = []
                for d in doc_list:
                    if hasattr(d, "extracted_text") and d.extracted_text:
                        lc_docs.append(
                            Document(
                                page_content=d.extracted_text,
                                metadata={
                                    "source": getattr(
                                        d, "original_filename", "Knowledge Base"
                                    ),
                                    "business_id": biz_key,
                                },
                            )
                        )
                    elif isinstance(d, Document):
                        lc_docs.append(d)
                if lc_docs:
                    bm25_retriever = BM25Retriever.from_documents(lc_docs)
                    bm25_retriever.k = k_s
                    sparse_docs = bm25_retriever.invoke(query)
        except Exception as e:
            logger.warning("Sparse BM25 retrieval fallback: %s", e)

        # Reciprocal Rank Fusion
        retrieval_sets = [docs for docs in [dense_docs, sparse_docs] if docs]
        if retrieval_sets:
            fused_docs = rrf.rank(retrieval_sets)
        else:
            fused_docs = []

        # Deduplicate
        seen_texts = set()
        candidate_docs: List[Document] = []
        for doc in fused_docs:
            normalized = doc.page_content.strip()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                candidate_docs.append(doc)

        if len(candidate_docs) > 1:
            reranked = self.reranker.compress_documents(
                documents=candidate_docs, query=query
            )
            return reranked[:top_n]
        return candidate_docs[:top_n]


rag_pipeline = RAGPipeline(reranker=reranker)

