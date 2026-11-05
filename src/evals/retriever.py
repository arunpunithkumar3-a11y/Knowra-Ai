import sys
import uuid
from pathlib import Path
from typing import List

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import embedding_model, reranker

DATA_DIR = CURRENT_DIR / "data"
PDF_PATH = DATA_DIR / "urbannest_workspace_knowledge_base_5_pages.pdf"
CHROMA_DIR = CURRENT_DIR / "chroma_db"

loader = PyPDFLoader(str(PDF_PATH))
pages = loader.load()

parent_splitter = RecursiveCharacterTextSplitter(chunk_size=350, chunk_overlap=50)
child_splitter = RecursiveCharacterTextSplitter(chunk_size=75, chunk_overlap=20)

parent_chunks = parent_splitter.split_documents(pages)

# 1. Attach sliding window context and parent_id to parent chunks
for i, parent in enumerate(parent_chunks):
    start = max(i - 2, 0)
    end = min(i + 1 + 2, len(parent_chunks))
    parent.metadata["window"] = "\n\n".join(
        p.page_content.strip() for p in parent_chunks[start:end]
    )
    parent.metadata["parent_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"parent_{i}"))

# 2. Build child chunks from parent chunks with window metadata
child_docs: List[Document] = []
child_ids: List[str] = []

for parent in parent_chunks:
    parent_id = parent.metadata["parent_id"]
    for c_idx, child in enumerate(child_splitter.split_documents([parent])):
        child_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{parent_id}_child_{c_idx}"))
        child_docs.append(
            Document(
                page_content=child.page_content,
                metadata={
                    **child.metadata,
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "parent_window": parent.metadata["window"],
                },
            )
        )
        child_ids.append(child_id)

# 3. Setup BM25 Retriever on CHILD chunks (in-memory keyword index)
bm25_retriever = BM25Retriever.from_documents(child_docs, k=5)

# 4. Setup Chroma Vector Store on CHILD chunks (persistent disk-based vector index)
vector_store = Chroma(
    embedding_function=embedding_model,
    persist_directory=str(CHROMA_DIR),
    collection_name="urbannest_workspace_knowledge_base",
)

retriever = vector_store.as_retriever(search_kwargs={"k": 5})


def add_docs(batch_size: int = 100):
    """Populate Chroma vector store with child chunks containing parent window context."""
    if child_docs:
        for i in range(0, len(child_docs), batch_size):
            batch_docs = child_docs[i : i + batch_size]
            batch_ids = child_ids[i : i + batch_size]
            vector_store.add_documents(batch_docs, ids=batch_ids)
        print(f"Indexed {len(child_docs)} child documents into Chroma.")


# Automatically index if Chroma collection is empty
if vector_store._collection.count() == 0:
    print("Chroma collection is empty. Indexing test document...")
    add_docs()


def rrf(retrieved_docs: List[List[Document]], k_val: int = 60) -> List[Document]:
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


def final_retrieve(query: str, top_k: int = 3) -> List[Document]:
    # 1. Dense retrieval (Chroma) + unwrap parent_window & deduplicate by parent_id
    dense_raw = retriever.invoke(query)
    dense_docs: List[Document] = []
    seen_dense_parents = set()

    for child in dense_raw:
        parent_id = child.metadata.get("parent_id")
        if parent_id and parent_id in seen_dense_parents:
            continue
        if parent_id:
            seen_dense_parents.add(parent_id)

        window_text = (
            child.metadata.get("parent_window") or child.page_content
        ).strip()
        if not window_text:
            continue

        dense_docs.append(
            Document(
                page_content=window_text,
                metadata={
                    **child.metadata,
                    "matched_child": child.page_content,
                },
            )
        )

    # 2. Sparse retrieval (BM25 on child chunks) + unwrap to parent_window & deduplicate
    sparse_raw = bm25_retriever.invoke(query)
    sparse_docs: List[Document] = []
    seen_sparse_parents = set()

    for child in sparse_raw:
        parent_id = child.metadata.get("parent_id")
        if parent_id and parent_id in seen_sparse_parents:
            continue
        if parent_id:
            seen_sparse_parents.add(parent_id)

        window_text = (
            child.metadata.get("parent_window") or child.page_content
        ).strip()
        if not window_text:
            continue

        sparse_docs.append(
            Document(
                page_content=window_text,
                metadata={
                    **child.metadata,
                    "matched_child": child.page_content,
                },
            )
        )

    if not dense_docs and not sparse_docs:
        return []

    # 3. Reciprocal Rank Fusion
    fused_docs = rrf([dense_docs, sparse_docs])
    if not fused_docs:
        return []

    # 4. Cross-Encoder Reranking
    if len(fused_docs) > 1 and reranker:
        try:
            candidates = fused_docs[: min(len(fused_docs), top_k * 2)]
            reranked = reranker.compress_documents(documents=candidates, query=query)
            if reranked:
                return reranked[:top_k]
        except Exception as e:
            print(f"Reranking failed ({e}); returning fused candidates.")

    return fused_docs[:top_k]


if __name__ == "__main__":
    import json

    raw_collection = vector_store._collection
    # Chroma's Collection.get() does not accept `ids` in the include list;
    # the IDs are returned as a separate top-level key in the response.
    data = raw_collection.get(include=["documents", "metadatas"])

    exported_chunks = []
    for i in range(len(data["ids"])):
        exported_chunks.append(
            {
                "id": data["ids"][i],
                "document": data["documents"][i],
                "metadata": data["metadatas"][i],
            }
        )

    with open("langchain_chroma_chunks.json", "w", encoding="utf-8") as f:
        json.dump(exported_chunks, f, ensure_ascii=False, indent=2)

    print(
        f"Successfully exported {len(exported_chunks)} chunks to"
        " langchain_chroma_chunks.json"
    )
