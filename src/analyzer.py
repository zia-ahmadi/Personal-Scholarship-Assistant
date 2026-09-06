"""Local Ollama analysis helpers.

This module sends cleaned opportunity text to a local Ollama model and asks for
structured JSON. It does not call any external AI API.
"""

from __future__ import annotations

import json
from typing import Any

import requests


OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b"
OLLAMA_KEEP_ALIVE = "10m"

OPPORTUNITY_FIELDS = [
    "title",
    "organization",
    "deadline",
    "funding",
    "degree_requirement",
    "field_requirement",
    "nationality_requirement",
    "gpa_requirement",
    "english_requirement",
    "required_documents",
    "other_eligibility_requirements",
]


def analyze_opportunity_text(
    opportunity_text: str,
    model: str = DEFAULT_MODEL,
    timeout: int = 300,
) -> dict[str, Any]:
    """Extract structured opportunity data from text using local Ollama."""
    text = opportunity_text.strip()
    if not text:
        return {
            "ok": False,
            "data": empty_opportunity_data(),
            "error": "Opportunity text is empty.",
            "raw_response": None,
        }

    prompt = build_extraction_prompt(text)

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "keep_alive": OLLAMA_KEEP_ALIVE,
                "options": {
                    "temperature": 0,
                },
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return {
            "ok": False,
            "data": empty_opportunity_data(),
            "error": f"Could not connect to Ollama: {error}",
            "raw_response": None,
        }

    try:
        ollama_payload = response.json()
    except ValueError:
        return {
            "ok": False,
            "data": empty_opportunity_data(),
            "error": "Ollama returned an invalid API response.",
            "raw_response": response.text,
        }

    raw_text = ollama_payload.get("response", "")
    parsed_data, parse_error = parse_json_response(raw_text)

    if parse_error:
        return {
            "ok": False,
            "data": empty_opportunity_data(),
            "error": parse_error,
            "raw_response": raw_text,
        }

    return {
        "ok": True,
        "data": normalize_opportunity_data(parsed_data),
        "error": None,
        "raw_response": raw_text,
    }


def build_extraction_prompt(opportunity_text: str) -> str:
    """Build a strict prompt for JSON-only extraction."""
    fields = "\n".join(f'- "{field}"' for field in OPPORTUNITY_FIELDS)

    return f"""
You extract scholarship, fellowship, internship, or academic opportunity data.

Return ONLY valid JSON.
Do not include markdown.
Do not explain your answer.
Do not invent missing information.
If a field is not clearly present in the text, use null.

The JSON object must contain exactly these keys:
{fields}

Rules:
- funding must describe the actual financial support or benefits stated in the
    text, such as tuition coverage, stipend, accommodation, insurance, or other
    fee waivers. Do not output "Unpaid" or similar employment wording merely
    because this is a scholarship or because no salary is mentioned.
- deadline should be the date for the current opportunity/application cycle
    described in the text, if clearly available, otherwise null. If the text
    says that the current cycle's deadline is not yet published, not announced,
    or otherwise unavailable, return null. Ignore dates explicitly identified as
    belonging to an older or previous cycle; never use an old cycle's deadline
    as the current opportunity deadline.
- required_documents should be a list of strings, or null.
- other_eligibility_requirements should be a list of strings, or null.
- All other fields should be strings or null.

Opportunity text:
\"\"\"
{opportunity_text[:12000]}
\"\"\"
""".strip()


def parse_json_response(raw_text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse JSON from Ollama and report malformed output without crashing."""
    if not raw_text.strip():
        return None, "Ollama returned an empty response."

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        json_block = extract_json_object(raw_text)
        if json_block is None:
            return None, "Ollama returned malformed JSON."

        try:
            parsed = json.loads(json_block)
        except json.JSONDecodeError:
            return None, "Ollama returned malformed JSON."

    if not isinstance(parsed, dict):
        return None, "Ollama JSON response was not an object."

    return parsed, None


def extract_json_object(text: str) -> str | None:
    """Try to recover a JSON object if the model adds extra text."""
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    return text[start : end + 1]


def normalize_opportunity_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return only the expected keys and fill missing values with None."""
    normalized = empty_opportunity_data()

    for field in OPPORTUNITY_FIELDS:
        value = data.get(field)
        normalized[field] = value if value not in ("", "unknown", "Unknown") else None

    return normalized


def empty_opportunity_data() -> dict[str, Any]:
    """Create an empty result with every expected field set to None."""
    return {field: None for field in OPPORTUNITY_FIELDS}


if __name__ == "__main__":
    sample_text = """
    The Global Computer Science Scholarship is offered by Example University.
    It is fully funded and open to international students applying for a
    master's degree in Computer Science or Software Engineering. Applicants
    should have a bachelor's degree. IELTS 6.5 is required. Documents include
    transcript, CV, recommendation letters, and statement of purpose.
    Deadline: January 15, 2027.
    """

    result = analyze_opportunity_text(sample_text)
    print(json.dumps(result, indent=2))
