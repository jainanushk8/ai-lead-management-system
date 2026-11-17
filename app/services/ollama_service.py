"""
app/services/ollama_service.py

Service module to interact with the local Ollama server and classify leads using the Hermes model.

Provides:
    classify_lead(lead_id: int, message: str) -> dict

The function builds a prompt, calls Ollama generate endpoint with JSON format, parses the result,
and returns a dictionary containing:
    - temperature: "hot" | "warm" | "cold"
    - requirements: list of strings extracted from the LLM response
    - ai_response: raw response string from the model
    - analysis_status: "completed" if successful, otherwise "failed"
"""

import json
import logging
from typing import Any, Dict, List

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def _post_to_ollama(prompt: str) -> Dict[str, Any]:
    """Send a prompt to Ollama and return the parsed JSON response.

    The Ollama `/api/generate` endpoint is used with ``format": "json"`` to request a JSON
    response. If the model does not return valid JSON we fall back to extracting a JSON
    fragment with a regular expression.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }
    timeout = settings.OLLAMA_TIMEOUT_SECONDS
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        # Ollama returns a JSON with a "response" field containing the model output.
        data = response.json()
        raw = data.get("response", "")
        # Attempt to parse the raw string as JSON.
        try:
            parsed = json.loads(raw)
            return {"raw": raw, "parsed": parsed}
        except json.JSONDecodeError:
            # Fallback: look for the first JSON object in the string.
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    return {"raw": raw, "parsed": parsed}
                except json.JSONDecodeError:
                    pass
            # If still not JSON, wrap the raw string.
            return {"raw": raw, "parsed": {}}


async def classify_lead(lead_id: int, message: str) -> Dict[str, Any]:
    """Classify a lead using the Hermes LLM.

    Parameters
    ----------
    lead_id: int
        Database identifier of the lead – passed through for traceability.
    message: str
        The free‑form message supplied by the lead.

    Returns
    -------
    dict
        ``{"temperature": str, "requirements": List[str], "ai_response": str, "analysis_status": str}``
    """
    # Build a prompt that asks the model to decide temperature, extract requirements,
    # and generate a personalized response message tailored to the lead.
    prompt = (
        f"You are an expert AI sales assistant. Analyze the following lead message and output a JSON object with these keys:\n"
        f"- \"temperature\": one of 'hot', 'warm', 'cold'\n"
        f"- \"requirements\": list of explicit product or service requirements mentioned\n"
        f"- \"personalized_response\": a polite, professional, and tailored reply directly to the customer acknowledging their specific requirements and proposing next steps\n"
        f"- \"explanation\": a short sentence summarising your categorization reasoning\n"
        f"Use only valid JSON.\n\n"
        f"Lead Message:\n{message}\n"
    )

    logger.debug("Sending prompt to Ollama for lead %s", lead_id)
    try:
        result = await _post_to_ollama(prompt)
    except Exception as exc:
        logger.error("Ollama request failed: %s", exc)
        # Fallback to a safe default classification.
        return {
            "temperature": "warm",
            "requirements": [],
            "ai_response": f"Ollama service temporarily unavailable: {exc}",
            "analysis_status": "failed",
        }

    raw_response = result.get("raw", "")
    parsed = result.get("parsed", {})

    temperature = parsed.get("temperature", "warm")  # default to warm if missing
    requirements = parsed.get("requirements", [])
    if not isinstance(requirements, list):
        # Ensure a list – some models may return a string.
        requirements = [str(requirements)]

    # Extract personalized response if present, else fallback to explanation or raw
    personalized_response = parsed.get("personalized_response") or parsed.get("explanation") or raw_response
    ai_response = str(personalized_response)
    analysis_status = "completed" if temperature else "failed"

    return {
        "temperature": temperature,
        "requirements": requirements,
        "ai_response": ai_response,
        "analysis_status": analysis_status,
    }
