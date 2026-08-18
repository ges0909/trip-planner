"""Simple i18n for user-facing error messages and status labels."""

from typing import Literal

type Lang = Literal["de", "en"]

MESSAGES: dict[str, dict[Lang, str]] = {
    "quota_exhausted": {
        "de": "LLM-Kontingent erschöpft oder Anfrage zu groß. Bitte prüfe dein Guthaben oder versuche eine kleinere Anfrage.",
        "en": "LLM quota exhausted or request too large. Please check your balance or try a smaller request.",
    },
    "api_error": {
        "de": "API-Fehler ({code}): {detail}",
        "en": "API error ({code}): {detail}",
    },
    "server_unavailable": {
        "de": "LLM-Server nicht erreichbar ({code}). Bitte später erneut versuchen.",
        "en": "LLM server unavailable ({code}). Please try again later.",
    },
    "unexpected_error": {
        "de": "Unerwarteter Fehler: {detail}",
        "en": "Unexpected error: {detail}",
    },
    "max_iterations": {
        "de": "Maximale Iterationen erreicht. Bitte versuche eine kürzere Anfrage.",
        "en": "Maximum iterations reached. Please try a shorter request.",
    },
    "no_api_key": {
        "de": "Der API-Schlüssel für das LLM ist nicht konfiguriert.",
        "en": "The API key for the LLM is not configured.",
    },
    "internal_error": {
        "de": "Interner Fehler: {detail}",
        "en": "Internal error: {detail}",
    },
    # Tool group status messages
    "status_routing": {
        "de": "🗺️ Berechne Route …",
        "en": "🗺️ Calculating route …",
    },
    "status_location": {
        "de": "📍 Suche Orte …",
        "en": "📍 Searching locations …",
    },
    "status_weather": {
        "de": "🌤️ Prüfe Wetter …",
        "en": "🌤️ Checking weather …",
    },
    "status_transit": {
        "de": "🚆 Suche Nahverkehrsverbindungen …",
        "en": "🚆 Searching regional connections …",
    },
    "status_pois": {
        "de": "📌 Suche Sehenswürdigkeiten …",
        "en": "📌 Searching points of interest …",
    },
    "status_trails": {
        "de": "🥾 Suche Wander-/Radrouten …",
        "en": "🥾 Searching hiking/cycling trails …",
    },
    "status_travel_info": {
        "de": "📖 Suche Reiseinformationen …",
        "en": "📖 Searching travel information …",
    },
    "status_web_search": {
        "de": "🔍 Suche im Web …",
        "en": "🔍 Searching the web …",
    },
    "status_rendering": {
        "de": "🖼️ Erstelle Karte …",
        "en": "🖼️ Rendering map …",
    },
    "status_generic": {
        "de": "⚙️ Verarbeite …",
        "en": "⚙️ Processing …",
    },
}


def msg(key: str, lang: Lang, **kwargs: str | int) -> str:
    """Get a localized message by key, formatted with kwargs."""
    template = MESSAGES.get(key, {}).get(lang, MESSAGES.get(key, {}).get("en", key))
    return template.format(**kwargs) if kwargs else template
