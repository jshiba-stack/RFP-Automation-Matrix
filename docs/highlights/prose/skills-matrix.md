# Skills Matrix: ProSE

Competencies demonstrated in **ProSE**, each tied to concrete evidence a recruiter
or interviewer can check. Use this to map the work onto a job description
quickly, and to pick which [case study](case-studies.md) to tell for a given
prompt.

For the document-assembly program, see
[ProPosal skills matrix](../proposal/skills-matrix.md).

| Competency | Evidence in this repo | Interview prompt it answers |
| --- | --- | --- |
| Root-cause debugging | Traced duplicate records to a later pipeline stage overwriting the identifier the de-duplication had grouped on, confirmed against the live upstream response | "Tell me about a hard bug." |
| Concurrency and data integrity | Lock-aware scans, dedup by stable key, non-destructive updates to a workbook a human edits at the same time | "How do you avoid corrupting shared state?" |
| Testing assumptions | Found a concurrency guard's premise false for cloud-synced files (no exclusive lock when co-authored) by testing it rather than trusting it | "When did you discover a premise was wrong?" |
| Designing safe recovery | Crash-leftover failsafe gated on a liveness probe, so cleanup can never disarm the guard it protects | "How do you build something that self-recovers without making things worse?" |
| Data migration and repair | Self-healing merge that fixes defects in already-written rows, folding human-entered values from both copies of a duplicate | "Have you had to fix bad data in production?" |
| Reverse-engineering an API | Determined an undocumented search API's matching semantics (substring, ANDed tokens, metadata-only scope) through systematic probing | "How do you work with a system you have no docs for?" |
| Automation and scheduling | OS task scheduler jobs that survive reboots and run without the app open, with a kill switch | "Have you built something that runs unattended?" |
| Cross-client rendering | Row sizing computed in-library plus conditional alignment, so the same file renders consistently in the desktop and browser spreadsheet clients | "Have you dealt with output that differs by environment?" |
| Product and stakeholder thinking | Automation built around a real procurement workflow; human action columns and formatting treated as a hard constraint | "How do you design for real users?" |
| Communicating limitations | Documented that the lock signal cannot see a remote collaborator, rather than implying full coverage | "How do you handle the gaps in your own solution?" |

## Stack keywords

Python, Flask, Excel automation (openpyxl), REST/JSON API integration, HTML
parsing (BeautifulSoup), Windows Task Scheduler, Gmail API and OAuth2,
SharePoint/OneDrive sync integration, concurrency and file-locking, Git.
