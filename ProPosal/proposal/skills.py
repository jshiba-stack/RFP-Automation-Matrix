"""Section I skill classifier.

The firm's Section I ("Professional Service Categories") carries a ``DIT #`` letter
per skill, keyed to the City & County notice. Those letters drift year to year as
categories are inserted/removed, so the firm's copy goes stale (e.g. a skill that
used to be ``d`` is now ``e``), and skills can pile up that map to the same category.

This pass reconciles each skill against the current-year DIT taxonomy
(``dit_taxonomy``):

* **exact name match** -> the correct FY letter is known; if it differs from the
  firm's it is **auto-applied** (recorded APPLIED + a REVIEW flag), same safe
  behaviour as the format proofreader;
* **no exact match** -> a **suggestion** is offered (local LLM if enabled, else a
  deterministic keyword score, else the "not listed above" catch-all) and
  **flag-only** — never silently applied, because it's a judgement call;
* **duplicates** -> skills that resolve to the same category are flagged with a
  merged-row suggestion for the human to accept.

Nothing requires the LLM: with it disabled or unreachable the deterministic path
runs and the build never fails.
"""

from __future__ import annotations

import json
import re

from . import dit_taxonomy
from .flags import KIND_REVIEW, Report

# A fuzzy suggestion needs at least this many shared keywords to name a specific
# category; a single generic token (e.g. "application") is too weak and defaults to
# the catch-all instead, so we never emit a confident-looking wrong letter.
_MIN_OVERLAP = 2


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _norm_letter(v) -> str:
    v = str(v or "").strip().lower()
    return v if re.fullmatch(r"[a-z]{1,2}", v) else ""   # "", "?" -> unknown


def _catchall_letter(taxonomy: list[dict]) -> str:
    for t in taxonomy:
        if "not listed" in t["name"].lower():
            return t["letter"]
    return taxonomy[-1]["letter"] if taxonomy else ""


def _label(cat: dict) -> str:
    name = (cat.get("name") or "").strip()
    return f"Section I · {name[:44]}" if name else "Section I · (unnamed)"


def _fuzzy_best(cat: dict, taxonomy: list[dict]):
    """Best keyword match: (overlap_count, coverage, letter, overlap_tokens) or None."""
    ftok = set(dit_taxonomy._keywords(f"{cat.get('name', '')} {cat.get('description', '')}"))
    best = None
    for t in taxonomy:
        ttok = set(t["keywords"])
        overlap = ftok & ttok
        if not ttok or not overlap:
            continue
        cand = (len(overlap), round(len(overlap) / len(ttok), 3), t["letter"], sorted(overlap))
        if best is None or cand[:2] > best[:2]:
            best = cand
    return best


def _llm_letter(cat: dict, taxonomy: list[dict], backend):
    """Ask the LLM for the single best letter. Returns (letter, conf, rationale) or None."""
    listing = "\n".join(f'{t["letter"]}: {t["name"]}' for t in taxonomy)
    prompt = (
        "A firm is applying to a City & County IT procurement. Assign the firm's "
        "service below to EXACTLY ONE official DIT category letter.\n\n"
        "Rules:\n"
        "- Match on the NATURE of the work and the technologies named (use the "
        "description, not just the title).\n"
        "- Prefer the most specific category that fits; only use the "
        '"not listed above" catch-all when no specific category is close.\n'
        '- Use "none" only if the service is genuinely unrelated to every category.\n\n'
        f"Firm service:\nname: {cat.get('name', '')}\n"
        f"description: {cat.get('description', '')}\n\n"
        f"Official DIT categories:\n{listing}\n\n"
        'Respond with JSON only: {"letter": "<letter or none>", '
        '"confidence": <0..1>, "rationale": "<one sentence: why this category>"}'
    )
    try:
        raw = backend.complete(
            prompt, system="You are a government procurement classification expert. "
            "You reason about the actual scope of work, then answer with JSON only.",
            json=True)
        data = json.loads(raw)
    except Exception:  # noqa: BLE001 — any backend/parse failure -> deterministic path
        return None
    letter = str(data.get("letter", "")).strip().lower()
    if letter in {t["letter"] for t in taxonomy}:
        return letter, float(data.get("confidence") or 0.0), str(data.get("rationale") or "")
    return None


def classify_categories(categories: list[dict], taxonomy: list[dict] | None = None, *,
                        backend=None, report: Report | None = None,
                        log=print, apply: bool = True) -> dict:
    """Reconcile Section I skills against the DIT taxonomy.

    Mutates each category's ``dit_number`` in place for exact matches when
    ``apply``. Records APPLIED + REVIEW flags in ``report``. Returns a summary
    (``results``, ``duplicates``, ``used_llm``, counts) for the caller/UI.
    """
    taxonomy = taxonomy if taxonomy is not None else dit_taxonomy.load_taxonomy()
    report = report if report is not None else Report()
    if not taxonomy:
        log("[skills] no DIT taxonomy available — skipping classification.")
        return {"results": [], "duplicates": [], "used_llm": False,
                "applied": 0, "flagged": 0, "no_taxonomy": True}

    by_letter = dit_taxonomy.by_letter(taxonomy)
    by_name = {_norm(t["name"]): t["letter"] for t in taxonomy}
    catchall = _catchall_letter(taxonomy)
    results, used_llm, applied_n = [], False, 0

    for cat in categories:
        name = (cat.get("name") or "").strip()
        if not name:
            continue
        current = _norm_letter(cat.get("dit_number"))
        loc = _label(cat)
        exact = by_name.get(_norm(name))

        if exact:
            suggested, kind, conf, applied = exact, "exact", 1.0, False
            rationale = f"category name matches DIT '{exact}' exactly"
            if apply and exact != current:
                old = str(cat.get("dit_number") or "")
                cat["dit_number"] = exact
                applied = True
                applied_n += 1
                report.applied(loc, f"reclassified to DIT category '{exact}' ({by_letter[exact]['name'][:40]})",
                               old=old or "(none)", new=exact)
                report.flag(loc, f"'{name}' DIT # {old or '(none)'} → '{exact}' — verify",
                            KIND_REVIEW, old=old, new=exact)
        else:
            got = _llm_letter(cat, taxonomy, backend) if backend is not None else None
            if got:
                used_llm = True
                suggested, conf, rationale = got
                kind = "llm"
            else:
                fb = _fuzzy_best(cat, taxonomy)
                if fb and fb[0] >= _MIN_OVERLAP:
                    suggested, conf, kind = fb[2], fb[1], "fuzzy"
                    rationale = "keywords: " + ", ".join(fb[3])
                else:
                    suggested, conf, kind = catchall, 0.0, "none"
                    rationale = "no close match to any current category — catch-all"
            applied = False
            if kind == "none":
                report.flag(loc, f"'{name}' has no matching DIT category (removed/renamed?) — "
                            f"consider catch-all '{catchall}' ({by_letter[catchall]['name'][:32]})",
                            KIND_REVIEW, old=cat.get("dit_number") or "", new=catchall)
            else:
                tail = " — matches current DIT #" if suggested == current else ""
                report.flag(loc, f"'{name}': no exact DIT match; suggest '{suggested}' "
                            f"({by_letter[suggested]['name'][:32]}) [{kind} {conf:.2f}]{tail} — verify",
                            KIND_REVIEW, old=cat.get("dit_number") or "", new=suggested)

        results.append({
            "id": cat.get("id"), "name": name, "current": current,
            "suggested": suggested, "kind": kind, "confidence": round(conf, 2),
            "applied": applied, "rationale": rationale,
        })

    duplicates = _find_duplicates(results, catchall, by_letter, report)
    log(f"[skills] classified {len(results)} skill(s): {applied_n} auto-applied, "
        f"{len(duplicates)} duplicate group(s){' (LLM)' if used_llm else ''}.")
    return {"results": results, "duplicates": duplicates, "used_llm": used_llm,
            "applied": applied_n, "flagged": len(report.flags)}


def _merge_items(descriptions) -> str:
    """Merge item lists into one, dropping duplicates (case-insensitive).

    Items are the newline- and comma-separated pieces of each description, so
    merging two categories that both list "Flutter" keeps it once. Order of first
    appearance is preserved; each surviving item lands on its own line.
    """
    out: list[str] = []
    seen: set[str] = set()
    for desc in descriptions:
        for line in str(desc or "").split("\n"):
            for part in line.split(","):
                item = part.strip()
                key = item.lower()
                if item and key not in seen:
                    seen.add(key)
                    out.append(item)
    return "\n".join(out)


def finalize_categories(categories: list[dict], taxonomy: list[dict] | None = None) -> list[dict]:
    """Produce the clean, FY-standard Section I table from the store categories.

    House rules (Section I formatting standard):
    - each skill's letter is resolved: an exact taxonomy name-match wins
      (self-heals drifted letters), else an already-valid DIT # is kept, else the
      skill folds into the "not listed above" catch-all;
    - letters are **uppercase** (A-X), matching the FY notice;
    - non-catch-all rows are sorted A-W, one per letter (duplicates combined), and
      **column 2 is the canonical FY category name**;
    - the **catch-all X is the exception**: each specialty keeps its OWN title and
      description (the firm's wording, never the canonical name), and the rows
      share a single merged "X" cell -- so ``catchall: True`` marks them for the
      builder to vertically merge column 1.

    Returns ``[{"dit_number", "name", "description", "catchall"}]``. Idempotent and
    independent of accumulated store state.
    """
    taxonomy = taxonomy if taxonomy is not None else dit_taxonomy.load_taxonomy()
    if not taxonomy:
        return [{"dit_number": str(c.get("dit_number") or "").upper(),
                 "name": (c.get("name") or "").strip(),
                 "description": (c.get("description") or "").strip(),
                 "catchall": False}
                for c in categories if (c.get("name") or "").strip()]

    by_name = {_norm(t["name"]): t["letter"] for t in taxonomy}
    by_letter = {t["letter"]: t for t in taxonomy}
    order = {t["letter"]: i for i, t in enumerate(taxonomy)}
    valid = set(by_letter)
    catchall = _catchall_letter(taxonomy)

    non_x: dict[str, list[tuple[str, str]]] = {}
    x_rows: list[tuple[str, str]] = []          # (title, description) in input order
    for c in categories:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        desc = (c.get("description") or "").strip()
        letter = by_name.get(_norm(name)) or (
            _norm_letter(c.get("dit_number")) if _norm_letter(c.get("dit_number")) in valid
            else catchall)
        if letter == catchall:
            if "not listed above" not in _norm(name):   # skip the catch-all placeholder itself
                x_rows.append((name, desc))
        else:
            non_x.setdefault(letter, []).append((name, desc))

    rows = []
    for letter in sorted(non_x, key=lambda ltr: order.get(ltr, 999)):
        members = non_x[letter]
        # single skill: keep its description verbatim; combined skills: merge their
        # items one-per-line, dropping duplicates (e.g. two N rows both list Flutter)
        descs = members[0][1] if len(members) == 1 \
            else _merge_items(d for _, d in members if d)
        rows.append({"dit_number": letter.upper(), "name": by_letter[letter]["name"],
                     "description": descs, "catchall": False})
    # catch-all X block last: each specialty keeps its own title + description
    for name, desc in x_rows:
        rows.append({"dit_number": catchall.upper(), "name": name,
                     "description": desc, "catchall": True})
    return rows


def _find_duplicates(results, catchall, by_letter, report) -> list[dict]:
    """Group skills that resolve to the same (non-catch-all) category and flag them.

    Only *reliable* letters group: an exact category-name match, or a skill's
    existing DIT #. Model/keyword guesses (llm/fuzzy) are suggestions the human
    hasn't accepted yet, so they never manufacture a duplicate.
    """
    groups: dict[str, list[dict]] = {}
    for r in results:
        letter = r["suggested"] if r["kind"] == "exact" else r["current"]
        if letter and letter != catchall:
            groups.setdefault(letter, []).append(r)
    dups = []
    for letter, members in groups.items():
        if len(members) < 2:
            continue
        names = [m["name"] for m in members]
        report.flag(
            f"Section I · '{letter}' ×{len(members)}",
            f"{len(members)} skills map to DIT '{letter}' ({by_letter[letter]['name'][:32]}): "
            f"{'; '.join(n[:30] for n in names)} — merge into one row?",
            KIND_REVIEW)
        dups.append({"letter": letter, "members": [m["id"] for m in members],
                     "names": names,
                     "suggestion": " / ".join(names)})
    return dups
