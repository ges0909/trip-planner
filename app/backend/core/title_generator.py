import logging

from pydantic_ai.messages import ModelRequest, TextPart, UserPromptPart
from pydantic_ai.settings import ModelSettings

from core.model_gateway import get_model

logger = logging.getLogger(__name__)

TITLE_SYSTEM_PROMPT = """Fasse den folgenden Chat-Verlauf in genau 3 bis 5 prägnanten Schlüsselwörtern zusammen.
Regeln:
- Maximal 45 Zeichen insgesamt.
- Nutze kurze Stichwörter mit Mittelpunkt oder Bindestrich getrennt (z. B. "Radtour Wannsee · 45 km · Potsdam").
- Keine Anführungszeichen, keine Sätze, kein Punkt am Ende.
- antworte ausschließlich mit den 3-5 Schlüsselwörtern in der Sprache des Chats ({language}).
"""


async def generate_session_title(
    chat_history: list[dict[str, str]],
    language: str = "de",
) -> str:
    """Generate a 3-5 word concise title for a session based on full chat history.

    Args:
        chat_history: List of message dicts [{"role": "user"|"assistant", "content": "..."}].
        language: "de" or "en".

    Returns:
        Concise 3-5 word title string.
    """
    if not chat_history:
        return "Neue Session" if language == "de" else "New Session"

    # Format last few messages for title summary (limit to last 6 messages to keep fast)
    recent_messages = chat_history[-6:]
    formatted_chat = "\n".join(
        f"{m.get('role', 'user').capitalize()}: {m.get('content', '')[:300]}"
        for m in recent_messages
    )

    sys_prompt = TITLE_SYSTEM_PROMPT.format(language="Deutsch" if language == "de" else "English")
    prompt = f"Chat-Verlauf:\n{formatted_chat}\n\nSchlüsselwörter:"

    try:
        model = get_model()
        messages = [
            ModelRequest(parts=[UserPromptPart(content=f"{sys_prompt}\n\n{prompt}")]),
        ]

        response = await model.request(
            messages,
            model_settings=ModelSettings(max_tokens=60, temperature=0.3),
            model_request_parameters=None,
        )

        for part in response.parts:
            if isinstance(part, TextPart) and part.content:
                title = part.content.strip().strip('"').strip("'").strip(".")
                if title:
                    # Truncate to max 50 chars if model exceeded limit
                    if len(title) > 50:
                        title = title[:47] + "..."
                    logger.info("Generated LLM session title: %s", title)
                    return title
    except Exception as e:
        logger.warning("Failed to generate LLM session title: %s", e)

    # Fallback: First user message content truncated
    first_user_msg = next((m["content"] for m in chat_history if m.get("role") == "user"), "")
    fallback = first_user_msg[:45].strip() if first_user_msg else "Tour Session"
    return fallback
