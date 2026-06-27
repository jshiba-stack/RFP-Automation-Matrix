"""Fetch and parse a HiePRO solicitation detail page into the 8 data fields.

Detail pages are static, server-rendered HTML. The "General Information" tab is
a ``<dl class="dl-horizontal">`` of ``<dt>`` label / ``<dd>`` value pairs, and
the title lives in ``<h4>NUMBER <small>TITLE</small></h4>``.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

DETAIL_URL = "https://hiepro.ehawaii.gov/public-display-solicitation.html"

# Ordered data fields the scanner writes to the spreadsheet.
FIELDS = [
    "solicitation_number",
    "organization",
    "title",
    "published",
    "due_date",
    "contact_name",
    "phone",
    "email",
]


def rfid_from_number(solicitation_number: str) -> str:
    """'B26003328' -> '26003328' (leading B/P/Q prefix stripped)."""
    num = (solicitation_number or "").strip()
    if num[:1] in ("B", "P", "Q"):
        return num[1:]
    return num


def _flip_name(name: str) -> str:
    """'Hilton, Alan' -> 'Alan Hilton'. Leaves other formats untouched."""
    name = (name or "").strip()
    if name.count(",") == 1:
        last, first = (p.strip() for p in name.split(","))
        if last and first:
            return f"{first} {last}"
    return name


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def parse_detail(html: str, solicitation_number: str | None = None) -> dict:
    """Parse detail-page HTML into a dict keyed by FIELDS."""
    soup = BeautifulSoup(html, "lxml")

    # Build label -> value map from the first dl.dl-horizontal.
    pairs: dict[str, str] = {}
    dl = soup.find("dl", class_="dl-horizontal")
    if dl:
        for dt in dl.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd is None:
                continue
            label = _clean(dt.get_text())
            pairs[label] = _clean(dd.get_text(" "))

    # Title from the <h4>NUMBER <small>TITLE</small></h4> heading.
    title = ""
    h4 = soup.find("h4")
    if h4:
        small = h4.find("small")
        if small:
            title = _clean(small.get_text())

    def get(*labels: str) -> str:
        for lab in labels:
            for key, val in pairs.items():
                if key.lower().startswith(lab.lower()):
                    return val
        return ""

    return {
        "solicitation_number": get("Solicitation Number") or (solicitation_number or ""),
        "organization": get("Department"),
        "title": title,
        "published": get("Release Date"),
        "due_date": get("Offer Due Date"),
        "contact_name": _flip_name(get("Contact Person")),
        "phone": get("Phone"),
        "email": get("Email"),
        # extra (not written to manual columns, handy for logging/filtering)
        "status": get("Status"),
    }


def fetch_detail(session, solicitation_number: str) -> dict:
    """Fetch + parse the detail page for a solicitation number.

    Sends ``&resetCookie`` (exactly as HiePRO's own result links do) so the
    public page loads without a sign-in/session redirect.
    """
    rfid = rfid_from_number(solicitation_number)
    resp = session.get(
        DETAIL_URL, params={"rfid": rfid, "resetCookie": ""}, timeout=30
    )
    resp.raise_for_status()
    data = parse_detail(resp.text, solicitation_number)
    data["rfid"] = rfid
    return data
