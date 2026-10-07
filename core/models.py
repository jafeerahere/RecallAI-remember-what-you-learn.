"""Replaceable inference interfaces; default adapters retain the existing models."""
from typing import Protocol
from utils.config import SUMMARY_MODEL, EMBEDDING_MODEL

class Summarizer(Protocol):
    def summarize(self, text: str, length: str, chunk_size: int) -> tuple[str, int]: ...

class Encoder(Protocol):
    def encode(self, texts: list[str]): ...

class LocalSummarizer:
    model_id = SUMMARY_MODEL
    processing = 'Local'
    def summarize(self, text, length='Medium', chunk_size=400):
        from core.summarizer import generate_summary
        return generate_summary(text, length, chunk_size)

class LocalEncoder:
    model_id = EMBEDDING_MODEL
    processing = 'Local'
    def encode(self, texts):
        from core.embeddings import encode_texts
        return encode_texts(tuple(texts), self.model_id)

class SourceQuestionGenerator:
    """Deterministic grounded fallback, explicitly used until a generative adapter is configured."""
    processing = 'Local'
    def generate(self, text, keywords, count=5):
        from core.quiz_generator import generate_quiz
        return generate_quiz(text,keywords,count)
