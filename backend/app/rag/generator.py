"""
generator.py — send the prompt to an LLM via OpenRouter and return the generated answer.
"""
import json
import os
import urllib.request

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemini-2.5-flash-lite"   # swap for any OpenRouter model slug
API_KEY = os.environ.get("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")


def generate(messages: list[dict]) -> str:
    if not API_KEY:
        raise RuntimeError("Set the OPENROUTER_API_KEY environment variable.")

    payload = json.dumps({"model": MODEL_NAME, "messages": messages}).encode()
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())

    return data["choices"][0]["message"]["content"]
