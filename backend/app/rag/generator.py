"""
generator.py — send the prompt to an LLM via OpenRouter and return the generated answer.
"""
import json
import os
import urllib.request

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.environ.get("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")

# Tried in order — OpenRouter auto-falls-back to the next if one is rate-limited/down.
MODEL_FALLBACKS = [
    "nvidia/nemotron-nano-9b-v2:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "meta-llama/llama-3-8b-instruct:free",
]


def generate(messages: list[dict]) -> str:
    if not API_KEY:
        raise RuntimeError("Set the OPENROUTER_API_KEY environment variable.")

    payload = json.dumps({"models": MODEL_FALLBACKS, "messages": messages}).encode()
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
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
   
