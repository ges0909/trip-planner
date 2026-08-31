"""Model gateway — OpenRouter LLM access via pydantic-ai.

Configuration via environment variables:
- OPENROUTER_API_KEY: Your OpenRouter API key (required)
- LLM_MODEL: Model ID from https://openrouter.ai/models
             (default: meta-llama/llama-3.3-70b-instruct)
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.models import Model, infer_model

# Load .env: Home first, then project (project overrides)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(Path.home() / ".env")  # Personal API keys
load_dotenv(PROJECT_ROOT / ".env", override=True)  # Project overrides

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_model_id() -> str:
    """Get the configured model identifier."""
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


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


def get_model() -> Model:
    """Get pydantic-ai Model instance configured for OpenRouter.

    Returns:
        Configured pydantic-ai Model instance.

    Raises:
        RuntimeError: If OPENROUTER_API_KEY is not configured.

    Example:
        >>> model = get_model()
        >>> agent = Agent(model=model, system_prompt="...")
    """
    _setup_openrouter()

    model_id = get_model_id()
    # pydantic-ai format for OpenAI-compatible APIs: openai:<model>
    # OpenRouter uses the model ID directly (e.g., meta-llama/llama-3.3-70b-instruct)
    full_model_id = f"openai:{model_id}"

    logger.info("Initializing LLM: %s", full_model_id)
    return infer_model(full_model_id)


def get_model_info() -> dict[str, str]:
    """Get information about the configured model."""
    return {
        "model": get_model_id(),
        "provider": "openrouter",
        "api_key_configured": str(bool(os.getenv("OPENROUTER_API_KEY"))).lower(),
    }
