"""Structure-aware reStructuredText chunker — same Chunk contract as markdown_chunker.

Pandas docs are written in rst; this module converts an rst file into the same
``Chunk`` units the markdown chunker emits, so the downstream RAG pipeline
(embedding, hybrid retrieval, rerank) is corpus-agnostic.
"""

import hashlib

import tiktoken
from docutils import nodes
from docutils.core import publish_doctree
from docutils.utils import SystemMessage

from app.services.rag.chunker import Chunk

_ENC = tiktoken.get_encoding("cl100k_base")
_MAX_TOKENS = 800
_MIN_TOKENS = 100


def _make_chunk_id(source_path: str, headers: list[str], text: str) -> str:
    """Deterministic chunk_id = sha256(source_path + headers + full body)."""
    key = f"{source_path}|{'>'.join(headers)}|{text}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def _count_tokens(text: str) -> int:
    """Returns the number of tokens in the text using cl100k_base."""
    return len(_ENC.encode(text))


def _section_to_text(section: nodes.section) -> tuple[str, str]:
    """Returns (title, body_text) for one rst section node. Preserves literal blocks."""
    title = ""
    parts: list[str] = []
    for child in section.children:
        if isinstance(child, nodes.title):
            title = child.astext()
        elif isinstance(child, nodes.section):
            # nested sections handled by the recursive walk
            continue
        elif isinstance(child, nodes.literal_block):
            lang = child.get("language", "")
            parts.append(f"```{lang}\n{child.astext()}\n```")
        else:
            parts.append(child.astext())
    return title, "\n\n".join(p for p in parts if p.strip())


def _walk_sections(doc: nodes.document) -> list[dict]:
    """Walks the doctree, returning a flat list of {headers, body} per section."""
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
    """Parses rst into structure-aware chunks. Falls back to one big chunk on parse failure."""
    try:
        # silence docutils warnings about unknown directives (rst-only sphinx extensions)
        doc = publish_doctree(text, settings_overrides={"report_level": 5, "halt_level": 5})
    except SystemMessage:
        # bad rst — emit one chunk so we never silently drop content
        full = text[:5000]
        return [
            Chunk(
                text=full,
                source_type="doc",
                source_path=source_path,
                section_headers=[],
                version_tag=version_tag,
                chunk_id=_make_chunk_id(source_path, [], full),
            )
        ]

    sections = _walk_sections(doc)
    chunks: list[Chunk] = []

    for sec in sections:
        body = sec["body"]
        headers = sec["headers"]
        full = (" > ".join(headers) + "\n\n" + body) if headers else body

        n_tokens = _count_tokens(full)
        if n_tokens < _MIN_TOKENS:
            # attach tiny sections to the previous chunk to avoid noise
            if chunks:
                chunks[-1].text += "\n\n" + body
                chunks[-1].chunk_id = _make_chunk_id(
                    chunks[-1].source_path, chunks[-1].section_headers, chunks[-1].text
                )
                continue
        if n_tokens <= _MAX_TOKENS:
            chunks.append(
                Chunk(
                    text=full,
                    source_type="doc",
                    source_path=source_path,
                    section_headers=headers,
                    version_tag=version_tag,
                    chunk_id=_make_chunk_id(source_path, headers, full),
                )
            )
        else:
            # split oversized sections on paragraph boundaries with overlap
            paras = body.split("\n\n")
            current = ""
            for para in paras:
                cand = (current + "\n\n" + para).strip() if current else para
                if _count_tokens(cand) > _MAX_TOKENS and current:
                    header_prefix = " > ".join(headers) + "\n\n" if headers else ""
                    chunk_text = header_prefix + current
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            source_type="doc",
                            source_path=source_path,
                            section_headers=headers,
                            version_tag=version_tag,
                            chunk_id=_make_chunk_id(source_path, headers, chunk_text),
                        )
                    )
                    current = para
                else:
                    current = cand
            if current:
                header_prefix = " > ".join(headers) + "\n\n" if headers else ""
                chunk_text = header_prefix + current
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        source_type="doc",
                        source_path=source_path,
                        section_headers=headers,
                        version_tag=version_tag,
                        chunk_id=_make_chunk_id(source_path, headers, chunk_text),
                    )
                )

    return chunks
