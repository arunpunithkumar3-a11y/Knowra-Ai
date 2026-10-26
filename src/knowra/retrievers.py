import logging
import uuid
from typing import List, Optional, Tuple, Union

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    VectorParams,
)

from src.client import qdrant_client
from src.config import (
    child_splitter,
    embedding_model,
    parent_splitter,
)

logger = logging.getLogger(__name__)


class SentenceWindowParentChildRetriever:
    """
    Multi-tenant Sentence-Window + Parent-Child Retriever.

    Splits documents into parent chunks with sliding window contexts, then splits
    into child chunks for fine-grained vector similarity search in Qdrant.
    Retrieval is completely stateless: window passages are stored directly inside
    the child vector metadata in Qdrant.
    """

    def __init__(
        self,
        parent_splitter: RecursiveCharacterTextSplitter,
        child_splitter: RecursiveCharacterTextSplitter,
        embedding_model: Embeddings,
        qdrant_client: QdrantClient,
        collection_name: str = "knowra_documents",
        window: int = 2,
        id_key: str = "parent_id",
        vector_size: int = 2048,
    ):
        self.parent_splitter = parent_splitter
        self.child_splitter = child_splitter
        self.embedding_model = embedding_model
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.window = window
        self.id_key = id_key
        self.vector_size = vector_size
        self._vector_store: Optional[QdrantVectorStore] = None
        self._collection_ready = False

    def _ensure_collection(self) -> None:
        """Create Qdrant collection and payload indices once if they do not exist."""
        if self._collection_ready:
            return
        try:
            if not self.qdrant_client.collection_exists(self.collection_name):
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Created Qdrant collection '%s'.", self.collection_name)

            for field in ("metadata.business_id", "metadata.document_id"):
                try:
                    self.qdrant_client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field,
                        field_schema="keyword",
                    )
                except Exception:
                    pass
            self._collection_ready = True
        except Exception as e:
            logger.warning("Qdrant collection setup check failed: %s", e)

    def get_vector_store(self) -> QdrantVectorStore:
        """Returns the cached LangChain Qdrant vector store."""
        if self._vector_store is None:
            self._ensure_collection()
            self._vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                embedding=self.embedding_model,
            )
        return self._vector_store

    def delete_document_vectors(
        self,
        business_id: Union[str, uuid.UUID],
        document_id: Union[str, uuid.UUID],
    ) -> None:
        """Delete all child vectors for a document in Qdrant."""
        biz_key = str(business_id)
        doc_key = str(document_id)

        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.business_id",
                            match=MatchValue(value=biz_key),
                        ),
                        FieldCondition(
                            key="metadata.document_id",
                            match=MatchValue(value=doc_key),
                        ),
                    ]
                ),
            )
            logger.info(
                "Deleted vectors for document '%s' (business '%s').", doc_key, biz_key
            )
        except Exception as e:
            logger.exception(
                "Failed to delete vectors for document '%s': %s", doc_key, e
            )

    async def add_documents(
        self,
        docs: Union[Document, List[Document]],
        business_id: Union[str, uuid.UUID],
        document_id: Union[str, uuid.UUID],
    ) -> Tuple[List[Document], List[Document]]:
        """
        Split document into windowed parents and index child vectors in Qdrant.
        Returns: (parent_documents, child_documents)
        """
        if not docs:
            return [], []

        biz_key = str(business_id)
        doc_key = str(document_id)
        doc_list = [docs] if isinstance(docs, Document) else docs

        parent_chunks = self.parent_splitter.split_documents(doc_list)
        if not parent_chunks:
            return [], []

        # 1. Attach sliding window context across neighboring parents
        for i, parent in enumerate(parent_chunks):
            start = max(i - self.window, 0)
            end = min(i + 1 + self.window, len(parent_chunks))
            parent.metadata["window"] = "\n\n".join(
                p.page_content.strip() for p in parent_chunks[start:end]
            )
            parent.metadata["business_id"] = biz_key
            parent.metadata["document_id"] = doc_key

        # 2. Split parents into child vectors with window context attached in metadata
        child_docs: List[Document] = []
        for parent in parent_chunks:
            parent_id = str(uuid.uuid4())
            parent.metadata[self.id_key] = parent_id

            for child in self.child_splitter.split_documents([parent]):
                child_docs.append(
                    Document(
                        page_content=child.page_content,
                        metadata={
                            **child.metadata,
                            self.id_key: parent_id,
                            "child_id": str(uuid.uuid4()),
                            "business_id": biz_key,
                            "document_id": doc_key,
                            "parent_window": parent.metadata["window"],
                        },
                    )
                )

        if child_docs:
            await self.get_vector_store().aadd_documents(child_docs)

        logger.info(
            "Indexed %d parents and %d children for business '%s', document '%s'.",
            len(parent_chunks),
            len(child_docs),
            biz_key,
            doc_key,
        )
        return parent_chunks, child_docs

    def retrieve(
        self,
        query: str,
        business_id: Union[str, uuid.UUID],
        k: int = 4,
    ) -> List[Document]:
        """
        Retrieve parent window passages via child-vector similarity search in Qdrant.
        Completely stateless: reconstructs parent windows directly from vector metadata.
        """
        if not query or not query.strip():
            return []

        biz_key = str(business_id)
        try:
            matched_children = self.get_vector_store().similarity_search(
                query=query,
                k=max(k * 3, 12),
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.business_id",
                            match=MatchValue(value=biz_key),
                        )
                    ]
                ),
            )
        except Exception as e:
            logger.exception(
                "Qdrant similarity search failed for business '%s': %s", biz_key, e
            )
            return []

        seen_parents = set()
        results: List[Document] = []

        for child in matched_children:
            parent_id = child.metadata.get(self.id_key)
            if parent_id and parent_id in seen_parents:
                continue
            if parent_id:
                seen_parents.add(parent_id)

            window_text = (
                child.metadata.get("parent_window") or child.page_content
            ).strip()
            if not window_text:
                continue

            results.append(
                Document(
                    page_content=window_text,
                    metadata={
                        self.id_key: parent_id,
                        "business_id": biz_key,
                        "document_id": child.metadata.get("document_id", ""),
                        "matched_child": child.page_content,
                        "source": child.metadata.get("source", ""),
                    },
                )
            )

            if len(results) >= k:
                break

        return results


class ReciprocalRankFusion:
    """Reciprocal Rank Fusion (RRF) for merging multi-retriever rankings."""

    def __init__(self, k: int = 60):
        self.k = k

    def rank(
        self,
        retrieved_docs: List[List[Document]],
        k: Optional[int] = None,
    ) -> List[Document]:
        k_val = k if k is not None else self.k
        scores = {}
        docs = {}

        for doc_list in retrieved_docs:
            for rank_idx, doc in enumerate(doc_list, start=1):
                text = doc.page_content.strip()
                if not text:
                    continue
                scores[text] = scores.get(text, 0.0) + (1.0 / (k_val + rank_idx))
                docs.setdefault(text, doc)

        return [
            docs[t] for t, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]


def get_retriever():
    return SentenceWindowParentChildRetriever(
        parent_splitter=parent_splitter,
        child_splitter=child_splitter,
        embedding_model=embedding_model,
        qdrant_client=qdrant_client,
    )


rrf = ReciprocalRankFusion()
