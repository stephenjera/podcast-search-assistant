from openai import OpenAI

from config import settings
from logger import get_logger

logger = get_logger(__name__)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for embeddings")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    vectors = [item.embedding for item in response.data]
    logger.info(f"Generated {len(vectors)} embeddings")
    return vectors
