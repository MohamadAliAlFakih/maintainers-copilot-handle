"""Structure-aware markdown chunker: header boundaries, intact code fences, size limits."""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

import tiktoken
from markdown_it import MarkdownIt

# Tokenizer for chunk-size budgeting. cl100k_base is OpenAI's; close enough to BGE's tokenizer for sizing.
_ENC = tiktoken.get_encoding("cl100k_base")
_MAX_TOKENS = 800
_MIN_TOKENS = 100
_OVERLAP_TOKENS = 100


@dataclass
class Chunk:
    """One unit of corpus content with full metadata."""

    text: str
    source_type: Literal["doc", "resolved_issue"]
    source_path: str
    section_headers: list[str] = field(default_factory=list)
    version_tag: str = "main"
    chunk_id: str = ""


def _make_chunk_id(source_path: str, headers: list[str], text_prefix: str) -> str:
    """Deterministic chunk_id = sha256(source_path + headers + first 80 chars)."""
    key = f"{source_path}|{'>'.join(headers)}|{text_prefix[:80]}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def _count_tokens(text: str) -> int:
    """Returns the number of tokens in the text using cl100k_base."""
    return len(_ENC.encode(text))


def _split_by_paragraph(text: str, max_tokens: int, overlap: int) -> list[str]:
    """Splits oversized text on blank lines, then re-joins with overlap."""
    paras = re.split(r"\n\s*\n", text.strip())
    out: list[str] = []
    current = ""
    for para in paras:
        candidate = (current + "\n\n" + para).strip() if current else para
        if _count_tokens(candidate) > max_tokens and current:
            out.append(current)
            tail_tokens = _ENC.encode(current)[-overlap:]
            current = _ENC.decode(tail_tokens) + "\n\n" + para
        else:
            current = candidate
    if current:
        out.append(current)
    return out


def _walk_tokens(md_text: str) -> list[dict]:
    """Parses markdown into a flat list of segments tagged with their enclosing header chain."""
    md = MarkdownIt("commonmark")
    tokens = md.parse(md_text)

    segments: list[dict] = []
    header_stack: list[tuple[int, str]] = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok.type == "heading_open":
            level = int(tok.tag[1])
            inline = tokens[i + 1]
            header_text = inline.content.strip()
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()
            header_stack.append((level, header_text))
            segments.append(
                {
                    "kind": "heading",
                    "level": level,
                    "text": header_text,
                    "headers": [h[1] for h in header_stack],
                }
            )
            i += 3
            continue

        if tok.type == "fence":
            segments.append(
                {
                    "kind": "fence",
                    "text": f"```{tok.info}\n{tok.content}```",
                    "headers": [h[1] for h in header_stack],
                }
            )
            i += 1
            continue

        if tok.type == "paragraph_open":
            inline = tokens[i + 1]
            segments.append(
                {"kind": "text", "text": inline.content, "headers": [h[1] for h in header_stack]}
            )
            i += 3
            continue

        if tok.type in ("bullet_list_open", "ordered_list_open"):
            depth = 1
            j = i + 1
            buf: list[str] = []
            while j < len(tokens) and depth > 0:
                if tokens[j].type in ("bullet_list_open", "ordered_list_open"):
                    depth += 1
                elif tokens[j].type in ("bullet_list_close", "ordered_list_close"):
                    depth -= 1
                if tokens[j].type == "inline":
                    buf.append(f"- {tokens[j].content}")
                j += 1
            segments.append(
                {"kind": "text", "text": "\n".join(buf), "headers": [h[1] for h in header_stack]}
            )
            i = j
            continue

        i += 1

    return segments


def chunk_markdown(text: str, source_path: str, version_tag: str = "main") -> list[Chunk]:
    """Splits markdown into structure-aware chunks. Returns ordered list."""
    segments = _walk_tokens(text)

    grouped: list[dict] = []
    current_group: dict | None = None

    for seg in segments:
        if seg["kind"] == "heading":
            if current_group is not None:
                grouped.append(current_group)
            current_group = {"headers": seg["headers"], "parts": []}
        else:
            if current_group is None:
                current_group = {"headers": [], "parts": []}
            current_group["parts"].append(seg)

    if current_group is not None:
        grouped.append(current_group)

    chunks: list[Chunk] = []

    def _same_parent(a: list[str], b: list[str]) -> bool:
        """True when two header chains share the same parent (all but the last element)."""
        return len(a) >= 1 and len(b) >= 1 and a[:-1] == b[:-1]

    # Preprocess: fold any group that is BOTH (a) under MIN_TOKENS AND (b) immediately
    # followed by a sibling under the same parent. Otherwise keep groups intact so each
    # header section becomes its own chunk.
    folded: list[dict] = []
    i = 0
    while i < len(grouped):
        cur = grouped[i]
        cur_body = "\n\n".join(p["text"] for p in cur["parts"])
        cur_tokens = _count_tokens(
            " > ".join(cur["headers"]) + "\n\n" + cur_body if cur["headers"] else cur_body
        )

        nxt = grouped[i + 1] if i + 1 < len(grouped) else None
        if (
            cur_tokens < _MIN_TOKENS
            and nxt is not None
            and _same_parent(cur["headers"], nxt["headers"])
        ):
            merged = {
                "headers": nxt["headers"],
                "parts": cur["parts"] + nxt["parts"],
            }
            folded.append(merged)
            i += 2
        else:
            folded.append(cur)
            i += 1

    for group in folded:
        body = "\n\n".join(p["text"] for p in group["parts"])
        body_with_header_prefix = (
            " > ".join(group["headers"]) + "\n\n" + body if group["headers"] else body
        )
        # Skip groups whose body is empty after stripping (e.g., parent heading whose only
        # content was promoted into a child group).
        if not body.strip():
            continue
        n_tokens = _count_tokens(body_with_header_prefix)

        if n_tokens <= _MAX_TOKENS:
            chunks.append(
                Chunk(
                    text=body_with_header_prefix,
                    source_type="doc",
                    source_path=source_path,
                    section_headers=group["headers"],
                    version_tag=version_tag,
                    chunk_id=_make_chunk_id(source_path, group["headers"], body_with_header_prefix),
                )
            )
        else:
            parts = _split_by_paragraph(body, _MAX_TOKENS, _OVERLAP_TOKENS)
            header_prefix = " > ".join(group["headers"]) + "\n\n" if group["headers"] else ""
            for part in parts:
                full = header_prefix + part
                chunks.append(
                    Chunk(
                        text=full,
                        source_type="doc",
                        source_path=source_path,
                        section_headers=group["headers"],
                        version_tag=version_tag,
                        chunk_id=_make_chunk_id(source_path, group["headers"], full),
                    )
                )

    return chunks
