# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv sync --group dev

# Run full pipeline (generate + ETL)
uv run run_all.py --count 20 --theme "electric vehicles"
uv run run_all.py --count 30 --theme "healthcare policy" --languages "English,Mandarin,Spanish"

# Run ETL only (requires existing data/posts.jsonl)
uv run main.py --theme "electric vehicles"

# Run generation only
uv run generate.py --count 10 --theme "general social media"

# Tests
uv run pytest
uv run pytest tests/test_extract.py   # single file
```

## Prerequisites

Ollama must be running locally with the model pulled:
```bash
ollama pull llama3.1:8b
ollama serve
```

## Architecture

The pipeline has four stages, each in `pipeline/`:

1. **Generate** (`pipeline/generate.py`) — LLM generates synthetic social media posts → `data/posts.jsonl`. Uses Ollama with Pydantic schemas via the `format` parameter for structured output (not prompt-engineered JSON).

2. **Extract** (`pipeline/extract.py`) — Reads `data/posts.jsonl` line-by-line into memory.

3. **Transform** (`pipeline/transform.py`) — Map→Reduce pattern:
   - **Map:** Each post tagged independently with `topic`, `sentiment`, and `language` (handles context window limits, allows incremental processing)
   - **Reduce:** Free-form topic labels consolidated into canonical clusters via LLM (mirrors real-world terminology variance), then sentiment aggregated per cluster, then each cluster gets a 2–3 sentence summary

4. **Load** (`pipeline/load.py`) — Renders `templates/report.html` (Jinja2) → `output/report_<YYYYMMDD_HHMMSS>.html`

Entry points: `run_all.py` (all stages), `main.py` (ETL only), `generate.py` (generation only).

## Key Design Decisions

- **Model:** `llama3.1:8b` via Ollama — fits in 16GB VRAM, fast, swappable via one-line config change.
- **Multilingual:** Posts preserved in source language; topic labels and summaries always output in English; language detection surfaced in report.
- **No linting/type-checking configured** — tests are the sole CI validation gate.
- `data/` and `output/` are git-ignored; `examples/` contains reference samples.
