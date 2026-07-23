# RFP Automation Matrix

A suite of small, focused programs that automate the **RFP / professional‑services
procurement workflow** — from discovering relevant solicitations, to tracking
them, to getting the right information in front of the right people.

Each program is self‑contained: its own folder, its own `README.md`, its own
`CHANGELOG.md`, and its own version. They can be run independently, but together
they form an end‑to‑end pipeline for finding and acting on procurement
opportunities.

## Programs

| Program | What it does | Status |
|---------|--------------|--------|
| [**ProSE**](ProSE/) — Professional Services Extractor | Scans Hawaii procurement sources (HANDS + HiePRO) for active solicitations matching your keywords, records them into a styled Excel spreadsheet with full contact details, and emails it on a schedule. Each row records the keyword(s) it matched; expired solicitations are struck through and sunk to the bottom; rows auto-fit their contents; and your own cell borders and column widths survive every scan. Runs as a **shared workbook** on a synced SharePoint/OneDrive folder so the tool and a human collaborator maintain one document: only the data columns are refreshed, the action columns are never touched, rows de-duplicate on a stable key (immune to amendment suffixes), the key column can be locked against accidental edits, and a scan skips rather than fighting a file someone has open. Local web dashboard plus OS-level scheduling. | ✅ v0.5.0 |
| [**ProPosal**](ProPosal/) — Professional Services Proposal Builder | Builds the City & County of Honolulu annual submittal end-to-end. Import Sections I–IV from any previous FINAL `.docx` into dashboard editors, edit/reorder there, then Build syncs the content back (preserving formatting, or a strict rebuild) and **assembles the deliverable PDF** — Word-exported body plus each person's one-page resume PDF in order. Auto-refreshes fiscal year / dates, classifies Section I against the current-year DIT taxonomy, enforces document-wide table / pagination / letterhead / resume-typography standards, lints and (optionally) re-typesets damaged resume pages, runs a compliance checklist + format check, and validates against the City's annual notice PDF. Local web dashboard, plus a PDF form-fill framework (DPW-120 today; SF330 pending a fillable template). | 🚧 v0.16.1 |
| _(more to come)_ | | |

## How it fits together

```
                 ┌────────────────────────────────────────────┐
   Procurement   │  ProSE  — discover + extract + track + email │
   sources  ───▶ │  (HANDS / HiePRO  →  Excel  →  scheduled mail)│
                 └────────────────────────────────────────────┘
                                      │
                                      ▼
                 ┌────────────────────────────────────────────┐
   Pursue a      │  ProPosal — build + refresh the submittal     │
   shortlisted ▶ │  (last year's FINAL .docx  →  updated draft  │
   opportunity   │   + flags;  data store  →  generate)         │
                 └────────────────────────────────────────────┘
```

## Conventions

- **One folder per program.** Each is independently runnable and versioned.
- **Per‑program docs.** Every program has a `README.md` (what it is + how to run)
  and a `CHANGELOG.md` (version history, *Keep a Changelog* style).
- **Secrets stay local.** Credentials, tokens, `.env` files, personal settings
  (`config.json`), and any generated data (spreadsheets with real contacts) are
  git‑ignored and never committed.
- **Python‑based** where applicable; each program manages its own virtual
  environment (`.venv`) and `requirements.txt`.

## Getting started

Pick a program and follow its README. For ProSE:

```bash
cd ProSE
# Windows: just double-click start.bat (creates the venv on first run)
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m prose
```

## Repository layout

```
RFP Automation Matrix/
├── README.md            ← this file (suite overview)
├── CHANGELOG.md         ← suite-level milestones (programs added/retired)
├── LICENSE              ← MIT
├── docs/                ← project context, decisions, plans, reference
│   ├── context/         ← current-state (what is true now)
│   ├── decisions/       ← accepted decisions + rationale
│   └── highlights/      ← public career layer (case studies per program)
├── ProSE/               ← Professional Services Extractor
│   ├── README.md
│   ├── CHANGELOG.md
│   └── …
└── ProPosal/             ← Professional Services Proposal Builder
    ├── README.md
    ├── CHANGELOG.md
    └── …
```

Working notes (`docs/sessions/`, `docs/audits/`) stay local and are git-ignored,
so nothing containing real contact or client data reaches this public repo.

## License

Released under the [MIT License](LICENSE).
