import logging
import uuid
from typing import List, Union

from langchain_core.documents import Document

from src.config import configure, reranker
from src.knowra.retrievers import get_retriever, rrf

logger = logging.getLogger(__name__)


def invalidate_bm25_cache(business_id: Union[str, uuid.UUID]) -> None:
    """Invalidate cached sparse retrieval entries for a business.

    The current retriever implementation is stateless and does not maintain a BM25
    cache, so this is a safe no-op placeholder for the Celery worker contract.
    """
    logger.info("BM25 cache invalidation requested for business '%s'.", business_id)


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
        dense_docs = retriever.retrieve(
            query=query, business_id=biz_key, k=configure.DENSE_K
        )

        fused_docs = rrf.rank([docs for docs in (dense_docs) if docs])
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
