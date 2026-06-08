# The Unofficial Guide — Project 1

A retrieval-augmented (RAG) question-answering system about **dining at Washington
University in St. Louis (WashU)**. It ingests and chunks a corpus of official and
student-sourced documents, embeds them locally, retrieves the most relevant chunks for a
question, and has an LLM answer **using only the retrieved text**, with source attribution.

**Pipeline:** `ingest.py` (clean + chunk → `chunks.json`) → `retrieve.py` (embed + ChromaDB
vector store + hybrid retrieval) → `generate.py` (grounded Groq generation) → `app.py`
(Gradio web UI).

---

## Domain

Dining options at and around WashU — on-campus dining halls, cafés, grab-and-go stations,
meal plans, and off-campus restaurants in St. Louis. This is valuable because the information
is scattered: official dining pages list venues and meal-point mechanics, but the *student*
perspective (which restaurants are actually worth it, how meal points really work, what the
vibe of a café is) lives in Reddit threads, a student newspaper, and local food blogs. As an
incoming transfer student, having all of it answerable in one place — instead of digging
through a dozen sources — is the point.

---

## Document Sources

10 documents collected into [documents/](documents/), spanning official, student, and local
perspectives:

| # | File | Source | Type | URL |
|---|------|--------|------|-----|
| 1 | `WashU_Dining.txt` | WashU Dining Services (Sodexo) | Official | https://washudining.sodexomyway.com/en-us/ |
| 2 | `WashU_Dining_2.txt` | WashU Dining Services — venue/items listing | Official | https://diningservices.wustl.edu/items/ |
| 3 | `WashU_Undergraduate_Admissions.txt` | WashU Undergraduate Admissions — Dining | Official | https://admissions.washu.edu/life-at-washu/dining-services/ |
| 4 | `WashU_Student_Life.txt` | Student Life (WashU student newspaper) — "A week of eating exploration" | Student journalism | https://www.studlife.com/ |
| 5 | `WashU_Disorientation_Guide_2025_2026.txt` | WashU Dis-Orientation Guide — Food in STL | Unofficial student guide | https://sites.wustl.edu/diso2025-26/items/type/life-in-stl/food/ |
| 6 | `reddit_1.txt` | r/WashU — "Best plan for meal plan and bear bucks?" | Forum | https://www.reddit.com/r/washu/comments/4a76i0/ |
| 7 | `reddit_2.txt` | r/WashU — "Favorite restaurant near campus?" | Forum | https://www.reddit.com/r/washu/comments/l90tqi/ |
| 8 | `reddit_3.txt` | r/WashU — "What's the food situation like at WashU?" | Forum | https://www.reddit.com/r/washu/comments/ok61h3/ |
| 9 | `substack_Shannon_weber.txt` | a periodic table (Shannon Weber) — "Back to school with WashU's new campus restaurants" | Food blog | https://aperiodictable.substack.com/p/back-to-school-with-washington-universitys |
| 10 | `saraswationline_top_10_near_washu.txt` | Saraswati Online — "Top 10 Places to Eat Near WashU" | Local guide | https://saraswationline.com/ |

---

## Chunking Strategy

Implemented in [ingest.py](ingest.py) (`clean_text` + `chunk_text`).

**Chunk size:** ~600-character cap with a ~200-character floor. Units (paragraphs, then
individual lines/list items) are accumulated up toward the cap; small heading/attribution
fragments are merged into the content that follows them so no orphan chunks fall below the
floor.

**Overlap:** 100 characters, applied **only** when a single unit exceeds the 600-char cap and
must be split with a sliding window. Self-contained sub-cap paragraphs are kept intact with no
overlap.

**Preprocessing (`clean_text`):** normalizes unicode (smart quotes, non-breaking spaces) and
strips source noise — Reddit metadata (vote-count lines, bullets, "10y ago" timestamps, "OP",
"u/x avatar"), blog boilerplate (Subscribe / Share / nav menus), and "| photo by …" captions.

**Why these choices fit the documents:** student reviews and Reddit comments run ~400–600
chars and are self-contained, so the cap keeps each one whole. The official WashU guides are
list- and heading-heavy (e.g. a "Barbecue" heading + reviewer attribution + a long review), so
the floor merges those tiny fragments up and keeps the topic label attached to its review for
better retrieval. Overlap is reserved for genuinely long blog paragraphs that must be split,
where it preserves continuity across the cut.

**Final chunk count: 162 chunks** across 10 documents:

| Source | Chunks | Source | Chunks |
|--------|-------:|--------|-------:|
| WashU_Dining.txt | 69 | reddit_1.txt | 12 |
| WashU_Disorientation_Guide_2025_2026.txt | 27 | WashU_Dining_2.txt | 7 |
| WashU_Student_Life.txt | 12 | saraswationline_top_10_near_washu.txt | 9 |
| substack_Shannon_weber.txt | 13 | reddit_2.txt | 5 |
| WashU_Undergraduate_Admissions.txt | 5 | reddit_3.txt | 3 |

Length distribution: min 202, median 541, max 789 characters.

---

## Sample Chunks

Five representative chunks, each labeled with its source document:

**1. `WashU_Dining_0` — source: `WashU_Dining.txt`** (445 chars)
> Bear Bodega Bear's Den Village House Danforth University Center Retail Dining 24/7 Vending
> Meet Our Team Mission "To provide a diverse, high-quality dining experience at WashU that
> fosters community, supports nutrition-forward choices, and enhances the overall student,
> faculty, and staff experience. We are committed to offering fresh, sustainable meals that
> nourish both body and mind, while embracing the rich diversity of our campus." Vision

**2. `reddit_2_1` — source: `reddit_2.txt`** (506 chars)
> …Fozzie's is where it's at!! schnebly5 Damn I graduated in 19 and never went there izlanda_
> Sauce on the side!!! Wonderful calzones!!!!! SwagosaurusRex_ Seoul Taco, the bulgogi beef
> burrito is UH-MAZING iEatSponge Best burrito I've had in STL. Amazing. lmlj1000 Three Kings
> on the loop has top tier wings…

**3. `substack_Shannon_weber_2` — source: `substack_Shannon_weber.txt`** (469 chars)
> Washington University in St. Louis. Prior to this year, these locations were populated by
> traditional food service options you're likely to find on many university campuses…The
> departure of the food service company the campus had been utilizing gave WashU an
> opportunity to rethink the dining program at every level…The Fattened Caf in McKelvey Hall.
> The Restaurants

**4. `WashU_Disorientation_Guide_2025_2026_4` — source: `WashU_Disorientation_Guide_2025_2026.txt`** (384 chars)
> …sweet and savory! The waits can be long, but you can order from the coffee bar in the
> meantime, and there is plenty of outdoor seating while you wait! While it is a bit pricier,
> Bowood by Niche offers brunch and lunch options for whatever you might be craving…and they
> truly elevate the classics. Also, you'll have a great time exploring the plant store…

**5. `saraswationline_top_10_near_washu_2` — source: `saraswationline_top_10_near_washu.txt`** (440 chars)
> Salt + Smoke offers delicious smoked meats and comfort sides in a laid-back setting. Its
> hearty plates are ideal for those who want robust flavors without overspending. 5. Fitz's
> Restaurant A classic American diner with a twist, Fitz's is famed for its burgers,
> hand-spun sodas, and nostalgic décor…6. Pi Pizzeria

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, stored in **ChromaDB** with
cosine similarity. It runs locally (no API key, no rate limits), is fast, and its 384-dim
embeddings are more than adequate for a small, factual/opinion corpus.

**Production tradeoff reflection:** If I were deploying this for real users with cost off the
table, I'd weigh:
- **Accuracy on domain-specific text / proper nouns.** This is the model's clearest weakness
  here — MiniLM under-weights rare proper nouns (building names like "McKelvey", restaurant
  names), which hurt recall (see Failure Case). A larger model like `bge-large-en-v1.5` or a
  hosted embedding (e.g. OpenAI `text-embedding-3-large`) would discriminate these better.
- **Context length.** MiniLM truncates at 256 tokens, which is fine for my ~600-char chunks
  but would force re-chunking if I moved to larger passages.
- **Latency vs. quality.** MiniLM is near-instant locally; a hosted model adds a network
  round-trip per query and per chunk at index time.
- **Multilingual support** — not needed for this English corpus, but would matter for a
  broader student body.

Given the domain is factual and opinion-based rather than reasoning-heavy, MiniLM is a
reasonable choice; the main lever for improvement would be embedding quality on names, which I
partially mitigated with hybrid keyword re-ranking rather than swapping the model.

---

## Retrieval

Implemented in [retrieve.py](retrieve.py) (`retrieve()`), top-k = 5. Retrieval is **hybrid**:
it pulls a wide semantic candidate pool from ChromaDB, then re-ranks by
`score = cosine_similarity + 0.15 × (fraction of query content-words found in the chunk)`.
The keyword boost rescues entity/enumeration queries where the embedding alone under-weights a
proper noun. A `min_similarity = 0.30` floor (applied to the *un-boosted* cosine similarity)
acts as an off-topic guard.

### Retrieval test results

**Query A — "How do WashU meal plans and points work?"**
| Rank | Source | Sim |
|---|---|---|
| 1 | WashU_Dining.txt #5 | 0.731 |
| 2 | reddit_1.txt #10 | 0.689 |
| 3 | reddit_1.txt #6 | 0.677 |
| 4 | WashU_Dining.txt #13 | 0.624 |
| 5 | WashU_Dining.txt #4 | 0.622 |

*Why these are relevant:* The top hit (`WashU_Dining #5`) is the official explanation of the
declining-balance meal-points system. Ranks 2–3 are the Reddit thread where students break
down the actual plan tiers and point costs, and rank 4 covers where meal plans are valid.
Together they pair the **official mechanics** with the **student-level practical detail** —
exactly the official + unofficial blend the system is designed to surface.

**Query B — "What dining options are in McKelvey Hall?"**
| Rank | Source | Sim | Score | Venue |
|---|---|---|---|---|
| 1 | WashU_Student_Life.txt #10 | 0.591 | 0.704 | Bytes Café |
| 2 | WashU_Disorientation_Guide_2025_2026.txt #21 | 0.598 | 0.636 | — |
| 3 | WashU_Dining_2.txt #5 | 0.523 | 0.635 | The Fattened Caf |
| 4 | substack_Shannon_weber.txt #2 | 0.482 | 0.632 | The Fattened Caf |
| 5 | WashU_Dining.txt #21 | 0.524 | 0.599 | — |

*Why these are relevant:* McKelvey Hall has two dining venues in the corpus, described in
**different documents** — Bytes Café (Student Life) and The Fattened Caf (WashU_Dining_2 and
the substack blog). By pure cosine similarity the Fattened Caf chunks ranked 6th–7th and were
cut off; the **keyword boost on "McKelvey"** lifted them into the top-4 (their `score` exceeds
their `sim`), so both venues now reach the LLM. This query is the direct motivation for the
hybrid retrieval design.

**Query C — "What off-campus restaurants near WashU do students recommend?"**
| Rank | Source | Sim |
|---|---|---|
| 1 | reddit_3.txt #2 | 0.739 |
| 2 | reddit_3.txt #0 | 0.702 |
| 3 | substack_Shannon_weber.txt #2 | 0.675 |
| 4 | WashU_Dining.txt #1 | 0.683 |
| 5 | reddit_2.txt #0 | 0.710 |

(`reddit_2 #0`, which contains the actual restaurant recommendations, sits at the rank-5
boundary — see Failure Case Analysis for why this is fragile.)

---

## Grounded Generation

Implemented in [generate.py](generate.py). Grounding is enforced at **two layers**:

**1. Pipeline structure (retrieval gate).** Before the LLM is ever called, `answer_question()`
runs `retrieve()`. Because retrieval applies the `min_similarity = 0.30` floor, an off-topic
query returns **zero chunks**, and the function returns the fallback *without calling the LLM
at all*. The model only ever sees chunks that passed the relevance floor, formatted as
explicitly numbered, source-labeled context blocks:
```
[1] (source: WashU_Dining.txt #5)
<chunk text>
```

**2. System prompt instruction.** The model is told:
> *"You are a helpful assistant answering questions about dining at Washington University in
> St. Louis. Answer the question using ONLY the information in the provided documents. If the
> documents don't contain enough information to answer, say 'I don't have enough information on
> that.' Do not use any outside knowledge."*

Generation runs at `temperature=0` for reproducibility.

**How source attribution is surfaced:** `answer_question()` returns the answer plus a `sources`
list built from the retrieved chunks (deduped by file, with chunk indices). The CLI and the
Gradio UI render this as a trailing **Sources** section beneath every answer, so the user can
see exactly which documents grounded the response.

---

## Example Responses

**Example 1 — Q: "What grab-and-go or station options are available, and what kind of items do they serve?"**
> According to the documents, the following grab-and-go or station options are available:
> 1. Paws & Go: Grab & Go options, including Halal items and breakfast options like yogurt
>    parfaits, overnight oats, and bagel & lox.
> 2. Millbrook Market: Grab & Go options, including Halal items…
> 5. Stanley's Sushi & Tea: Grab & Go sushi rolls and made-to-order rolls.
> 8. The Fattened Caf: Smoked meats, rice bowls, bakery items, and a unique coffee menu…
>
> **Sources:**
> - WashU_Dining.txt (chunks #21, #26, #25, #20)
> - WashU_Dining_2.txt (chunk #5)

**Example 2 — Q: "How does WashU describe its dietary accommodations and food quality values?"**
> According to the documents, WashU describes its dietary accommodations and food quality
> values as follows:
> - Prioritizing fresh, locally sourced ingredients to reflect diverse tastes and dietary needs.
> - Offering options for vegetarians, those who require kosher or halal options, and those with
>   food allergies.
> - Designing menus with health and wellness in mind…
> - Committing to sustainable practices and reducing food waste.
>
> **Sources:**
> - WashU_Dining.txt (chunks #1, #16, #2, #42)
> - WashU_Undergraduate_Admissions.txt (chunk #0)

**Out-of-scope query — Q: "What time does the campus library close on Sundays?"**
> I don't have enough information on that. The provided documents do not mention the library's
> hours of operation on Sundays. They do mention Corner 17 at Olin Library, but only describe
> the food options and atmosphere, without providing information about the library's hours.

The system correctly refuses rather than guessing — even though "Olin Library" appears in a
retrieved dining chunk, the system prompt prevents it from fabricating hours.

---

## Query Interface

A **Gradio** web app ([app.py](app.py)), launched with `python app.py`.

**Input field:**
- *Your question* — a multi-line textbox where the user types a dining question. Submit via the
  **Ask** button or by pressing Enter. Five example questions (the evaluation set) are
  provided as one-click chips.

**Output fields:**
- *Answer* — a Markdown panel with the grounded answer (or the "I don't have enough
  information on that." refusal).
- *Sources* — a Markdown panel listing each cited document once, with the contributing chunk
  numbers. Empty for out-of-scope queries.

If `GROQ_API_KEY` is missing, the UI surfaces a friendly ⚠️ message instead of crashing.

**Sample interaction transcript:**
```
User:    What off-campus restaurants near WashU do students personally recommend, and why?

Answer:  According to the provided documents, one off-campus restaurant near WashU that a
         student personally recommends is Fozzie's Sandwich Emporium on Big Bend. The student,
         eBoneSteak, recommends it because they have a large range of inventive sandwiches
         with a solid variety of veggie and meat-based options, and they also serve a style of
         burger called a Juicy Lucy, which the student finds to be "to die for".

Sources: - reddit_3.txt (chunks #2, #0)
         - WashU_Dining.txt (chunk #1)
         - substack_Shannon_weber.txt (chunk #2)
         - reddit_2.txt (chunk #0)   ← the chunk the Fozzie's recommendation came from
```

---

## Evaluation Report

Run against the 5 test questions from [planning.md](planning.md), using the live
`llama-3.3-70b-versatile` model.

| # | Question | Expected answer | System response (summarized) | Retrieval | Accuracy |
|---|----------|-----------------|------------------------------|-----------|----------|
| 1 | Main on-campus dining locations and how they're categorized | Official venues/categories (dining halls, cafés, grab-and-go) | "I don't have enough information" — pulled mission/vision + scattered venue names, not the categorized listing | Off-target | **Inaccurate** |
| 2 | Grab-and-go / station options and items served | Specific stations + item types | Detailed, correct list (Paws & Go, Millbrook, Stanley's Sushi, Fattened Caf, etc.) with items | Relevant | **Accurate** |
| 3 | Off-campus restaurants students recommend, and why | Specific restaurants + student reasons | Names Fozzie's Sandwich Emporium with the student's reasoning (sandwiches, Juicy Lucy) | Partially relevant | **Partially accurate** |
| 4 | Cuisine types and price ranges near campus | Cuisine categories + relative price levels | Lists budget spots (Blueberry Hill, Corner 17, Salt + Smoke), cheap on-campus options, honestly flags missing exact prices | Relevant | **Accurate** |
| 5 | WashU's dietary accommodations and food-quality values | Institutional language on dietary options + values | Comprehensive, grounded summary (vegetarian/kosher/halal/allergen, sustainability, wellness) | Relevant | **Accurate** |

**Summary:** 3 accurate, 1 partially accurate, 1 inaccurate. The system is strong on official,
descriptive content (Q2, Q4, Q5) and the off-topic refusal works correctly. The weaknesses are
in *enumeration* and *aggregation* queries (Q1, Q3), where the answer is spread across many
chunks and the retriever doesn't gather all of them.

---

## Failure Case Analysis

**Question that failed:** Q1 — "What are the main on-campus dining locations at WashU, and how
are they categorized?" (Q3 is a milder version of the same root cause.)

**What the system returned:** "I don't have enough information on that." — followed by sources
that were mostly the dining mission/vision statement (`WashU_Dining #1`), a general "what's the
food situation" Reddit thread (`reddit_3`), and a blog intro (`substack #2`).

**Root cause (retrieval / embedding stage):** This is a *recall + ranking* failure, not a
generation failure — the model answered faithfully given weak context. The query is dominated
by generic semantics ("dining locations", "WashU", "categorized"), which match high-level
mission/overview chunks more strongly than the actual venue listings. The corpus *does* contain
categorized venue lists (`WashU_Dining` chunks ~#20–#26, `WashU_Dining_2`), but with top-k = 5
and all-MiniLM-L6-v2's weak discrimination on this bunched score range, those listing chunks
don't all make the cut. Q3 shows the same fragility from a different angle: the chunk that
actually answers it (`reddit_2 #0`, the "favorite restaurant" thread) sits at the **rank-5
boundary** — it barely makes it in, and because the keyword boost favors chunks matching
"restaurants/WashU/students" (which `reddit_2 #0` phrases as "favorite restaurant near
campus"), it can get edged out entirely. During development this boundary chunk flipped in and
out of the top-k depending on whether `generate.py` used k=4 or k=5.

**What I would change to fix it:** (1) Raise top-k further (8–10) for these "list all"
queries — more recall at the cost of more tokens; (2) add true lexical/BM25 hybrid scoring so
exact venue-name matches are guaranteed to surface, not just boosted; (3) use a stronger
embedding model (`bge-large`) to better separate specific venue chunks from generic
mission/overview text. The cleanest single fix would be query-type-aware retrieval that detects
enumeration questions and widens k automatically.

---

## Spec Reflection

**One way the spec helped me during implementation:** Writing the Chunking Strategy section in
`planning.md` *before* coding forced me to look at the documents' actual shapes first. I'd
specified a ~600-char cap with a ~200-char floor "to merge small list items," and that floor
turned out to be exactly what the WashU Dis-Orientation Guide needed — its structure of a tiny
heading ("Barbecue") + attribution ("Sean H., M1") + a long review would otherwise have
produced useless 20-character orphan chunks. Because the spec named the behavior up front, I
implemented heading-merging deliberately instead of discovering the problem later.

**One way the implementation diverged from the spec, and why:** `planning.md` specified a plain
top-k semantic search with `min_similarity` as the only retrieval refinement. In practice that
failed the McKelvey Hall enumeration test (it returned only one of two venues), so I added a
**hybrid keyword-boost re-ranking** layer that wasn't in the spec. The embedding model
under-weighted the proper noun "McKelvey," and rather than swap models (heavier, also not in
spec), the keyword boost was the lighter fix that surfaced both venues. I also bumped top-k
from the planned 4 to 5 for a bit more recall headroom.

---

## AI Usage

**Instance 1 — Ingestion and chunking**
- *What I gave the AI:* My Documents and Chunking Strategy sections from `planning.md` (the
  ~600-char cap, ~200-char floor, 100-char overlap) plus the raw files in `documents/`.
- *What it produced:* `ingest.py` with `clean_text()` and `chunk_text()`, a paragraph-then-line
  unit splitter, accumulation up to the cap, and sliding-window overlap only for oversize units.
- *What I changed or overrode:* The first version emitted 20–30 char orphan chunks from the
  Dis-Orientation Guide's heading/attribution lines and left sub-floor window remainders. I
  directed it to (a) prepend small heading buffers onto the following content so topic labels
  stay attached, and (b) absorb sub-floor sliding-window tails into the preceding window. That
  took the corpus from 193 noisy chunks to 162 clean ones with no sub-200 orphans.

**Instance 2 — Retrieval debugging (the McKelvey failure)**
- *What I gave the AI:* The bug report ("asked for all dining options in McKelvey Hall, only
  got one") and access to the corpus and `retrieve.py`.
- *What it produced:* A diagnosis showing the second venue (The Fattened Caf) ranked #6–7 by
  pure cosine similarity, just outside top-k, because MiniLM under-weighted the building name;
  it then implemented hybrid keyword-boost re-ranking over a wider candidate pool.
- *What I changed or overrode:* I directed it to keep the `min_similarity` off-topic guard
  applied to the *un-boosted* similarity (so the keyword boost couldn't let off-topic chunks
  leak through), and to verify the fix didn't disturb the existing evaluation queries before
  accepting it.
