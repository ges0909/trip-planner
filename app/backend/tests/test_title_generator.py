import pytest
from core.title_generator import generate_session_title
from pydantic_ai.messages import TextPart


@pytest.mark.asyncio
async def test_generate_session_title_success(monkeypatch):
    """Test generating a concise title using mocked model."""

    class FakeModelResponse:
        def __init__(self):
            self.parts = [TextPart(content="Radtour Wannsee · 45 km · Potsdam")]

    class FakeModel:
        async def request(self, *args, **kwargs):
            return FakeModelResponse()

    monkeypatch.setattr("core.title_generator.get_model", lambda model_id=None: FakeModel())

    chat_history = [
        {"role": "user", "content": "Ich möchte eine Radtour von Berlin nach Potsdam machen."},
        {"role": "assistant", "content": "# Berliner Radtour\n\nSchöne 45 km Strecke."},
    ]

    title = await generate_session_title(chat_history, language="de")
    assert title == "Radtour Wannsee · 45 km · Potsdam"


@pytest.mark.asyncio
async def test_generate_session_title_fallback_on_error(monkeypatch):
    """Test falling back to user message snippet when model fails."""

    class FailingModel:
        async def request(self, *args, **kwargs):
            raise RuntimeError("Model timeout")

    monkeypatch.setattr("core.title_generator.get_model", lambda model_id=None: FailingModel())

    chat_history = [
        {"role": "user", "content": "Roadtrip durch Schweden von Malmö nach Stockholm"},
    ]

    title = await generate_session_title(chat_history, language="de")
    assert "Roadtrip durch Schweden" in title
