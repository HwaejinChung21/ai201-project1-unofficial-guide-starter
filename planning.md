# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

I chose dining options at Washington University in St. Louis, because it is something that I personally would use as an incoming transfer student. I suspect the dining experience as a student at WashU will be much different than that of Oberlin, where the school and town are much smaller and thus the options are more limited. At WashU, there seem to a greater variety of dining options throughout campus as well as many restaurants in St. Louis, and I felt that it would be nice to have all of this information in one place instead of having to dig through multiple different sources about the "best dining halls" or "best restaurants" at/around WashU/St. Louis.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | WashU Dining Services | Useful for broad campus dining structure, locations, and official dining categories. | https://washudining.sodexomyway.com/en-us/
| 2 | WashU Undergraduate Admissions | Useful for a student-facing overview of campus dining and notable locations. | https://admissions.washu.edu/life-at-washu/dining-services/ |
| 3 | WashU Dining Services | Useful for detailed station-by-station listings, grab-and-go items, and hours-style information. | https://diningservices.wustl.edu/items/ |
| 4 | Reddit | Useful for advice on meal plan options. | https://www.reddit.com/r/washu/comments/4a76i0/what_is_the_best_plan_for_meal_plan_and_bear_bucks/ |
| 5 | WashU HR dining on campus page | Useful for institutional language about dining quality, dietary options, and campus food values | https://hr.wustl.edu/items/dining-on-campus/ |
| 6 | WashU “Where to Eat” guide | Useful for a more descriptive campus dining guide with hours and specific venues. | https://mii.wustl.edu/2019-mii-conference/where-to-eat/ |
| 7 | WashU Dis-Orientation Guide food page | Useful as an unofficial student-oriented source for food recommendations and local context. | https://sites.wustl.edu/diso2025-26/items/type/life-in-stl/food/ |
| 8 | Reddit | Good for off-campus restaurant recommendations from students. | https://www.reddit.com/r/washu/comments/l90tqi/what_is_your_favorite_restaurant_near_campus/ |
| 9 | Reddit |Good for broad student impressions of dining variety, hours, and on-campus options. |https://www.reddit.com/r/washu/comments/ok61h3/whats_the_food_situation_like_at_washu/ |
| 10 | WashU campus restaurant list / local campus food guide | Useful as an informal campus-oriented article about local restaurants on or near campus. | https://aperiodictable.substack.com/p/back-to-school-with-washington-universitys |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**
~600 char cap, ~200 char floor (merge small list items up to it)

**Overlap:**
100 chars, applied only when a unit exceeds the cap

**Reasoning:**
 review paragraphs run 400–600 chars and are self-contained, so the cap keeps each review intact; lists have tiny items, so the floor merges them into coherent chunks instead of noisy fragments.
---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
all-MiniLM-L6-v2

**Top-k:**
k = 4

**Production tradeoff reflection:**
Since the domain does not require a great depth of knowledge but is rather factual and opinion based, I would not need to consider too much on accuracy. I think using smaller local models like qwen3.5:4b or so would still be feasibile since those models can handel generic tasks pretty well, and since this domain does not require too much reasoning, we don't have to use super advanced API models like GPT 5.5.
---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What are the main on-campus dining locations at WashU, and how are they categorized? | Should list the official dining venues/categories (e.g. dining halls, cafés, grab-and-go). *Verify exact names against Source #1 / #2.* |
| 2 | What grab-and-go or station options are available, and what kind of items do they serve? | Should name specific stations and item types from the station-by-station listing. *Verify against Source #3.* |
| 3 | What off-campus restaurants near WashU do students personally recommend, and why? | Should surface specific restaurants with student opinions/reasons (cuisine, value, vibe). *Verify against Reddit thread #8 / Substack #10.* |
| 4 | What types of cuisine and price ranges are available at restaurants near campus? | Should list cuisine categories and relative price levels for nearby venues. *Verify against OpenTable #9.* |
| 5 | How does WashU describe its dietary accommodations and food quality values? | Should reflect institutional language on dietary options (e.g. allergen/vegetarian) and food values. *Verify against #5 / #4.* |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. The llm goes beyond the distance range when searching for off campus restauarants

2. Not enough opinionated sources causes llm to hallucinate about restaurant recommendations or doesn't provide enough variety

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

loading chunks from ingestion pipeline, embedding with all-MiniLM-L6-v2, storing in ChromaDB with source metadata

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

I will use Claude for my chunking strategy section and ask it to implement chunk_text()

I will use Claude for similarity search and sort query results from lowest to highest similarity scores




**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
