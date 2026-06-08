"""Milestone 4 — Embedding and retrieval.

Loads the chunks produced by ingest.py (chunks.json), embeds them locally with
all-MiniLM-L6-v2, stores them in a persistent ChromaDB collection with source
metadata, and exposes a top-k retrieval function for the generation milestone.

    python retrieve.py                 # build / refresh the vector index
    python retrieve.py "your query"    # build if needed, then retrieve top-k

Or import retrieve() / build_index() into the generation pipeline.
"""

import json
import re
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "washu_dining"
CHROMA_DIR = str(Path(__file__).parent / "chroma_db")
CHUNKS_FILE = Path(__file__).parent / "chunks.json"
DEFAULT_K = 5
# Off-topic guard: off-topic queries score <=0.23, on-topic hits >=0.39.
DEFAULT_MIN_SIMILARITY = 0.30
# Hybrid re-ranking: pull a wider semantic candidate pool, then boost candidates
# whose text lexically matches query terms. This rescues entity/enumeration
# queries (e.g. a building name) where the embedding alone under-weights a rare
# proper noun. Boost is added to the cosine similarity before the top-k cut.
CANDIDATE_POOL = 25
KEYWORD_BOOST = 0.15
_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "is",
    "are", "was", "were", "be", "what", "which", "who", "how", "do", "does",
    "list", "all", "any", "some", "with", "that", "this", "there", "near",
    "me", "my", "i", "you", "it", "its", "can", "give",
}
_WORD_RE = re.compile(r"[a-z0-9']+")

_model = None
_collection = None


def get_model():
    """Return a cached SentenceTransformer instance (loaded once per process)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_collection():
    """Return the persistent ChromaDB collection (cosine space)."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def build_index():
    """Load chunks.json, embed every chunk, and upsert into ChromaDB."""
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"{CHUNKS_FILE.name} not found — run `python ingest.py` first."
        )

    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    if not chunks:
        raise ValueError(f"{CHUNKS_FILE.name} is empty — re-run `python ingest.py`.")

    model = get_model()
    embeddings = model.encode(
        [c["text"] for c in chunks],
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    collection = get_collection()
    # Upsert keyed on the stable chunk id, so re-running never duplicates.
    collection.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings.tolist(),
        documents=[c["text"] for c in chunks],
        metadatas=[
            {"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks
        ],
    )
    print(f"Stored {collection.count()} chunks in ChromaDB collection "
          f"'{COLLECTION_NAME}' at {CHROMA_DIR}")
    return collection


def _keyword_terms(text):
    """Content words of a string: lowercased tokens minus stopwords/short words."""
    return {w for w in _WORD_RE.findall(text.lower())
            if len(w) > 2 and w not in _STOPWORDS}


def retrieve(query, k=DEFAULT_K, min_similarity=DEFAULT_MIN_SIMILARITY,
             keyword_boost=True):
    """Return the top-k most relevant chunks for a query, most-relevant-first.

    Each result is a dict with the chunk text and its source attribution:
        {"text", "source", "chunk_index", "distance", "similarity", "score"}
    `similarity` is 1 - cosine distance (1.0 = identical, 0.0 = orthogonal).
    `score` is the rank key: similarity plus a keyword-overlap boost (so a chunk
    that lexically matches query terms — e.g. a building name — can outrank a
    semantically-generic chunk). Set `keyword_boost=False` for pure semantic rank.

    The `min_similarity` cutoff is applied to the (un-boosted) cosine similarity,
    preserving the off-topic guard; an off-topic query still returns fewer than k
    results (or none). Pass `min_similarity=None` to disable that filter.
    """
    collection = get_collection()
    query_embedding = get_model().encode([query], normalize_embeddings=True)

    # Pull a wide candidate pool so re-ranking can surface keyword matches that
    # the embedding alone ranked just outside the top-k.
    pool = max(k, CANDIDATE_POOL) if keyword_boost else k
    result = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=pool,
        include=["documents", "metadatas", "distances"],
    )

    query_terms = _keyword_terms(query) if keyword_boost else set()

    hits = []
    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        similarity = 1.0 - dist
        if min_similarity is not None and similarity < min_similarity:
            continue
        # Fraction of query content words present in the chunk → boost.
        overlap = 0.0
        if query_terms:
            doc_terms = _keyword_terms(doc)
            overlap = len(query_terms & doc_terms) / len(query_terms)
        hits.append({
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
            "similarity": similarity,
            "score": similarity + KEYWORD_BOOST * overlap,
        })

    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:k]


def main():
    args = sys.argv[1:]

    if not args:
        build_index()
        return

    query = " ".join(args)
    collection = get_collection()
    if collection.count() == 0:
        print("Index is empty — building it first...\n")
        build_index()

    hits = retrieve(query)
    print(f"\nQuery: {query}\n" + "=" * 70)
    if not hits:
        print(f"\nNo chunks passed the similarity threshold "
              f"({DEFAULT_MIN_SIMILARITY:.2f}) — off-topic query?")
        return
    for rank, hit in enumerate(hits, 1):
        preview = " ".join(hit["text"].split())
        if len(preview) > 240:
            preview = preview[:240] + "..."
        print(f"\n[{rank}] similarity {hit['similarity']:.3f}  "
              f"— {hit['source']} (#{hit['chunk_index']})")
        print(f"    {preview}")


if __name__ == "__main__":
    main()
