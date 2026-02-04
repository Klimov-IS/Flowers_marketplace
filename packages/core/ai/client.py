"""DeepSeek API client for AI-assisted normalization."""
import json
import os
from typing import Any, Optional

import httpx

from packages.core.ai.schemas import AIExtractionResponse


class DeepSeekError(Exception):
    """Exception raised for DeepSeek API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DeepSeekClient:
    """Client for DeepSeek API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize DeepSeek client.

        Args:
            api_key: DeepSeek API key (or from DEEPSEEK_API_KEY env var)
            base_url: API base URL (or from DEEPSEEK_BASE_URL env var)
            model: Model name (or from DEEPSEEK_MODEL env var)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout = timeout

        if not self.api_key:
            raise DeepSeekError("DEEPSEEK_API_KEY not set")

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0, lower = more deterministic)
            max_tokens: Maximum tokens in response
            response_format: Response format (e.g., {"type": "json_object"})

        Returns:
            API response dict

        Raises:
            DeepSeekError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                error_body = e.response.text
                raise DeepSeekError(
                    f"API error: {e.response.status_code} - {error_body}",
                    status_code=e.response.status_code,
                )
            except httpx.RequestError as e:
                raise DeepSeekError(f"Request failed: {str(e)}")

    async def extract_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> tuple[dict[str, Any], int, int]:
        """
        Send a request expecting JSON response.

        Args:
            system_prompt: System message content
            user_prompt: User message content
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (parsed JSON dict, input tokens, output tokens)

        Raises:
            DeepSeekError: If API request fails or response is not valid JSON
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        # Extract usage stats
        usage = response.get("usage", {})
        tokens_input = usage.get("prompt_tokens", 0)
        tokens_output = usage.get("completion_tokens", 0)

        # Extract content
        choices = response.get("choices", [])
        if not choices:
            raise DeepSeekError("No choices in response")

        content = choices[0].get("message", {}).get("content", "")

        # Parse JSON
        try:
            parsed = json.loads(content)
            return parsed, tokens_input, tokens_output
        except json.JSONDecodeError as e:
            raise DeepSeekError(f"Invalid JSON response: {str(e)}\nContent: {content[:500]}")

    def is_available(self) -> bool:
        """Check if client is properly configured."""
        return bool(self.api_key)
