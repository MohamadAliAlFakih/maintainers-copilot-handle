"""Async Azure OpenAI client wrapper with retries and timeout."""

from openai import AsyncAzureOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def build_llm_client(
    api_key: str,
    endpoint: str,
    api_version: str = "2024-11-20",
    timeout: float = 60.0,
) -> AsyncAzureOpenAI:
    """Builds an AsyncAzureOpenAI client. Single instance per process."""
    return AsyncAzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
        timeout=timeout,
    )


async def chat_complete(
    client: AsyncAzureOpenAI,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> str:
    """Calls chat.completions and returns the assistant's content string with retries."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    ):
        with attempt:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
    return ""  # unreachable