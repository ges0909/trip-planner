"""Model gateway — OpenRouter LLM access via pydantic-ai.

Configuration via environment variables:
- OPENROUTER_API_KEY: Your OpenRouter API key (required)
- LLM_MODEL: Primary model ID from https://openrouter.ai/models
             (default: meta-llama/llama-3.3-70b-instruct)
- LLM_FALLBACK_MODELS: Comma-separated list of fallback model IDs
                       (default: mistralai/mistral-large-2411,google/gemini-2.5-flash)
"""

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_ai.models import Model, infer_model

# Load .env: Home first, then project (project overrides)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(Path.home() / ".env")  # Personal API keys
load_dotenv(PROJECT_ROOT / ".env", override=True)  # Project overrides

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"
DEFAULT_FALLBACK_MODELS = "mistralai/mistral-large-2411,google/gemini-2.5-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_model_id() -> str:
    """Get the configured primary model identifier."""
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


def get_fallback_model_ids() -> list[str]:
    """Get the list of configured fallback model identifiers."""
    raw = os.getenv("LLM_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS)
    models = [m.strip() for m in raw.split(",") if m.strip()]
    primary = get_model_id()
    return [m for m in models if m != primary]


def get_model_chain() -> list[str]:
    """Get the complete model fallback chain: [primary, fallback1, fallback2, ...]."""
    primary = get_model_id()
    fallbacks = get_fallback_model_ids()
    chain = [primary]
    for fb in fallbacks:
        if fb not in chain:
            chain.append(fb)
    return chain


def _setup_openrouter() -> None:
    """Configure OpenRouter API credentials for pydantic-ai.

    OpenRouter uses the OpenAI-compatible API, so we set
    OPENAI_API_KEY and OPENAI_BASE_URL.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Get your key at https://openrouter.ai/keys")

    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = OPENROUTER_BASE_URL


def get_model(model_id: str | None = None) -> Model:
    """Get pydantic-ai Model instance configured for OpenRouter.

    Args:
        model_id: Optional specific model identifier. Defaults to get_model_id().

    Returns:
        Configured pydantic-ai Model instance.

    Raises:
        RuntimeError: If OPENROUTER_API_KEY is not configured.
    """
    _setup_openrouter()

    target_id = model_id or get_model_id()
    full_model_id = f"openai:{target_id}"

    logger.info("Initializing LLM: %s", full_model_id)
    return infer_model(full_model_id)


def get_model_info() -> dict[str, Any]:
    """Get information about the configured models and fallback chain."""
    return {
        "model": get_model_id(),
        "primary_model": get_model_id(),
        "fallback_models": get_fallback_model_ids(),
        "model_chain": get_model_chain(),
        "provider": "openrouter",
        "api_key_configured": str(bool(os.getenv("OPENROUTER_API_KEY"))).lower(),
    }
