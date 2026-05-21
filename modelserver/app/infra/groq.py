"""Async Groq client wrapper with retries and timeout."""
from groq import AsyncGroq
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def build_groq_client(api_key: str, timeout: float = 60.0) -> AsyncGroq:
    """Builds an AsyncGroq client. Single instance per process."""
    return AsyncGroq(api_key=api_key, timeout=timeout)


async def chat_complete(
    client: AsyncGroq,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> str:
    """Calls Groq chat.completions and returns the assistant's content string with retries."""
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
