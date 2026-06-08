"""Milestone 3 — Document ingestion and chunking.

Loads every .txt file in documents/, cleans source-specific noise, and splits
each document into chunks matching the strategy in planning.md:

    ~600 char cap, ~200 char floor (merge small units up),
    100-char overlap applied only when a single unit exceeds the cap.

Run directly to (re)generate chunks.json for the embedding milestone:

    python ingest.py

Or import chunk_text() / clean_text() into the embedding pipeline.
"""

import json
import re
import statistics
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "documents"
OUTPUT_FILE = Path(__file__).parent / "chunks.json"

MAX_CHARS = 600
MIN_CHARS = 200
OVERLAP = 100

# Full lines (after strip, case-insensitive) that are pure source noise.
_NOISE_LINE_EXACT = {
    "op",
    "subscribe",
    "subscribesign in",
    "sign in",
    "share",
    "abouttoggle menu",
    "toggle menu",
    "what's open now",
    "what’s open now",
}

# Line-level noise patterns: lone vote counts, bare bullets, relative
# timestamps ("10y ago", "3 mo ago"), and "u/<user> avatar" lines.
_NOISE_LINE_PATTERNS = [
    re.compile(r"^\d+$"),
    re.compile(r"^[•·]+$"),
    re.compile(r"^\d+\s*(y|yr|mo|mon|d|h|m)\s*ago$", re.IGNORECASE),
    re.compile(r"avatar$", re.IGNORECASE),
]

# Inline "| photo by ..." caption, up to the next sentence end or newline.
_PHOTO_CAPTION = re.compile(r"\s*\|\s*photo by[^.\n]*\.?", re.IGNORECASE)

_UNICODE_MAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ", "…": "...",
}


def clean_text(text):
    """Normalize unicode and strip source noise (moderate aggressiveness)."""
    for src, dst in _UNICODE_MAP.items():
        text = text.replace(src, dst)

    text = _PHOTO_CAPTION.sub("", text)

    kept = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered in _NOISE_LINE_EXACT:
            continue
        if any(p.search(stripped) for p in _NOISE_LINE_PATTERNS):
            continue
        kept.append(line)

    text = "\n".join(kept)
    # Collapse 3+ blank lines down to a single blank line.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_units(text):
    """Split text into units: paragraphs first, then single lines.

    Paragraph boundaries (blank lines) keep prose together; the newline
    fallback makes each list item its own unit so the floor can merge them.
    """
    units = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        for line in block.split("\n"):
            line = line.strip()
            if line:
                units.append(line)
    return units


def _window(unit, max_chars, overlap, min_chars):
    """Slide a max_chars window over an oversize unit with the given overlap.

    A trailing remainder shorter than min_chars is absorbed into its window
    instead of being emitted as a tiny fragment.
    """
    step = max_chars - overlap
    pieces = []
    start = 0
    n = len(unit)
    while start < n:
        end = min(start + max_chars, n)
        if n - end < min_chars:  # absorb a too-small tail into this window
            end = n
        pieces.append(unit[start:end])
        if end == n:
            break
        start += step
    return pieces


def chunk_text(text, max_chars=MAX_CHARS, min_chars=MIN_CHARS, overlap=OVERLAP):
    """Split cleaned text into chunks per the planning.md strategy."""
    chunks = []
    buffer = ""

    for unit in _split_units(text):
        if len(unit) > max_chars:
            # Oversize unit. A small leading buffer (e.g. a section heading and
            # attribution line) is prepended so its topic label stays attached
            # to the content; a larger buffer is flushed as its own chunk.
            if buffer and len(buffer) < min_chars:
                unit = buffer + " " + unit
                buffer = ""
            elif buffer:
                chunks.append(buffer)
                buffer = ""
            # Sliding-window split — the only place overlap applies.
            chunks.extend(_window(unit, max_chars, overlap, min_chars))
            continue

        if not buffer:
            buffer = unit
        elif len(buffer) + 1 + len(unit) <= max_chars:
            buffer = buffer + " " + unit
        elif len(buffer) < min_chars:
            # Small heading-like buffer that doesn't fit with this unit: keep it
            # attached anyway, splitting with overlap if the result is oversize.
            chunks.extend(_window(buffer + " " + unit, max_chars, overlap, min_chars))
            buffer = ""
        else:
            chunks.append(buffer)
            buffer = unit

    if buffer:
        chunks.append(buffer)

    # Floor: merge a too-small trailing chunk back into the previous one.
    if len(chunks) > 1 and len(chunks[-1]) < min_chars:
        chunks[-2] = chunks[-2] + " " + chunks[-1]
        chunks.pop()

    return chunks


def load_documents(docs_dir=DOCS_DIR):
    """Yield (filename, raw_text) for each .txt file, sorted by name."""
    docs = []
    for path in sorted(docs_dir.glob("*.txt")):
        docs.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
    return docs


def main():
    records = []
    per_file = {}

    for filename, raw in load_documents():
        stem = Path(filename).stem
        chunks = chunk_text(clean_text(raw))
        per_file[filename] = len(chunks)
        for i, chunk in enumerate(chunks):
            records.append({
                "id": f"{stem}_{i}",
                "source": filename,
                "chunk_index": i,
                "text": chunk,
                "char_count": len(chunk),
            })

    OUTPUT_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Summary.
    print(f"{'Source':<48} {'Chunks':>6}")
    print("-" * 56)
    for filename in sorted(per_file):
        print(f"{filename:<48} {per_file[filename]:>6}")
    print("-" * 56)
    print(f"{'TOTAL':<48} {len(records):>6}")

    if records:
        lengths = [r["char_count"] for r in records]
        print(
            f"\nChunk length — min {min(lengths)}, "
            f"median {int(statistics.median(lengths))}, max {max(lengths)}"
        )
    print(f"\nWrote {len(records)} chunks to {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
