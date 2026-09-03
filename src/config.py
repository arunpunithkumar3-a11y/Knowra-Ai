from langchain_openai import ChatOpenAI, OpenAIEmbeddings
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
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

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


class _LazyReranker:
    def __init__(self):
        self._instance = None

    def _get_instance(self):
        if self._instance is None:
            from langchain_nvidia_ai_endpoints import NVIDIARerank

            self._instance = NVIDIARerank(
                model=configure.RERANKER_MODEL,
                api_key=configure.NVIDIA_API_KEY,
                top_n=configure.TOP_K_RERANK,
            )
        return self._instance

    def compress_documents(self, *args, **kwargs):
        return self._get_instance().compress_documents(*args, **kwargs)


reranker = _LazyReranker()


safety_llm = ChatOpenAI(
    model="nvidia/nemotron-3.5-content-safety",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=configure.NVIDIA_API_KEY,
    temperature=0,
)
