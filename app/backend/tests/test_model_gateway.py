"""Tests for model_gateway — OpenRouter LLM configuration.

Covers:
- Environment variable handling
- Model ID formatting
- Error handling for missing API key
"""

import os
from unittest.mock import patch

import pytest


class TestGetModelId:
    """Tests for get_model_id function."""

    def test_returns_default_model_when_not_set(self):
        """Should return default model when LLM_MODEL not set."""
        from core.model_gateway import DEFAULT_MODEL, get_model_id

        with patch.dict(os.environ, {}, clear=True):
            # Remove LLM_MODEL if present
            os.environ.pop("LLM_MODEL", None)
            result = get_model_id()

        assert result == DEFAULT_MODEL
        assert result == "meta-llama/llama-3.3-70b-instruct"

    def test_returns_custom_model_when_set(self):
        """Should return custom model from environment."""
        from core.model_gateway import get_model_id

        with patch.dict(os.environ, {"LLM_MODEL": "anthropic/claude-sonnet-4"}):
            result = get_model_id()

        assert result == "anthropic/claude-sonnet-4"


class TestGetModelInfo:
    """Tests for get_model_info function."""

    def test_returns_correct_structure(self):
        """Should return dict with model, provider, and api_key_configured."""
        from core.model_gateway import get_model_info

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-test-key"}):
            result = get_model_info()

        assert "model" in result
        assert "provider" in result
        assert "api_key_configured" in result
        assert result["provider"] == "openrouter"

    def test_api_key_configured_true_when_set(self):
        """api_key_configured should be 'true' when key is set."""
        from core.model_gateway import get_model_info

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-test-key"}):
            result = get_model_info()

        assert result["api_key_configured"] == "true"

    def test_api_key_configured_false_when_not_set(self):
        """api_key_configured should be 'false' when key is not set."""
        from core.model_gateway import get_model_info

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENROUTER_API_KEY", None)
            result = get_model_info()

        assert result["api_key_configured"] == "false"


class TestSetupOpenRouter:
    """Tests for _setup_openrouter internal function."""

    def test_sets_openai_env_vars(self):
        """Should set OPENAI_API_KEY and OPENAI_BASE_URL for pydantic-ai."""
        from core.model_gateway import OPENROUTER_BASE_URL, _setup_openrouter

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test-key"}):
            _setup_openrouter()

            assert os.environ.get("OPENAI_API_KEY") == "sk-or-test-key"
            assert os.environ.get("OPENAI_BASE_URL") == OPENROUTER_BASE_URL

    def test_raises_error_when_api_key_missing(self):
        """Should raise RuntimeError when OPENROUTER_API_KEY not set."""
        from core.model_gateway import _setup_openrouter

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENROUTER_API_KEY", None)

            with pytest.raises(RuntimeError) as exc_info:
                _setup_openrouter()

            assert "OPENROUTER_API_KEY" in str(exc_info.value)
            assert "openrouter.ai" in str(exc_info.value)


class TestGetModel:
    """Tests for get_model function."""

    def test_raises_error_without_api_key(self):
        """get_model should raise RuntimeError when API key missing."""
        from core.model_gateway import get_model

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENROUTER_API_KEY", None)

            with pytest.raises(RuntimeError):
                get_model()

    def test_returns_model_with_valid_config(self):
        """get_model should return a Model instance when properly configured."""
        from core.model_gateway import get_model
        from pydantic_ai.models import Model

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test-key"}):
            result = get_model()

        assert isinstance(result, Model)


class TestOpenRouterConstants:
    """Tests for module-level constants."""

    def test_default_model_is_llama(self):
        """Default model should be Llama 3.3 70B."""
        from core.model_gateway import DEFAULT_MODEL

        assert DEFAULT_MODEL == "meta-llama/llama-3.3-70b-instruct"

    def test_base_url_is_openrouter(self):
        """Base URL should be OpenRouter's API."""
        from core.model_gateway import OPENROUTER_BASE_URL

        assert OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"


class TestFallbackChain:
    """Tests for fallback model configuration and chains."""

    def test_fallback_models_defaults(self):
        """Should return default fallback model IDs."""
        from core.model_gateway import get_fallback_model_ids

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LLM_FALLBACK_MODELS", None)
            fallbacks = get_fallback_model_ids()

        assert "mistralai/mistral-large-2411" in fallbacks
        assert "google/gemini-2.5-flash" in fallbacks

    def test_custom_fallback_models(self):
        """Should parse custom comma-separated fallback models."""
        from core.model_gateway import get_fallback_model_ids

        with patch.dict(os.environ, {"LLM_FALLBACK_MODELS": "model-a, model-b , model-c"}):
            fallbacks = get_fallback_model_ids()

        assert fallbacks == ["model-a", "model-b", "model-c"]

    def test_model_chain_order(self):
        """Model chain should have primary first, then fallbacks."""
        from core.model_gateway import get_model_chain

        with patch.dict(
            os.environ,
            {
                "LLM_MODEL": "primary-model",
                "LLM_FALLBACK_MODELS": "fallback-1, fallback-2",
            },
        ):
            chain = get_model_chain()

        assert chain == ["primary-model", "fallback-1", "fallback-2"]
