# Skills Matrix: RFP Automation Matrix

Competencies demonstrated in this suite, each tied to concrete evidence a
recruiter or interviewer can check. Use this to map your work onto a job
description quickly, and to pick which [case study](case-studies.md) to tell for a
given prompt.

| Competency | Evidence in this repo | Interview prompt it answers |
| --- | --- | --- |
| Root-cause debugging | Diagnosed elongated PDF text as an editor re-save via per-run scale matrices, after clearing the assumed cause by measurement | "Tell me about a hard bug." |
| Document and PDF engineering | Page-level assembly, glyph-scale linting, template-driven rebuild, header restamping through Word | "Have you worked with a messy real-world format?" |
| Designing for graceful degradation | Optional local LLM behind a deterministic fallback; damaged resumes self-heal or are flagged, never ship silently | "How do you handle unreliable inputs or dependencies?" |
| Pragmatic AI integration | Model is opt-in and off by default; default path is free, offline, and private | "When would you not use an LLM?" |
| Test discipline | 100-plus tests on fictional data in a public repo; outputs verified page-for-page | "How do you know your code works?" |
| Security and privacy | Full git-history privacy audit, leak removal with backup and verification, hardened process | "Have you handled sensitive data?" |
| Concurrency and data integrity | Lock-aware scans, dedup by stable key, non-destructive updates to a shared workbook | "How do you avoid corrupting shared state?" |
| Automation and scheduling | OS task scheduler jobs that survive reboots and run without the app open, with a kill switch | "Have you built something that runs unattended?" |
| Product and stakeholder thinking | Automation built around a real procurement workflow; human action columns and formatting treated as a hard constraint | "How do you design for real users?" |
| Documentation and knowledge management | Tool-neutral docs and memory framework enabling handoff without the original conversation | "How do you make your work maintainable by others?" |

## Stack keywords

Python, Flask, Excel automation (openpyxl), Word and PDF automation (python-docx,
pypdf, Word COM), local LLM integration (Ollama), Windows Task Scheduler, Gmail
API and OAuth2, Git and git history rewriting, test-driven development.
