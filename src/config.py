from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str
    JWT_ALGORITHM: str
    SUPABASE_API_KEY: str
    SUPABASE_URL: str
    BUCKET_NAME: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


configure = Settings()
