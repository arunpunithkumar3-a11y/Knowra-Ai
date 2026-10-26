import asyncio
import logging
import time
import uuid
from typing import List, Union

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from src.config import configure, reranker
from src.core.main import async_session_maker
from src.knowra.retrievers import get_retriever, rrf
from src.services.document import document_service

logger = logging.getLogger(__name__)

_bm25_cache: dict[str, tuple[float, BM25Retriever]] = {}
BM25_CACHE_TTL = 300.0  # 5 minutes


def invalidate_bm25_cache(business_id: Union[str, uuid.UUID]) -> None:
    """Invalidate cached BM25 index for a business when its documents change."""
    _bm25_cache.pop(str(business_id), None)


class RAGPipeline:
    """
    Multi-Tenant Conversational RAG Pipeline:
    - Dense Sentence-Window Vector Search (Qdrant)
    - Sparse BM25 Keyword Search with caching
    - Concurrent dense and sparse retrieval
    - Reciprocal Rank Fusion (RRF)
    - Cross-Encoder Reranking with safe fallback
    """

    def __init__(self, reranker):
        self.reranker = reranker

    async def _get_sparse_docs(
        self,
        query: str,
        business_id: Union[str, uuid.UUID],
        k: int,
    ) -> List[Document]:
        """Fetch business documents from DB and run BM25 search with caching."""
        biz_key = str(business_id)
        now = time.monotonic()

        cached = _bm25_cache.get(biz_key)
        if cached and (now - cached[0] < BM25_CACHE_TTL):
            bm25 = cached[1]
            bm25.k = k
            try:
                return bm25.invoke(query)
            except Exception:
                pass

        try:
            async with async_session_maker() as session:
                records = await document_service.get_documents_by_business_id(
                    business_id=business_id,
                    session=session,
                )
            if not records:
                return []

            docs = [
                Document(
                    page_content=r.extracted_text,
                    metadata={
                        "source": getattr(r, "original_filename", "Knowledge Base"),
                        "business_id": biz_key,
                    },
                )
                for r in (records if isinstance(records, list) else [records])
                if getattr(r, "extracted_text", None) and r.extracted_text.strip()
            ]
            if not docs:
                return []

            bm25 = BM25Retriever.from_documents(docs)
            _bm25_cache[biz_key] = (now, bm25)
            bm25.k = k
            return bm25.invoke(query)
        except Exception as e:
            logger.warning("BM25 search skipped for business '%s': %s", biz_key, e)
            return []

    async def retrieve_ranked_context(
        self,
        query: str,
        business_id: Union[str, uuid.UUID] = "default_business",
    ) -> List[Document]:
        """Retrieve, fuse, and rerank documents for the specified business."""
        if not query or not query.strip():
            return []

        biz_key = str(business_id)
        top_n = configure.TOP_K_RERANK

        retriever = get_retriever()

        # Run dense and sparse retrieval in parallel
        dense_task = asyncio.to_thread(
            retriever.retrieve, query=query, business_id=biz_key, k=configure.DENSE_K
        )
        sparse_task = self._get_sparse_docs(
            query=query, business_id=biz_key, k=configure.SPARSE_K
        )
        dense_docs, sparse_docs = await asyncio.gather(dense_task, sparse_task)

        fused_docs = rrf.rank([docs for docs in (dense_docs, sparse_docs) if docs])
        if not fused_docs:
            return []

        if len(fused_docs) > 1 and self.reranker:
            try:
                candidates_to_rerank = fused_docs[: min(len(fused_docs), top_n * 2)]
                reranked = self.reranker.compress_documents(
                    documents=candidates_to_rerank, query=query
                )
                if reranked:
                    return reranked[:top_n]
            except Exception as e:
                logger.warning("Reranking failed (%s); returning fused candidates.", e)

        return fused_docs[:top_n]


rag_pipeline = RAGPipeline(reranker=reranker)
