"""Milestone 5 — Gradio web interface.

A thin front-end over generate.answer_question(): ask a question, get a grounded
answer with a source list.

    python app.py
"""

import gradio as gr

from generate import answer_question

# The 5 evaluation questions from planning.md.
EXAMPLE_QUESTIONS = [
    "What are the main on-campus dining locations at WashU, and how are they categorized?",
    "What grab-and-go or station options are available, and what kind of items do they serve?",
    "What off-campus restaurants near WashU do students personally recommend, and why?",
    "What types of cuisine and price ranges are available at restaurants near campus?",
    "How does WashU describe its dietary accommodations and food quality values?",
]


def _sources_markdown(sources):
    if not sources:
        return ""
    lines = ["### Sources"]
    for s in sources:
        ids = ", ".join(f"#{i}" for i in s["chunk_indices"])
        label = "chunks" if len(s["chunk_indices"]) > 1 else "chunk"
        lines.append(f"- **{s['source']}** ({label} {ids})")
    return "\n".join(lines)


def respond(question):
    if not question or not question.strip():
        return "Please enter a question.", ""
    try:
        result = answer_question(question)
    except RuntimeError as e:  # e.g. missing GROQ_API_KEY
        return f"⚠️ {e}", ""
    return result["answer"], _sources_markdown(result["sources"])


with gr.Blocks(title="WashU Dining — Unofficial Guide") as demo:
    gr.Markdown(
        "# 🍔 WashU Dining — The Unofficial Guide\n"
        "Ask about dining at Washington University in St. Louis. Answers are grounded "
        "only in the collected documents, with sources listed below each answer."
    )
    question = gr.Textbox(
        label="Your question",
        placeholder="e.g. What off-campus restaurants do students recommend?",
        lines=2,
    )
    submit = gr.Button("Ask", variant="primary")
    answer = gr.Markdown(label="Answer")
    sources = gr.Markdown(label="Sources")

    gr.Examples(examples=EXAMPLE_QUESTIONS, inputs=question)

    submit.click(respond, inputs=question, outputs=[answer, sources])
    question.submit(respond, inputs=question, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
