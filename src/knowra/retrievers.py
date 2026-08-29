import logging
import uuid
from typing import Dict, List, Optional, Union

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

    Architecture:

        Full Document
              ↓
        Parent Splitter
              ↓
        Parent Chunks
              ↓
        Sliding Window
              ↓
        Child Splitter
              ↓
        Child Chunks
              ↓
        Embeddings
              ↓
        Qdrant Cloud

    All businesses share one Qdrant collection.

    Tenant isolation is handled through:
        business_id
    stored in Qdrant payload metadata.
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

        # Parent documents are kept here temporarily during runtime.
        #
        # IMPORTANT:
        # This is NOT the source of truth.
        # The parent window is also stored inside Qdrant metadata,
        # so retrieval still works after a restart.
        self.parents: Dict[str, Dict[str, Document]] = {}

        self._initialize_collection()

    # ============================================================
    # QDRANT COLLECTION
    # ============================================================

    def _initialize_collection(self) -> None:
        """
        Create the Qdrant collection if it doesn't already exist.
        """

        if not self.qdrant_client.collection_exists(self.collection_name):
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

            logger.info(
                "Created Qdrant collection '%s'.",
                self.collection_name,
            )

    # ============================================================
    # QDRANT VECTOR STORE
    # ============================================================

    def get_vector_store(self) -> QdrantVectorStore:
        """
        Returns the LangChain Qdrant vector store.
        """

        return QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embedding=self.embedding_model,
        )

    # ============================================================
    # ADD DOCUMENTS
    # ============================================================

    def add_documents(
        self,
        docs: Union[Document, List[Document]],
        business_id: Union[str, uuid.UUID],
        document_id: Union[str, uuid.UUID],
    ) -> tuple[List[Document], List[Document]]:
        """
        Split and index a document into Qdrant.

        Returns:
            (
                parent_documents,
                child_documents
            )
        """

        biz_key = str(business_id)
        doc_key = str(document_id)

        if biz_key not in self.parents:
            self.parents[biz_key] = {}

        if isinstance(docs, Document):
            docs = [docs]

        # ========================================================
        # STEP 1
        # Parent splitting
        # ========================================================

        parent_chunks = self.parent_splitter.split_documents(docs)

        # ========================================================
        # STEP 2
        # Sliding window
        # ========================================================

        for i, parent in enumerate(parent_chunks):
            start = max(
                i - self.window,
                0,
            )

            end = min(
                i + 1 + self.window,
                len(parent_chunks),
            )

            window_content = "\n\n".join(
                parent_chunks[j].page_content.strip() for j in range(start, end)
            )

            parent.metadata["window"] = window_content

            parent.metadata["business_id"] = biz_key

            parent.metadata["document_id"] = doc_key

        # ========================================================
        # STEP 3
        # Parent → Child splitting
        # ========================================================

        child_docs_to_index: List[Document] = []

        for parent in parent_chunks:
            parent_id = str(uuid.uuid4())

            parent.metadata[self.id_key] = parent_id

            self.parents[biz_key][parent_id] = parent

            child_chunks = self.child_splitter.split_documents([parent])

            for child in child_chunks:
                child_id = str(uuid.uuid4())

                child_doc = Document(
                    page_content=child.page_content,
                    metadata={
                        **child.metadata,
                        self.id_key: parent_id,
                        "child_id": child_id,
                        "business_id": biz_key,
                        "document_id": doc_key,
                        "parent_window": parent.metadata["window"],
                    },
                )

                child_docs_to_index.append(child_doc)

        # ========================================================
        # STEP 4
        # Store children in Qdrant
        # ========================================================

        if child_docs_to_index:
            vector_store = self.get_vector_store()

            vector_store.add_documents(child_docs_to_index)

        logger.info(
            "Indexed %d parent chunks and %d child vectors "
            "for business '%s', document '%s'.",
            len(parent_chunks),
            len(child_docs_to_index),
            biz_key,
            doc_key,
        )

        return (
            parent_chunks,
            child_docs_to_index,
        )

    # ============================================================
    # RETRIEVE
    # ============================================================

    def retrieve(
        self,
        query: str,
        business_id: Union[str, uuid.UUID],
        k: int = 4,
    ) -> List[Document]:
        """
        Retrieve parent windows using child-vector similarity.

        Retrieval is strictly filtered by business_id.
        """

        biz_key = str(business_id)

        vector_store = self.get_vector_store()

        # Search more children than final result count.
        child_k = max(
            k * 3,
            12,
        )

        # ========================================================
        # BUSINESS FILTER
        # ========================================================

        business_filter = Filter(
            must=[
                FieldCondition(
                    key="metadata.business_id",
                    match=MatchValue(value=biz_key),
                )
            ]
        )

        # ========================================================
        # VECTOR SEARCH
        # ========================================================

        try:
            matched_children = vector_store.similarity_search(
                query=query,
                k=child_k,
                filter=business_filter,
            )

        except Exception as e:
            logger.exception(
                "Qdrant similarity search failed for business '%s': %s",
                biz_key,
                e,
            )

            return []

        # ========================================================
        # RESOLVE PARENTS
        # ========================================================

        seen_parents = set()

        seen_windows = set()

        results: List[Document] = []

        biz_parents = self.parents.get(
            biz_key,
            {},
        )

        for child in matched_children:
            parent_id = child.metadata.get(self.id_key)

            if not parent_id:
                continue

            if parent_id in seen_parents:
                continue

            seen_parents.add(parent_id)

            # ====================================================
            # Try in-memory parent first
            # ====================================================

            if parent_id in biz_parents:
                parent_doc = biz_parents[parent_id]

                window_text = parent_doc.metadata.get(
                    "window",
                    parent_doc.page_content,
                )

            # ====================================================
            # Fallback to persistent Qdrant metadata
            # ====================================================

            else:
                window_text = child.metadata.get(
                    "parent_window",
                    child.page_content,
                )

            window_text = window_text.strip()

            if not window_text:
                continue

            if window_text in seen_windows:
                continue

            seen_windows.add(window_text)

            retrieved_doc = Document(
                page_content=window_text,
                metadata={
                    self.id_key: parent_id,
                    "business_id": biz_key,
                    "document_id": child.metadata.get(
                        "document_id",
                        "",
                    ),
                    "matched_child": child.page_content,
                    "source": child.metadata.get(
                        "source",
                        "",
                    ),
                },
            )

            results.append(retrieved_doc)

            if len(results) >= k:
                break

        return results


# ================================================================
# RECIPROCAL RANK FUSION
# ================================================================


class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion.

    RRF score:

        score(d) =
            Σ 1 / (k + rank(d))
    """

    def __init__(
        self,
        k: int = 60,
    ):
        self.k = k

    def rank(
        self,
        retrieved_docs: List[List[Document]],
        k: Optional[int] = None,
    ) -> List[Document]:

        k_val = k if k is not None else self.k

        fused_scores = {}

        doc_lookup = {}

        for doc_list in retrieved_docs:
            for rank_idx, doc in enumerate(
                doc_list,
                start=1,
            ):
                content = doc.page_content.strip()

                score = 1.0 / (k_val + rank_idx)

                if content not in fused_scores:
                    fused_scores[content] = score

                    doc_lookup[content] = doc

                else:
                    fused_scores[content] += score

        sorted_items = sorted(
            fused_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [doc_lookup[content] for content, _ in sorted_items]


retriever = SentenceWindowParentChildRetriever(
    parent_splitter=parent_splitter,
    child_splitter=child_splitter,
    embedding_model=embedding_model,
    qdrant_client=qdrant_client,
)

rrf = ReciprocalRankFusion()
