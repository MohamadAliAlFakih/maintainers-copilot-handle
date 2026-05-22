"""Main chat loop: Groq tool-calling, max 5 turns, ToolError handling, observability."""
import json
import uuid
from pathlib import Path
from typing import Any, AsyncIterator

import httpx
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infra.logging_setup import get_logger
from app.repositories.messages import append_message, list_messages
from app.tools._base import ToolError
from app.tools.classify_issue import ClassifyIssueArgs, run_classify_issue
from app.tools.classify_issue import TOOL_SPEC as CLASSIFY_SPEC
from app.tools.extract_entities import ExtractEntitiesArgs, run_extract_entities
from app.tools.extract_entities import TOOL_SPEC as NER_SPEC
from app.tools.rag_search import RagSearchArgs, run_rag_search
from app.tools.rag_search import TOOL_SPEC as RAG_SPEC
from app.tools.summarize_thread import SummarizeThreadArgs, run_summarize_thread
from app.tools.summarize_thread import TOOL_SPEC as SUMMARIZE_SPEC
from app.tools.write_memory import TOOL_SPEC as MEMORY_SPEC
from app.tools.write_memory import WriteMemoryArgs, run_write_memory

log = get_logger(__name__)

MAX_TURNS = 5

ALL_TOOL_SPECS = [CLASSIFY_SPEC, NER_SPEC, SUMMARIZE_SPEC, RAG_SPEC, MEMORY_SPEC]


def _failure(error: str, retryable: bool = False) -> dict[str, Any]:
    """Builds a structured failure payload (matches ToolResult.failure().to_llm_payload())."""
    return {"ok": False, "error": ToolError(error=error, retryable=retryable).to_dict()}


async def dispatch_tool(
    *, name: str, arguments_json: str, deps: dict[str, Any]
) -> dict[str, Any]:
    """Routes a tool_call to its implementation; returns LLM-ready payload dict."""
    try:
        args_raw = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        return _failure(f"tool {name}: invalid JSON arguments")

    try:
        if name == "classify_issue":
            args = ClassifyIssueArgs(**args_raw)
            result = await run_classify_issue(args, deps["http"])
        elif name == "extract_entities":
            args = ExtractEntitiesArgs(**args_raw)
            result = await run_extract_entities(args, deps["http"])
        elif name == "summarize_thread":
            args = SummarizeThreadArgs(**args_raw)
            result = await run_summarize_thread(args, deps["http"])
        elif name == "rag_search":
            args = RagSearchArgs(**args_raw)
            result = await run_rag_search(
                args,
                session=deps["session"],
                orchestrator=deps["orchestrator"],
                groq=deps["groq"],
                prompts_dir=deps["prompts_dir"],
                conversation_id=deps.get("conversation_id"),
            )
        elif name == "write_memory":
            args = WriteMemoryArgs(**args_raw)
            result = await run_write_memory(
                args,
                session=deps["session"],
                http=deps["http"],
                user_id=deps["user_id"],
            )
        else:
            return _failure(f"unknown tool: {name}")
    except Exception as e:  # noqa: BLE001 — catch malformed args + anything unexpected
        log.exception("tool.dispatch.error", tool=name)
        return _failure(f"tool {name} failed: {e}")

    return result.to_llm_payload()


async def run_chat_loop(
    *,
    user_message: str,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    groq: AsyncGroq,
    http: httpx.AsyncClient,
    orchestrator: Any,
    session_factory: async_sessionmaker,
    prompts_dir: Path,
    model: str = "llama-3.3-70b-versatile",
) -> AsyncIterator[str]:
    """Yields streaming string chunks for the SSE response.

    Loop:
      1. Read history from DB
      2. Build messages list with system prompt + history + new user message
      3. Call Groq with tools=[...] each turn
      4. If finish_reason is tool_calls, dispatch each, append tool result message, loop
      5. Else stream final content and break
      6. Cap at MAX_TURNS to prevent runaway calls
    """
    system_prompt = (prompts_dir / "chatbot_system.md").read_text(encoding="utf-8")

    # Build conversation history
    async with session_factory() as session:
        history = await list_messages(session, conversation_id)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for m in history:
        msg: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.tool_calls:
            msg["tool_calls"] = m.tool_calls
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})

    # persist the user message
    async with session_factory() as session:
        await append_message(
            session, conversation_id=conversation_id, role="user", content=user_message
        )
        await session.commit()

    for turn in range(MAX_TURNS):
        try:
            resp = await groq.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                tools=ALL_TOOL_SPECS,  # type: ignore[arg-type]
                tool_choice="auto",
                max_tokens=1000,
                temperature=0.2,
            )
        except Exception as e:  # noqa: BLE001
            log.exception("chat.llm.failed")
            yield f"data: {json.dumps({'type':'error','message':f'LLM call failed: {e}'})}\n\n"
            return

        choice = resp.choices[0]
        finish = choice.finish_reason
        msg = choice.message

        if finish == "tool_calls" and msg.tool_calls:
            # Persist the assistant turn that requested tools
            tc_serialized = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": tc_serialized})

            # Dispatch each tool
            tool_results_for_db: list[dict[str, Any]] = []
            for tc in msg.tool_calls:
                yield f"data: {json.dumps({'type':'tool_call','name':tc.function.name})}\n\n"
                async with session_factory() as session:
                    deps = {
                        "http": http,
                        "session": session,
                        "orchestrator": orchestrator,
                        "groq": groq,
                        "prompts_dir": prompts_dir,
                        "conversation_id": str(conversation_id),
                        "user_id": user_id,
                    }
                    payload = await dispatch_tool(
                        name=tc.function.name,
                        arguments_json=tc.function.arguments,
                        deps=deps,
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(payload),
                    }
                )
                tool_results_for_db.append({"tool_call_id": tc.id, "payload": payload})
                yield f"data: {json.dumps({'type':'tool_result','name':tc.function.name,'ok':payload.get('ok')})}\n\n"

            async with session_factory() as session:
                await append_message(
                    session,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=msg.content or "",
                    tool_calls=tc_serialized,
                    tool_results=tool_results_for_db,
                )
                await session.commit()
            continue

        # Final assistant message — stream the content
        final_content = msg.content or ""
        async with session_factory() as session:
            await append_message(
                session, conversation_id=conversation_id, role="assistant", content=final_content
            )
            await session.commit()
        for line in final_content.splitlines(keepends=True):
            yield f"data: {json.dumps({'type':'token','content':line})}\n\n"
        yield f"data: {json.dumps({'type':'done'})}\n\n"
        return

    # Cap reached — force a final answer
    log.warning("chat.cap_reached", turns=MAX_TURNS, conversation_id=str(conversation_id))
    messages.append(
        {
            "role": "user",
            "content": "You've used all available tool budget. Produce your final answer now using only what you have so far.",
        }
    )
    try:
        resp = await groq.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=600,
            temperature=0.0,
        )
        final = (resp.choices[0].message.content or "") + "\n\n(I had to stop tool use early.)"
    except Exception as e:  # noqa: BLE001
        final = f"(I had to stop tool use early and the final synthesis also failed: {e})"

    async with session_factory() as session:
        await append_message(
            session, conversation_id=conversation_id, role="assistant", content=final
        )
        await session.commit()
    yield f"data: {json.dumps({'type':'token','content':final})}\n\n"
    yield f"data: {json.dumps({'type':'done'})}\n\n"
