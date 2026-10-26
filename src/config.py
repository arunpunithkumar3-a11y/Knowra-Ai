import logging
from pathlib import Path
from typing import Any, List, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str
    JWT_ALGORITHM: str
    QDRANT_URL: str
    QDRANT_API_KEY: str
    NVIDIA_API_KEY: str
    GROQ_API_KEY: str
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
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = ""
    MAIL_FROM_NAME: str = "Knowra"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    DOMAIN: str = "localhost:8000"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",
    )


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
            try:
                from langchain_nvidia_ai_endpoints import NVIDIARerank
                from langchain_nvidia_ai_endpoints._statics import MODEL_TABLE, Model

                model_name = configure.RERANKER_MODEL
                if model_name and model_name not in MODEL_TABLE:
                    MODEL_TABLE[model_name] = Model(
                        id=model_name,
                        model_type="ranking",
                        client="NVIDIARerank",
                        endpoint=f"https://ai.api.nvidia.com/v1/retrieval/{model_name}/reranking",
                        supports_tools=False,
                        supports_structured_output=False,
                        supports_thinking=False,
                        deprecated=False,
                    )

                self._instance = NVIDIARerank(
                    model=model_name,
                    api_key=configure.NVIDIA_API_KEY,
                    top_n=configure.TOP_K_RERANK,
                )
            except Exception as e:
                logger.warning("Reranker initialization skipped/failed: %s", e)
                self._instance = None
        return self._instance

    def compress_documents(self, documents: List[Any], query: str, *args, **kwargs) -> List[Any]:
        inst = self._get_instance()
        if inst is not None:
            try:
                return inst.compress_documents(documents=documents, query=query, *args, **kwargs)
            except Exception as e:
                logger.warning("Reranking failed (%s); returning unranked candidates.", e)
        return documents[: configure.TOP_K_RERANK]

    async def acompress_documents(self, documents: List[Any], query: str, *args, **kwargs) -> List[Any]:
        inst = self._get_instance()
        if inst is not None:
            try:
                return await inst.acompress_documents(documents=documents, query=query, *args, **kwargs)
            except Exception as e:
                logger.warning("Async reranking failed (%s); returning unranked candidates.", e)
        return documents[: configure.TOP_K_RERANK]


reranker = _LazyReranker()


class _LazyClassifier:
    def __init__(self):
        self._instance = None

    def _get_instance(self):
        if self._instance is None:
            pkl_path = Path(__file__).resolve().parent.parent / "question_relevance_pipeline.pkl"
            if pkl_path.exists():
                try:
                    import joblib
                    self._instance = joblib.load(pkl_path)
                except Exception as e:
                    logger.warning("Classifier load failed: %s", e)
                    self._instance = None
        return self._instance

    def predict(self, texts: List[str], *args, **kwargs) -> List[str]:
        inst = self._get_instance()
        if inst is not None:
            try:
                return inst.predict(texts, *args, **kwargs)
            except Exception as e:
                logger.warning("Classifier predict failed: %s", e)
        return ["no"] * len(texts)


classifier = _LazyClassifier()


safety_llm = ChatOpenAI(
    model="nvidia/nemotron-3.5-content-safety",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=configure.NVIDIA_API_KEY,
    temperature=0,
)
