"""AI module for normalization assistance using DeepSeek API."""
from packages.core.ai.client import DeepSeekClient
from packages.core.ai.schemas import (
    AIExtractionRequest,
    AIExtractionResponse,
    RowSuggestion,
    FieldExtraction,
)
from packages.core.ai.service import AIService

__all__ = [
    "DeepSeekClient",
    "AIService",
    "AIExtractionRequest",
    "AIExtractionResponse",
    "RowSuggestion",
    "FieldExtraction",
]
