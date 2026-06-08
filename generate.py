"""Milestone 5 — Grounded generation.

Takes a user question, retrieves grounded context with retrieve.py, and asks
Groq's llama-3.3-70b-versatile to answer using ONLY the retrieved documents,
returning the answer plus a source list for attribution.

    python generate.py "your question"

Or import answer_question() into the Gradio interface (app.py).
"""

import os

from dotenv import load_dotenv
from groq import Groq

from retrieve import retrieve, DEFAULT_K

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
FALLBACK = "I don't have enough information on that."

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about dining at Washington "
    "University in St. Louis. Answer the question using ONLY the information in the "
    "provided documents. If the documents don't contain enough information to answer, "
    f"say '{FALLBACK}' Do not use any outside knowledge."
)

_client = None


def get_client():
    """Return a cached Groq client, with a clear error if the key is missing."""
    global _client
    if _client is None:
        key = os.environ.get("GROQ_API_KEY")
        if not key or key == "your_key_here":
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
                "Groq API key (https://console.groq.com)."
            )
        _client = Groq(api_key=key)
    return _client


def format_context(hits):
    """Render retrieved chunks as numbered, source-labeled context blocks."""
    blocks = []
    for i, hit in enumerate(hits, 1):
        blocks.append(
            f"[{i}] (source: {hit['source']} #{hit['chunk_index']})\n{hit['text']}"
        )
    return "\n\n".join(blocks)


def format_sources(hits):
    """Dedupe hits by source file (relevance order preserved), grouping chunk ids."""
    grouped = {}
    for hit in hits:
        grouped.setdefault(hit["source"], []).append(hit["chunk_index"])
    sources = []
    for source, indices in grouped.items():
        sources.append({"source": source, "chunk_indices": indices})
    return sources


def answer_question(query, k=DEFAULT_K):
    """Answer a question grounded in retrieved documents.

    Returns {"answer": str, "sources": [{"source", "chunk_indices"}]}. If retrieval
    finds nothing relevant (e.g. an off-topic query), returns the grounded fallback
    without calling the LLM.
    """
    hits = retrieve(query, k=k)
    if not hits:
        return {"answer": FALLBACK, "sources": []}

    user_message = (
        f"Documents:\n{format_context(hits)}\n\n"
        f"Question: {query}"
    )

    response = get_client().chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    answer = response.choices[0].message.content.strip()
    return {"answer": answer, "sources": format_sources(hits)}


def _format_sources_text(sources):
    if not sources:
        return ""
    lines = ["\nSources:"]
    for s in sources:
        ids = ", ".join(f"#{i}" for i in s["chunk_indices"])
        label = "chunks" if len(s["chunk_indices"]) > 1 else "chunk"
        lines.append(f"- {s['source']} ({label} {ids})")
    return "\n".join(lines)


def main():
    import sys

    if len(sys.argv) < 2:
        print('Usage: python generate.py "your question"')
        return
    query = " ".join(sys.argv[1:])
    result = answer_question(query)
    print(result["answer"])
    print(_format_sources_text(result["sources"]))


if __name__ == "__main__":
    main()
