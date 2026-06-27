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
| [**ProSE**](ProSE/) — Professional Services Extractor | Scans Hawaii procurement sources (HANDS + HiePRO) for active solicitations matching your keywords, records them into a styled Excel spreadsheet with full contact details, and emails it on a schedule. Includes a local web dashboard. | ✅ v0.1.0 |
| _(more to come)_ | | |

## How it fits together

```
                 ┌────────────────────────────────────────────┐
   Procurement   │  ProSE  — discover + extract + track + email │
   sources  ───▶ │  (HANDS / HiePRO  →  Excel  →  scheduled mail)│
                 └────────────────────────────────────────────┘
                                      │
                                      ▼
                        (future programs build on the
                         tracked opportunity data)
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
└── ProSE/               ← Professional Services Extractor
    ├── README.md
    ├── CHANGELOG.md
    └── …
```

## License

Released under the [MIT License](LICENSE).
