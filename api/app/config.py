from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    OLLAMA_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str
    OLLAMA_NUM_CTX: int
    TEMPLATES_DIR: str = "templates"
    LOG_LEVEL: str
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
