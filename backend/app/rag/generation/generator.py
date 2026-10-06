import os
import httpx


class OpenRouterGenerator:

    def __init__(
        self,
        model: str = "openai/gpt-4o-mini"
    ):

        self.api_key = os.getenv(
            "OPENROUTER_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set"
            )

        self.model = model

        self.url = (
            "https://openrouter.ai/api/v1/chat/completions"
        )

    async def generate(
        self,
        prompt: str
    ) -> str:

        headers = {
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You answer questions strictly "
                        "from the supplied document context."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        }

        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:

            response = await client.post(
                self.url,
                headers=headers,
                json=payload
            )

            response.raise_for_status()

            data = response.json()

        return (
            data["choices"][0]["message"]["content"]
            .strip()
        )
