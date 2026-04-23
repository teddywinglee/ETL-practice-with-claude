# Development Notes

This project was built collaboratively with [Claude Code](https://claude.ai/claude-code) (Anthropic's AI coding agent), using it as a hands-on pairing tool throughout — from architecture decisions to implementation and debugging.

The notes below capture design decisions and insights that came out of that process.

---

## Architecture: why per-post tagging instead of one big batch

The transform stage tags each post individually, merges similar topic labels, then summarises each cluster. This mirrors how production social media analytics pipelines are typically structured.

The alternative — feeding all posts to the LLM in one prompt — sounds simpler but breaks down at scale:
- Context windows cap out (especially relevant when this type of system was first built)
- You can't process posts incrementally as new ones arrive
- The same post produces different tags depending on what else is in the batch

The per-post approach is a classic **map → reduce** pattern:
- **Map:** each post gets a topic label + sentiment independently
- **Reduce:** similar labels are merged, then each cluster is summarised

This also makes the pipeline more maintainable — you can swap the LLM, change the tagging prompt, or redefine clusters without reprocessing everything.

---

## Topic merging: free-form labels + a consolidation pass

Rather than giving the LLM a fixed list of allowed topic labels, posts are tagged with free-form labels and a second LLM pass consolidates similar ones (e.g. "EV charging experience", "EV charging convenience", "EV Charging Progress" → "EV Charging").

The constrained approach is more predictable but requires you to know your topics upfront. The free-form + merge approach is closer to how real datasets behave — especially in healthcare or policy topics where language varies widely across sources.

---

## Structured output via Pydantic

All LLM calls that return structured data use the OpenAI `response_format` parameter with a Pydantic schema, rather than prompt-engineering the model to return JSON and then parsing it manually.

The practical difference: `Literal["positive", "neutral", "negative"]` on the sentiment field means the model is *constrained* to those values at the token level — not just instructed. This produced noticeably better results: neutral sentiment tags started appearing where previously the model defaulted to positive for everything.

It also eliminated fragile `find("[")` / `find("{")` parsing hacks that would silently break on edge cases.

---

## Model choice

The model is configured via `MODEL` in `pipeline/config.py` and served through LM Studio's local server. Reasons for keeping models in the 8B range:
- 8B fits comfortably in 16GB VRAM and runs fast
- Summarising social media posts doesn't require frontier-level reasoning
- Larger models running heavily quantised to fit in memory often produce *worse* structured output, not better
- Swapping the model later is a one-line change in `pipeline/config.py`

---

## Multilingual design

For multilingual datasets, the pipeline detects the language of each post and always produces topic labels and summaries in English — keeping the report readable regardless of input language mix.

Original post text is preserved in its source language in the report. Translating source material would be misleading and would obscure the quality of the underlying analysis.

Language detection is surfaced as a metric in the report overview when more than one language is present.

One honest limitation: smaller models typically generate lower quality Mandarin content than English or Spanish. For production use on CJK-heavy datasets, a model with stronger multilingual support (e.g. `qwen2.5`) would be a better fit — and the pipeline is designed to make that swap straightforward via `pipeline/config.py`.

---

## On using an AI coding agent

Claude Code handled scaffolding, first-pass implementations, debugging, and refinement across the full pipeline. The workflow felt less like dictating code and more like pairing with someone who could hold the full context of the project across sessions.

The most valuable moments weren't code generation — they were the architectural discussions: whether to use free-form or constrained topic labels, how to handle multilingual normalisation, whether the demo scope was realistic. Having those conversations grounded in the actual codebase (rather than in the abstract) made the decisions sharper.
