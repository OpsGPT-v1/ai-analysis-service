import json
from typing import Any


class JSONExtractionError(ValueError):
    """Raised when a model response does not contain a JSON object."""


def extract_json_object(content: str) -> dict[str, Any]:
    """Extract a JSON object from direct JSON or a fenced model response."""
    value = content.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1] if "\n" in value else ""
        if value.rstrip().endswith("```"):
            value = value.rstrip()[:-3]
    if value.lstrip().lower().startswith("json\n"):
        value = value.lstrip().split("\n", 1)[1]

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        if start == -1:
            raise JSONExtractionError("AI response did not contain a JSON object") from None
        try:
            parsed, _ = json.JSONDecoder().raw_decode(value[start:])
        except json.JSONDecodeError as exc:
            raise JSONExtractionError("AI response did not contain valid JSON") from exc

    if not isinstance(parsed, dict):
        raise JSONExtractionError("AI response JSON must be an object")
    return parsed
