from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

SAFETY_MODEL = "openai/gpt-oss-safeguard-20b"
FAST_MODEL = "openai/gpt-oss-20b"
QUALITY_MODEL = "openai/gpt-oss-120b"


class Settings(BaseSettings):
    groq_api_key: str

    # Guardrail uses a model tuned for safety/policy classification.
    # Classifier is a single-shot, low-complexity routing decision that
    # runs on every query, so a small/fast general model keeps the
    # pipeline responsive. Summarize/synthesize/qna need real reasoning
    # quality over clinical content, so they default to the larger model.
    groq_model_guardrail: str = SAFETY_MODEL
    groq_model_classifier: str = FAST_MODEL
    groq_model_summarize: str = QUALITY_MODEL
    groq_model_synthesize: str = QUALITY_MODEL
    groq_model_qna: str = QUALITY_MODEL

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
