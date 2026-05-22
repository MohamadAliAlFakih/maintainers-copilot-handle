"""Structure-aware chunkers (markdown + RST + issues) producing the same Chunk contract."""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Literal

import tiktoken
from docutils import nodes
from docutils.core import publish_doctree
from docutils.utils import SystemMessage
from markdown_it import MarkdownIt

_ENC = tiktoken.get_encoding("cl100k_base")
_MAX_TOKENS = 800
_MIN_TOKENS = 100
_OVERLAP_TOKENS = 100
_ISSUE_MAX_TOKENS = 1000


@dataclass
class Chunk:
    text: str
    source_type: Literal["doc", "resolved_issue"]
    source_path: str
    section_headers: list[str] = field(default_factory=list)
    version_tag: str = "main"
    chunk_id: str = ""


def _count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


def _make_chunk_id(source_path: str, headers: list[str], text: str) -> str:
    key = f"{source_path}|{'>'.join(headers)}|{text}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def _make_issue_id(issue_number: int, part: str) -> str:
    return hashlib.sha256(f"issues/{issue_number}|{part}".encode()).hexdigest()[:32]


# ---------- markdown ----------


def _split_by_paragraph(text: str, max_tokens: int, overlap: int) -> list[str]:
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


def _walk_md_tokens(md_text: str) -> list[dict]:
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
                {"kind": "heading", "level": level, "text": header_text,
                 "headers": [h[1] for h in header_stack]}
            )
            i += 3
            continue
        if tok.type == "fence":
            segments.append(
                {"kind": "fence", "text": f"```{tok.info}\n{tok.content}```",
                 "headers": [h[1] for h in header_stack]}
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
    segments = _walk_md_tokens(text)
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

    def _same_parent(a: list[str], b: list[str]) -> bool:
        return len(a) >= 1 and len(b) >= 1 and a[:-1] == b[:-1]

    folded: list[dict] = []
    i = 0
    while i < len(grouped):
        cur = grouped[i]
        cur_body = "\n\n".join(p["text"] for p in cur["parts"])
        cur_full = (
            " > ".join(cur["headers"]) + "\n\n" + cur_body if cur["headers"] else cur_body
        )
        nxt = grouped[i + 1] if i + 1 < len(grouped) else None
        if (
            _count_tokens(cur_full) < _MIN_TOKENS
            and nxt is not None
            and _same_parent(cur["headers"], nxt["headers"])
        ):
            folded.append({"headers": nxt["headers"], "parts": cur["parts"] + nxt["parts"]})
            i += 2
        else:
            folded.append(cur)
            i += 1

    chunks: list[Chunk] = []
    for group in folded:
        body = "\n\n".join(p["text"] for p in group["parts"])
        if not body.strip():
            continue
        full = " > ".join(group["headers"]) + "\n\n" + body if group["headers"] else body
        if _count_tokens(full) <= _MAX_TOKENS:
            chunks.append(
                Chunk(
                    text=full, source_type="doc", source_path=source_path,
                    section_headers=group["headers"], version_tag=version_tag,
                    chunk_id=_make_chunk_id(source_path, group["headers"], full),
                )
            )
        else:
            parts = _split_by_paragraph(body, _MAX_TOKENS, _OVERLAP_TOKENS)
            header_prefix = " > ".join(group["headers"]) + "\n\n" if group["headers"] else ""
            for part in parts:
                full_part = header_prefix + part
                chunks.append(
                    Chunk(
                        text=full_part, source_type="doc", source_path=source_path,
                        section_headers=group["headers"], version_tag=version_tag,
                        chunk_id=_make_chunk_id(source_path, group["headers"], full_part),
                    )
                )
    return chunks


# ---------- rst ----------


def _section_to_text(section: nodes.section) -> tuple[str, str]:
    title = ""
    parts: list[str] = []
    for child in section.children:
        if isinstance(child, nodes.title):
            title = child.astext()
        elif isinstance(child, nodes.section):
            continue
        elif isinstance(child, nodes.literal_block):
            lang = child.get("language", "")
            parts.append(f"```{lang}\n{child.astext()}\n```")
        else:
            parts.append(child.astext())
    return title, "\n\n".join(p for p in parts if p.strip())


def _walk_rst_sections(doc: nodes.document) -> list[dict]:
    out: list[dict] = []

    def visit(node: nodes.Element, header_stack: list[str]) -> None:
        if isinstance(node, nodes.section):
            title, body = _section_to_text(node)
            new_stack = header_stack + ([title] if title else [])
            if body.strip():
                out.append({"headers": new_stack, "body": body})
            for child in node.children:
                if isinstance(child, nodes.section):
                    visit(child, new_stack)
        else:
            for child in node.children:
                if isinstance(child, nodes.section):
                    visit(child, header_stack)

    visit(doc, [])
    return out


def chunk_rst(text: str, source_path: str, version_tag: str = "main") -> list[Chunk]:
    try:
        doc = publish_doctree(text, settings_overrides={"report_level": 5, "halt_level": 5})
    except SystemMessage:
        full = text[:5000]
        return [
            Chunk(
                text=full, source_type="doc", source_path=source_path,
                section_headers=[], version_tag=version_tag,
                chunk_id=_make_chunk_id(source_path, [], full),
            )
        ]

    sections = _walk_rst_sections(doc)
    chunks: list[Chunk] = []
    for sec in sections:
        body = sec["body"]
        headers = sec["headers"]
        full = (" > ".join(headers) + "\n\n" + body) if headers else body
        n_tokens = _count_tokens(full)
        if n_tokens < _MIN_TOKENS and chunks:
            chunks[-1].text += "\n\n" + body
            chunks[-1].chunk_id = _make_chunk_id(
                chunks[-1].source_path, chunks[-1].section_headers, chunks[-1].text
            )
            continue
        if n_tokens <= _MAX_TOKENS:
            chunks.append(
                Chunk(
                    text=full, source_type="doc", source_path=source_path,
                    section_headers=headers, version_tag=version_tag,
                    chunk_id=_make_chunk_id(source_path, headers, full),
                )
            )
        else:
            paras = body.split("\n\n")
            current = ""
            for para in paras:
                cand = (current + "\n\n" + para).strip() if current else para
                if _count_tokens(cand) > _MAX_TOKENS and current:
                    header_prefix = " > ".join(headers) + "\n\n" if headers else ""
                    ctext = header_prefix + current
                    chunks.append(
                        Chunk(
                            text=ctext, source_type="doc", source_path=source_path,
                            section_headers=headers, version_tag=version_tag,
                            chunk_id=_make_chunk_id(source_path, headers, ctext),
                        )
                    )
                    current = para
                else:
                    current = cand
            if current:
                header_prefix = " > ".join(headers) + "\n\n" if headers else ""
                ctext = header_prefix + current
                chunks.append(
                    Chunk(
                        text=ctext, source_type="doc", source_path=source_path,
                        section_headers=headers, version_tag=version_tag,
                        chunk_id=_make_chunk_id(source_path, headers, ctext),
                    )
                )
    return chunks


# ---------- issues ----------


def chunk_issue(issue: dict[str, Any]) -> list[Chunk]:
    """Turns a resolved-issue dict into one or two chunks."""
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    answer = issue.get("best_answer") or ""
    n_issue = int(issue["issue_number"])
    src = f"issues/{n_issue}"

    full_text = f"# Issue #{n_issue}: {title}\n\n{body}"
    full_with_answer = full_text + f"\n\n## Maintainer answer\n\n{answer}" if answer else full_text
    total_tokens = _count_tokens(full_with_answer)

    if total_tokens <= _ISSUE_MAX_TOKENS or not answer:
        return [
            Chunk(
                text=full_with_answer, source_type="resolved_issue", source_path=src,
                section_headers=[f"#{n_issue} {title}"],
                chunk_id=_make_issue_id(n_issue, "all"),
            )
        ]
    return [
        Chunk(
            text=full_text, source_type="resolved_issue", source_path=src,
            section_headers=[f"#{n_issue} {title}"],
            chunk_id=_make_issue_id(n_issue, "body"),
        ),
        Chunk(
            text=f"# Maintainer answer for #{n_issue}\n\n{answer}",
            source_type="resolved_issue", source_path=src,
            section_headers=[f"#{n_issue} answer"],
            chunk_id=_make_issue_id(n_issue, "answer"),
        ),
    ]
