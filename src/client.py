from qdrant_client import QdrantClient

try:
    from src.config import configure
except ImportError:
    from config import configure

qdrant_client = QdrantClient(
    url=configure.QDRANT_URL,
    api_key=configure.QDRANT_API_KEY,
)
