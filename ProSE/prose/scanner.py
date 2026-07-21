"""Scan for active solicitations matching keywords.

Search source: the HANDS public JSON API
(``POST /hands/api/bidding-opportunities``). HANDS is a fast, stateless search
front-end over HiePRO (and other systems). Compared to driving HiePRO's own
search (Spring WebFlow + CSRF + DataTables), the HANDS API:
  * needs no session/CSRF dance,
  * returns all matches in one call (``omitPagination: true``),
  * tolerates rapid repeated searches, and
  * already includes Solicitation #, Department, Title, Published, Due Date and
    the HiePRO detail URL.

The only fields HANDS omits are Contact Name / Phone / Email, so for each unique
solicitation we fetch its (static, un-throttled) HiePRO detail page to fill
those in. Detail values are authoritative and override the HANDS values; if a
detail fetch fails we still keep the 5 fields HANDS gave us (graceful degrade).
"""

from __future__ import annotations

import re
import time

import requests

from . import parser

HANDS_SEARCH = "https://hands.ehawaii.gov/hands/api/bidding-opportunities"
# Public per-opportunity detail (no login) -- holds full contact info for
# HANDS-native notices (county/UH/agency postings).
HANDS_DETAIL = "https://hands.ehawaii.gov/hands/api/opportunity"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 ProSE/0.1"
)

TIMEOUT = 45
RETRIES = 3
RETRY_BACKOFF = 5     # seconds * attempt, between retries
KEYWORD_DELAY = 0.4   # HANDS is fast/tolerant; a small courtesy delay
DETAIL_DELAY = 0.4    # between HiePRO detail-page fetches

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub("", text or "")).strip()


def _clean(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip() if value else ""


def _title_name(name: str) -> str:
    """Normalize a person's name to Title Case for a consistent-looking sheet.

    HANDS returns names in wildly mixed conventions ('JANE DOE', 'john smith').
    Each letter run is capitalized when it is entirely upper- or lower-case;
    runs that are already mixed-case (e.g. 'McCarthy', 'DeLuca') are left
    untouched so we don't degrade them. Handles hyphens/apostrophes (each part
    cased: 'SMITH-JONES' -> 'Smith-Jones', "o'brien" -> "O'Brien").
    """
    def fix(match: re.Match) -> str:
        word = match.group(0)
        if word.isupper() or word.islower():
            return word[:1].upper() + word[1:].lower()
        return word

    return re.sub(r"[A-Za-z]+", fix, name)


def normalize_phone(value) -> str:
    """Standardize phone numbers to '808-555-1234' regardless of source format.

    HiePRO gives '808-587-1990'; HANDS gives '(808) 241-4292'. Drops a leading
    US country code and preserves an extension if present. Leaves unparseable
    values as their cleaned original.
    """
    raw = _clean(value)
    if not raw:
        return ""
    ext_match = re.search(r"(?:ext\.?|x)\s*(\d+)\s*$", raw, re.I)
    ext = ext_match.group(1) if ext_match else ""
    core = raw[: ext_match.start()] if ext_match else raw
    digits = re.sub(r"\D", "", core)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return raw  # unexpected format — keep original (cleaned)
    formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return f"{formatted} x{ext}" if ext else formatted


def make_session() -> requests.Session:
    """Session for the HANDS JSON API (needs the XHR/JSON Accept headers)."""
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    return s


def make_detail_session() -> requests.Session:
    """Plain session for HiePRO detail pages. The JSON/XHR headers used for the
    HANDS API make HiePRO serve a different (contact-less) view, so detail
    fetches must use a plain browser-like session."""
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _search_body(keyword: str) -> dict:
    return {
        "query": keyword,
        "showClosed": False,
        "showCancelled": False,
        "omitPagination": True,          # return every match in one response
        "categories": [],
        "procurementCategory": "",
        "department": "",
        "islands": [],
        "statuses": ["POSTED"],          # active only (HiePRO "Released")
        "publishDate": "",
        "offerDueDate": "",
        "jurisdiction": "",
    }


def _hands_to_record(item: dict) -> dict:
    """Map a HANDS result object to our field dict (5 of 8 fields + rfid)."""
    number = str(item.get("solicitionNo") or "").strip()  # note: HANDS' spelling
    rfid = str(item.get("id") or parser.rfid_from_number(number)).strip()
    return {
        "solicitation_number": number,
        "organization": item.get("department") or "",
        "title": _strip_html(item.get("title")),
        "published": item.get("publishDate") or "",
        "due_date": item.get("dueDate") or "",
        "contact_name": "",
        "phone": "",
        "email": "",
        "rfid": rfid,
        "system": (item.get("system") or "").upper(),
        "details_url": item.get("detailsUrl") or "",
        "status": item.get("status") or "",
        "keyword": "",  # filled in scan(): the keyword(s) that matched this row
    }


def _search_once(session: requests.Session, keyword: str) -> list[dict]:
    resp = session.post(HANDS_SEARCH, json=_search_body(keyword), timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    content = (
        data.get("data", {})
        .get("searchResult", {})
        .get("content")
        or []
    )
    return [_hands_to_record(it) for it in content if it.get("solicitionNo")]


def search_keyword(session: requests.Session, keyword: str) -> list[dict]:
    """Return active solicitation records (from HANDS) matching one keyword."""
    for attempt in range(1, RETRIES + 1):
        try:
            return _search_once(session, keyword)
        except (requests.RequestException, ValueError):
            if attempt == RETRIES:
                raise
            time.sleep(RETRY_BACKOFF * attempt)
    return []  # pragma: no cover


def _combine_contacts(opp: dict) -> tuple[str, str, str]:
    """Combine a HANDS notice's two contacts into multi-line Name/Phone/Email.

    HANDS notices carry both a **Specifications Contact** (``contact*`` — the SME
    who owns the scope) and a **Buyer** (``buyer*`` — the procurement officer),
    each a distinct person. We keep both, one per line, **specifications first
    then buyer**, with the role in parentheses after each name. Only contacts
    that are actually listed are included (a single-contact notice yields a
    single line). The line order is identical across all three fields, so
    Name/Phone/Email always line up row-for-row.
    """
    contacts = [
        ("Specifications", opp.get("contactName"), opp.get("contactPhone"), opp.get("contactEmail")),
        ("Buyer", opp.get("buyerName"), opp.get("buyerPhone"), opp.get("buyerEmail")),
    ]
    names: list[str] = []
    phones: list[str] = []
    emails: list[str] = []
    for label, name, phone, email in contacts:
        name, phone, email = _title_name(_clean(name)), _clean(phone), _clean(email)
        if not (name or phone or email):
            continue  # this contact isn't listed on the notice
        names.append(f"{name} ({label})" if name else f"({label})")
        phones.append(normalize_phone(phone) if phone else "")
        emails.append(email)
    return "\n".join(names), "\n".join(phones), "\n".join(emails)


def fetch_hands_detail(session: requests.Session, opp_id) -> dict:
    """Fetch contact + key fields for a HANDS-native opportunity via the public
    ``api/opportunity?id=`` endpoint. Returns {} if the id isn't a HANDS notice
    (e.g. HiePRO-sourced rows, which have no record here)."""
    resp = session.get(HANDS_DETAIL, params={"id": opp_id}, timeout=TIMEOUT)
    resp.raise_for_status()
    opp = (resp.json().get("data") or {}).get("opportunity")
    if not opp:
        return {}
    name, phone, email = _combine_contacts(opp)
    return {
        "organization": _clean(opp.get("department")),
        "published": _clean(opp.get("publishedDate")),
        "due_date": _clean(opp.get("dueDate")),
        "contact_name": name,
        "phone": phone,
        "email": email,
    }


def scan(keywords: list[str], log=print) -> list[dict]:
    """Scan all keywords via HANDS, de-duplicate by Solicitation #, and enrich
    each with Contact/Phone/Email -- from the HiePRO detail page for
    HiePRO-sourced rows, or the public HANDS opportunity endpoint for
    HANDS-native rows.
    """
    session = make_session()
    detail_session = make_detail_session()
    seen: dict[str, dict] = {}

    # 1) Fast search across all keywords (HANDS).
    for idx, kw in enumerate(keywords):
        kw = kw.strip()
        if not kw:
            continue
        if idx:
            time.sleep(KEYWORD_DELAY)
        try:
            records = search_keyword(session, kw)
        except Exception as exc:  # noqa: BLE001 - keep going on other keywords
            log(f"  ! keyword '{kw}' failed: {exc}")
            continue
        log(f"  '{kw}': {len(records)} active result(s)")
        for rec in records:
            number = rec["solicitation_number"]
            existing = seen.get(number)
            if existing is None:
                rec["keyword"] = kw
                seen[number] = rec
            else:
                # Same solicitation matched another keyword — accumulate it so
                # the row shows every keyword it came up under.
                current = [k.strip() for k in existing["keyword"].split(",") if k.strip()]
                if kw not in current:
                    existing["keyword"] = ", ".join(current + [kw])

    log(f"  {len(seen)} unique solicitation(s); fetching contact details...")

    # 2) Enrich each unique solicitation with contact info from the right source.
    for i, (number, rec) in enumerate(seen.items()):
        if i:
            time.sleep(DETAIL_DELAY)
        is_hiepro = rec.get("system") == "HIEPRO" or "hiepro.ehawaii.gov" in (
            rec.get("details_url") or ""
        )
        try:
            if is_hiepro:
                detail = parser.fetch_detail(detail_session, number)
                for field in parser.FIELDS:
                    if detail.get(field):  # authoritative; keep HANDS as fallback
                        rec[field] = detail[field]
            else:
                detail = fetch_hands_detail(session, rec.get("rfid"))
                for field, value in detail.items():
                    if value:
                        rec[field] = value
        except Exception as exc:  # noqa: BLE001
            log(f"    ! detail fetch failed for {number} (keeping search fields): {exc}")
        # HANDS dual-contact rows carry a multi-line phone already normalized
        # per line — don't run it back through the single-number normalizer
        # (which collapses newlines). Single-line phones still get normalized.
        phone_val = rec.get("phone") or ""
        rec["phone"] = phone_val if "\n" in phone_val else normalize_phone(phone_val)

    return list(seen.values())
