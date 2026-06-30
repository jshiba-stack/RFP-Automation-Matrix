# Phase 6 (planned) — LLM requirements check against any solicitation's guideline PDF

**Status: design only — not built.** This documents the planned approach so we can
build it deliberately later.

## Why this exists

The deterministic `notice.py` parser is hand-tuned to the City & County **annual ad**
(departments, lettered categories, fiscal year). It does not generalize: every bidding
opportunity publishes its *own* requirements PDF —

- **HANDS-listed** opportunities (general info on HANDS): a downloadable PDF under **"Files."**
- **HiePRO-exported** opportunities: a downloadable PDF under **"Attachments."**

…and each has a different layout. To verify a final product against *that specific*
opportunity's requirements, we need a model that can **read an arbitrary PDF** and compare
it to our draft — not a per-format regex. That's an LLM job.

## Backend decision: local Ollama (default), pluggable

| Option | Verdict |
|---|---|
| **Claude Pro/Max plan** | ❌ Not usable. The subscription powers claude.ai + Claude Code, **not** programmatic API access. A custom app needs separate pay-as-you-go API credits. |
| **Claude API (Opus 4.8)** | ✅ Highest quality, native PDF reading. ❌ Per-run cost (~$0.15–0.30/check) + API key + sends confidential docs off-machine. Keep as an *optional* swappable backend. |
| **Ollama (local)** | ✅ **Default.** No key, no per-run cost, and — most important — **nothing leaves the machine** (these are confidential submittals/resumes/client refs, same privacy concern as SharePoint). ❌ Less capable than Opus 4.8; needs adequate RAM/VRAM. |

**Design for a pluggable backend** so we start on Ollama and could swap in the Claude API
later without rearchitecting.

## How the PDF gets in (v1)

**Manual drop** (matches current habit): download the opportunity's *Files*/*Attachments*
PDF and put it in the active source folder. ProPosal already discovers PDFs there
(`discovery.find_notice_pdf` can be generalized). **Auto-downloading** the attachment
straight from HANDS/HiePRO is a separate, more brittle follow-on (reverse-engineering each
site's attachment URL via ProSE's access) — defer until the LLM check is proven.

## Architecture

New module `proposal/llmcheck.py`, plus a small backend abstraction:

```
proposal/llm/
  __init__.py
  base.py        # LLMBackend: .complete(prompt, *, json=True) -> str
  ollama.py      # OllamaBackend  (POST http://localhost:11434/api/chat, format=json)
  # api.py       # (future) ClaudeBackend — optional, swappable
proposal/llmcheck.py   # orchestration -> ChecklistReport
```

### Pipeline (`validate_against_requirements`)
1. **Extract requirements text** from the PDF with `pdfplumber` (already a dependency).
2. **Extract draft text + structure** from the `.docx` using the existing
   `docx_edit.para_text` / section anchors (headings, Capacity table, etc.).
3. **Pull store facts** (`opportunity`: department, fiscal year, selected categories,
   required form, page limit) for the model to check against.
4. **Prompt** the model to (a) extract the discrete requirements from the PDF and
   (b) judge each against the draft + store, returning **strict JSON**:
   ```json
   {"checks":[{"name":"Fiscal year matches","status":"PASS|WARN|FAIL","detail":"..."}, ...]}
   ```
   Use Ollama's `format: "json"` (or `format` = a JSON schema on newer Ollama) to force
   parseable output; validate and coerce to our `checks.ChecklistReport`.
5. **Render** with the existing checklist UI (reuse `checks.py`), clearly labeled as an
   **AI review** (flag-only, may err — never auto-fixes). Show the model's per-item detail.

### Backend (Ollama) specifics
- Talk to the local daemon (`ollama` Python package or raw `requests` to `/api/chat`).
- **Model:** a mid-size instruct model with solid long-context and JSON adherence —
  candidates: `qwen2.5:14b-instruct` (good reasoning/JSON), `llama3.1:8b` (lighter).
  Recommend starting at the largest the user's hardware runs comfortably.
- **Context length:** requirements PDFs can be long (the annual ad ≈ 22 pages). Set
  `num_ctx` generously (e.g. 16k–32k) and, if a PDF still overflows, **chunk** the
  requirements (extract per-section) and merge per-chunk findings.
- **Determinism:** low temperature; the check is advisory, so minor variance is fine.

### Config (`instance/config.json`)
```json
"llm": {
  "enabled": false,
  "backend": "ollama",
  "model": "qwen2.5:14b-instruct",
  "host": "http://localhost:11434",
  "num_ctx": 16384
}
```

### Triggers (manual only)
- CLI: `python -m proposal validate --llm [--requirements <pdf>] [--draft <docx>]`
- Dashboard: an **"AI requirements review"** button on the validate card; runs only on
  click (no background cost), renders results inline like the other checklists.

## Setup (for the README, when built)
1. Install Ollama (ollama.com), then `ollama pull qwen2.5:14b-instruct`.
2. `pip install ollama` (add to requirements only when this phase is built).
3. Enable in the dashboard settings; click **AI requirements review**.

## Risks / open questions
- **Hardware.** 14b needs ~10–12 GB RAM/VRAM; fall back to 8b on lighter machines.
- **Capability gap.** Local models miss subtler requirements vs Opus 4.8 — keep it
  advisory and keep the deterministic checks (`compliance.py`, `notice.py`) as the
  backbone; the LLM is an *additional* net, not a replacement.
- **JSON reliability.** Enforce with `format=json` + a validate/repair step; on parse
  failure, surface the raw model text as a single WARN rather than crashing.
- **Long PDFs.** Chunking strategy above; measure on the real annual ad first.
- **Auto-download (future).** Pulling Files/Attachments straight from HANDS/HiePRO is a
  separate phase that reuses ProSE's site access.

## Build order (when greenlit)
1. `llm/base.py` + `llm/ollama.py` (+ a tiny smoke test against a running daemon).
2. `llmcheck.py` pipeline → `ChecklistReport`, tested on the FY2026 annual ad + a draft.
3. CLI `validate --llm`; then the dashboard button.
4. (Later) generalize PDF discovery to any requirements doc; then auto-download research.
