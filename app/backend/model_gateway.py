"""Model gateway — LLM provider abstraction via pydantic-ai.

Supports multiple LLM providers configured via environment variables:
- Google: LLM_PROVIDER=google (default)
- OpenAI: LLM_PROVIDER=openai
- Anthropic: LLM_PROVIDER=anthropic

The appropriate API key must be set for the chosen provider.

pydantic-ai uses the format "provider:model-name" for model identification,
e.g., "google:gemini-2.5-flash", "openai:gpt-4o-mini", "anthropic:claude-haiku-4-5".
"""

import logging
import os
from typing import Literal

from dotenv import load_dotenv
from pydantic_ai.models import Model, infer_model

load_dotenv()

logger = logging.getLogger(__name__)

Provider = Literal["google", "openai", "anthropic"]

# Default models per provider (pydantic-ai format: provider:model)
DEFAULT_MODELS: dict[Provider, str] = {
    "google": "google:gemini-2.5-flash",
    "openai": "openai:gpt-4o-mini",
    "anthropic": "anthropic:claude-haiku-4-5",
}

# Environment variable names for API keys
API_KEY_ENV_VARS: dict[Provider, str] = {
    "google": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def get_provider() -> Provider:
    """Get configured LLM provider from environment.

    Returns:
        Provider name (google, openai, or anthropic).
        Defaults to 'google' if not configured.
    """
    provider = os.getenv("LLM_PROVIDER", "google").lower()
    # Support 'gemini' as alias for 'google'
    if provider == "gemini":
        provider = "google"
    if provider not in ("google", "openai", "anthropic"):
        logger.warning("Unknown LLM_PROVIDER '%s', falling back to google", provider)
        return "google"
    return provider  # type: ignore


def get_model_name(provider: Provider | None = None) -> str:
    """Get full model identifier for the given provider.

    Args:
        provider: LLM provider. If None, uses configured provider.

    Returns:
        Full model identifier in pydantic-ai format (provider:model).
    """
    if provider is None:
        provider = get_provider()

    custom_model = os.getenv("LLM_MODEL")
    if custom_model:
        # If user provides full identifier (e.g., "openai:gpt-4o"), use as-is
        if ":" in custom_model:
            return custom_model
        # Otherwise, prepend provider
        return f"{provider}:{custom_model}"

    return DEFAULT_MODELS[provider]


def get_api_key(provider: Provider) -> str:
    """Get API key for the given provider.

    Args:
        provider: LLM provider.

    Returns:
        API key string.

    Raises:
        RuntimeError: If API key is not configured.
    """
    env_var = API_KEY_ENV_VARS[provider]
    api_key = os.getenv(env_var)

    if not api_key:
        raise RuntimeError(
            f"{env_var} not set. Please configure it in your .env file "
            f"or set LLM_PROVIDER to a different provider."
        )

    return api_key


def _set_api_key_env(provider: Provider) -> None:
    """Set the API key in environment for pydantic-ai to pick up.

    pydantic-ai reads API keys from standard environment variables.
    This ensures the right key is set regardless of our naming convention.
    """
    api_key = get_api_key(provider)

    if provider == "google":
        os.environ["GOOGLE_API_KEY"] = api_key
    elif provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key


def get_model() -> Model:
    """Get pydantic-ai Model instance based on environment configuration.

    Reads LLM_PROVIDER and LLM_MODEL from environment, along with
    the appropriate API key for the chosen provider.

    Returns:
        Configured pydantic-ai Model instance.

    Raises:
        RuntimeError: If required API key is not configured.

    Example:
        >>> model = get_model()
        >>> agent = Agent(model=model, system_prompt="...")
    """
    provider = get_provider()
    model_id = get_model_name(provider)

    # Ensure API key is available in environment
    _set_api_key_env(provider)

    logger.info("Initializing LLM: %s", model_id)

    return infer_model(model_id)


def get_model_info() -> dict[str, str]:
    """Get information about the configured model.

    Returns:
        Dict with provider, model, and api_key_configured status.
    """
    provider = get_provider()
    model_id = get_model_name(provider)
    env_var = API_KEY_ENV_VARS[provider]
    has_key = bool(os.getenv(env_var))

    return {
        "provider": provider,
        "model": model_id,
        "api_key_configured": str(has_key).lower(),
    }
