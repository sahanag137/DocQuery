
import os
import httpx
from dotenv import load_dotenv


load_dotenv()


class OpenRouterGenerator:

    def __init__(
        self,
        model: str = "openai/gpt-4o-mini"
    ):
        self.api_key = os.getenv("OPENROUTER_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Check your backend .env file."
            )

        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate(self, prompt: str) -> str:

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a document question-answering assistant. "
                        "Answer strictly using the supplied document context. "
                        "Do not invent information."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        }

        async with httpx.AsyncClient(timeout=120.0) as client:

            response = await client.post(
                self.url,
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            data = response.json()

        try:
            answer = data["choices"][0]["message"]["content"]

            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("The LLM returned an empty answer")

            return answer.strip()

        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected OpenRouter response: {data}"
            ) from exc
