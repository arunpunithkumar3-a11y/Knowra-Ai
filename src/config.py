from langchain_nvidia_ai_endpoints import NVIDIARerank
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str
    JWT_ALGORITHM: str
    QDRANT_URL: str
    QDRANT_API_KEY: str
    NVIDIA_API_KEY: str
    NVIDIA_BASE_URL: str
    EMBEDDING_MODEL: str
    RERANKER_MODEL: str
    LLM_MODEL: str
    PARENT_CHUNK_SIZE: int = 350
    PARENT_CHUNK_OVERLAP: int = 50
    CHILD_CHUNK_SIZE: int = 75
    CHILD_CHUNK_OVERLAP: int = 20

    # Sentence-Window Parameters
    WINDOW_SIZE: int = 2  # +/- 2 neighboring parent chunks

    # Hybrid Retrieval & Reranker Defaults
    DENSE_K: int = 4
    SPARSE_K: int = 3
    RRF_K: int = 60
    TOP_K_RERANK: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


configure = Settings()


embedding_model = OpenAIEmbeddings(
    base_url=configure.NVIDIA_BASE_URL,
    model=configure.EMBEDDING_MODEL,
    api_key=configure.NVIDIA_API_KEY,
    check_embedding_ctx_length=False,
    model_kwargs={"extra_body": {"input_type": "passage"}},
)

parent_splitter = RecursiveCharacterTextSplitter(
    chunk_size=configure.PARENT_CHUNK_SIZE,
    chunk_overlap=configure.PARENT_CHUNK_OVERLAP,
)
child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=configure.CHILD_CHUNK_SIZE,
    chunk_overlap=configure.CHILD_CHUNK_OVERLAP,
)

reranker = NVIDIARerank(
    model=configure.RERANKER_MODEL,
    api_key=configure.NVIDIA_API_KEY,
    top_n=configure.TOP_K_RERANK,
)
