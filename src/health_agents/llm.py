from langchain_groq import ChatGroq

from health_agents.config import get_settings


def get_groq_chat(model: str, temperature: float = 0.2) -> ChatGroq:
    settings = get_settings()
    return ChatGroq(model=model, api_key=settings.groq_api_key, temperature=temperature)
