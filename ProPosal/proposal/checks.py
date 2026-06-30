"""Shared check-result model for the compliance checklist and the format checker.

A check is PASS / WARN / FAIL. WARN means "couldn't verify" (e.g. no exported
PDF yet) or a soft issue; FAIL is a hard problem. Nothing here ever edits the
document -- checks only report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

_MARK = {PASS: "[x]", WARN: "[!]", FAIL: "[ ]"}


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""


@dataclass
class ChecklistReport:
    title: str
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(name, status, detail))

    def pass_(self, name, detail=""):
        self.add(name, PASS, detail)

    def warn(self, name, detail=""):
        self.add(name, WARN, detail)

    def fail(self, name, detail=""):
        self.add(name, FAIL, detail)

    @property
    def failed(self):
        return [c for c in self.checks if c.status == FAIL]

    @property
    def warned(self):
        return [c for c in self.checks if c.status == WARN]

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_console(self) -> str:
        lines = [self.title]
        for c in self.checks:
            d = f"  {_MARK[c.status]} {c.name}"
            if c.detail:
                d += f" -- {c.detail}"
            lines.append(d)
        lines.append(
            f"  => {len(self.failed)} fail, {len(self.warned)} warn, "
            f"{len(self.checks) - len(self.failed) - len(self.warned)} pass"
        )
        return "\n".join(lines)

    def to_markdown(self) -> str:
        lines = [f"## {self.title}", "", "| | Check | Detail |", "|---|---|---|"]
        for c in self.checks:
            lines.append(f"| {_MARK[c.status]} | {c.name} | {c.detail} |")
        lines.append("")
        return "\n".join(lines)
