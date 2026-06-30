"""Change/flag records + report rendering.

Every edit the updater considers becomes a record. Nothing is ever silently
dropped: a value is either APPLIED (and reported) or FLAGGED for the human.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


APPLIED = "applied"
FLAG = "flag"

# flag kinds
KIND_REVIEW = "REVIEW"          # value differs; left unchanged on purpose
KIND_ADD = "ADD MANUALLY"       # store entity with no place in the base doc
KIND_UNSAFE = "UNSAFE EDIT"     # mixed formatting / field region -> not auto-edited
KIND_MISSING = "MISSING"        # expected anchor not found


@dataclass
class Record:
    status: str            # APPLIED or FLAG
    location: str          # human-readable place, e.g. "Cover p26" / "Capacity T10 r1"
    summary: str
    old: str = ""
    new: str = ""
    kind: str = ""         # for flags

    @property
    def is_flag(self) -> bool:
        return self.status == FLAG


@dataclass
class Report:
    base: str = ""
    output: str = ""
    records: list[Record] = field(default_factory=list)

    def applied(self, location, summary, old="", new=""):
        self.records.append(Record(APPLIED, location, summary, old, new))

    def flag(self, location, summary, kind, old="", new=""):
        self.records.append(Record(FLAG, location, summary, old, new, kind))

    @property
    def applied_records(self):
        return [r for r in self.records if r.status == APPLIED]

    @property
    def flags(self):
        return [r for r in self.records if r.is_flag]

    # --- rendering ---
    def to_console(self) -> str:
        lines = [
            f"Base : {self.base}",
            f"Out  : {self.output}",
            f"Applied {len(self.applied_records)} change(s), {len(self.flags)} flag(s).",
            "",
        ]
        if self.applied_records:
            lines.append("APPLIED:")
            for r in self.applied_records:
                d = f"  [{r.location}] {r.summary}"
                if r.old or r.new:
                    d += f"  ({r.old!r} -> {r.new!r})"
                lines.append(d)
            lines.append("")
        if self.flags:
            lines.append("FLAGS (need your review):")
            for r in self.flags:
                d = f"  [{r.kind}] ({r.location}) {r.summary}"
                if r.old or r.new:
                    d += f"  ({r.old!r} -> {r.new!r})"
                lines.append(d)
        else:
            lines.append("No flags.")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# ProPosal build report ({ts})",
            "",
            f"- **Base:** `{self.base}`",
            f"- **Output:** `{self.output}`",
            f"- **Applied:** {len(self.applied_records)} change(s)",
            f"- **Flags:** {len(self.flags)}",
            "",
            "## Applied changes",
            "",
        ]
        if self.applied_records:
            lines.append("| Location | Change | Old | New |")
            lines.append("|---|---|---|---|")
            for r in self.applied_records:
                lines.append(
                    f"| {r.location} | {r.summary} | `{r.old}` | `{r.new}` |"
                )
        else:
            lines.append("_None._")
        lines += ["", "## Flags (need your review)", ""]
        if self.flags:
            lines.append("| Kind | Location | Detail | Old | New |")
            lines.append("|---|---|---|---|---|")
            for r in self.flags:
                lines.append(
                    f"| {r.kind} | {r.location} | {r.summary} | `{r.old}` | `{r.new}` |"
                )
        else:
            lines.append("_None._")
        lines.append("")
        return "\n".join(lines)
