from qdrant_client import QdrantClient

from src.config import configure

qdrant_client = QdrantClient(
    url=configure.QDRANT_URL,
    api_key=configure.QDRANT_API_KEY,
)
