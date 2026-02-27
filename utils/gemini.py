"""Google Gemini API integration for dynamic D&D content generation."""

from __future__ import annotations

import json
import re
import textwrap

from google import genai
from google.genai import types

_client: genai.Client | None = None
_model_name = "gemini-2.0-flash"


def init_gemini(api_key: str) -> None:
    global _client
    _client = genai.Client(api_key=api_key)


def is_initialised() -> bool:
    return _client is not None


# ---------------------------------------------------------------------------
# JSON schema templates shown to Gemini so responses are importable
# ---------------------------------------------------------------------------

_CREATURE_SCHEMA = {
    "name": "string",
    "size": "string (e.g. Medium humanoid)",
    "alignment": "string",
    "challenge": "string (e.g. '5 (1,800 XP)')",
    "hit_points": "string (e.g. '65 (10d8+20)')",
    "armor_class": "string (e.g. '15 (chain mail)')",
    "speed": "string (e.g. '30 ft.')",
    "str_score": "integer",
    "dex_score": "integer",
    "con_score": "integer",
    "int_score": "integer",
    "wis_score": "integer",
    "cha_score": "integer",
    "str_mod": "string (e.g. '(+2)')",
    "dex_mod": "string",
    "con_mod": "string",
    "int_mod": "string",
    "wis_mod": "string",
    "cha_mod": "string",
    "skills": "string",
    "saving_throws": "string",
    "senses": "string",
    "languages": "string",
    "abilities": "string (Markdown – traits, actions, legendary actions)",
    "source": "Gemini",
}

_SPELL_SCHEMA = {
    "name": "string",
    "level": "integer (0 = cantrip)",
    "school": "string",
    "casting_time": "string",
    "range": "string",
    "components": "string",
    "duration": "string",
    "description": "string",
    "classes": "string (comma-separated)",
    "source": "Gemini",
}

_ITEM_SCHEMA = {
    "name": "string",
    "type": "string (e.g. Weapon, Armor, Wondrous Item)",
    "rarity": "string (common/uncommon/rare/very rare/legendary/artifact)",
    "description": "string",
    "properties": "object (any additional key-value properties)",
    "source": "Gemini",
}


def _extract_json(text: str) -> dict | None:
    """Try to extract the first JSON object from a Gemini response."""
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?", "", text).strip("` \n")
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _ask(prompt: str) -> str:
    if _client is None:
        raise RuntimeError("Gemini not initialised – please provide an API key.")
    response = _client.models.generate_content(model=_model_name, contents=prompt)
    return response.text


def lookup_creature(name: str) -> dict | None:
    prompt = textwrap.dedent(f"""
        You are a D&D 5e rules expert. Return a JSON object describing the creature
        "{name}" using *exactly* this schema (fill every field):

        {json.dumps(_CREATURE_SCHEMA, indent=2)}

        Respond with only the JSON object – no extra text.
    """)
    return _extract_json(_ask(prompt))


def lookup_spell(name: str) -> dict | None:
    prompt = textwrap.dedent(f"""
        You are a D&D 5e rules expert. Return a JSON object describing the spell
        "{name}" using *exactly* this schema (fill every field):

        {json.dumps(_SPELL_SCHEMA, indent=2)}

        Respond with only the JSON object – no extra text.
    """)
    return _extract_json(_ask(prompt))


def lookup_item(name: str) -> dict | None:
    prompt = textwrap.dedent(f"""
        You are a D&D 5e rules expert. Return a JSON object describing the magic item
        "{name}" using *exactly* this schema (fill every field):

        {json.dumps(_ITEM_SCHEMA, indent=2)}

        Respond with only the JSON object – no extra text.
    """)
    return _extract_json(_ask(prompt))


def encounter_suggestions(participants: list[dict], notes: str = "") -> str:
    """Return narrative / tactical suggestions for an encounter in progress."""
    participant_summary = "\n".join(
        f"- {p['name']} (HP {p['hp_current']}/{p['hp_max']})" for p in participants
    )
    prompt = textwrap.dedent(f"""
        You are an experienced D&D 5e Dungeon Master providing tactical advice.

        Current encounter participants:
        {participant_summary}

        Additional notes: {notes or 'None'}

        Provide 3-5 concise tactical suggestions or narrative hooks for this encounter.
        Be specific and practical.
    """)
    return _ask(prompt)
