# Changelog — RFP Automation Matrix

Suite-level milestones (programs added, retired, or significantly changed).
Each program keeps its own detailed changelog in its folder.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## 2026-07-02

### Added
- **Adopted the tool-neutral `docs/` memory framework** at the suite root
  (context / decisions / plans / sessions / audits / runbooks + a context-contract
  and `CLAUDE.md`/`AGENTS.md` entry points). Authored a rich
  `docs/context/current-state.md` and three decision records (program-suite
  structure, public-repo privacy posture, ProPosal dual-mode build). Working notes
  (`docs/sessions/`, `docs/audits/`) are git-ignored — important since this repo is
  public. `docs/` complements this changelog; it does not replace it.

## 2026-06-30

### Added
- **ProPosal** (Professional Services Proposal Builder) **v0.7.0** — the second
  program in the suite. Builds the City & County of Honolulu annual submittal:
  smart copy-and-update from last year's FINAL, generate-from-data-store (with a
  store extractor), an automatic compliance checklist + format checker, an
  ocean-blue local dashboard sourcing files from OneDrive/SharePoint-synced
  folders, resume cross-verification, validation against the annual notice PDF,
  and a PDF form-fill framework (DPW-120 today; SF330 pending a fillable
  template). See [ProPosal/CHANGELOG.md](ProPosal/CHANGELOG.md).
- Design note for a future, privacy-preserving local-LLM (Ollama) requirements
  check ([ProPosal/docs/phase6-requirements-llm.md](ProPosal/docs/phase6-requirements-llm.md)).

### Changed
- Hardened the root `.gitignore` to keep all business documents (proposals,
  forms, notices, exports) and firm/reference data out of the public repo. The
  bundled example data store and tests use **fictional placeholder data only** —
  no firm, personnel, client, or contact details.

## 2026-06-27

### Added
- **ProSE** (Professional Services Extractor) **v0.1.0** — scans Hawaii
  procurement sources (HANDS + HiePRO) for active solicitations, extracts full
  contact details into a styled Excel spreadsheet, and emails it on a schedule
  via a local dashboard. See [ProSE/CHANGELOG.md](ProSE/CHANGELOG.md).
- Established the suite structure and conventions (one folder per program; each
  with its own README, CHANGELOG, and version; secrets and generated data kept
  local and never committed).
