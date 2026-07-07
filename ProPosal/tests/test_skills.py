"""Tests for the Section I skill classifier (deterministic path — no LLM).

Uses the committed FY2027 taxonomy cache, so it runs without the notice PDF.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import dit_taxonomy, skills  # noqa: E402
from proposal.flags import Report  # noqa: E402

TAX = dit_taxonomy.load_taxonomy()
BY = dit_taxonomy.by_letter(TAX)


def _silent(*_a, **_k):
    pass


def test_exact_match_autoapplies_stale_letter():
    # a skill named like FY category 'e' (Web Applications) but still labelled 'd'
    cats = [{"id": "c1", "dit_number": "d", "name": BY["e"]["name"], "description": ""}]
    rep = Report()
    out = skills.classify_categories(cats, TAX, backend=None, report=rep, log=_silent)
    assert cats[0]["dit_number"] == "e", "stale d -> e should be auto-applied"
    assert out["applied"] == 1
    assert any(r.status == "applied" for r in rep.applied_records)
    r0 = out["results"][0]
    assert r0["kind"] == "exact" and r0["applied"] and r0["suggested"] == "e"


def test_correct_letter_is_left_untouched():
    cats = [{"id": "c1", "dit_number": "a", "name": BY["a"]["name"], "description": ""}]
    rep = Report()
    out = skills.classify_categories(cats, TAX, report=rep, log=_silent)
    assert cats[0]["dit_number"] == "a"
    assert out["applied"] == 0
    assert not rep.applied_records


def test_removed_category_is_flagged_not_applied():
    cats = [{"id": "c1", "dit_number": "?",
             "name": "IT Portfolio and Project Management", "description": "PMP, Agile"}]
    rep = Report()
    out = skills.classify_categories(cats, TAX, backend=None, report=rep, log=_silent)
    assert cats[0]["dit_number"] == "?", "a non-exact match must not be auto-applied"
    assert out["applied"] == 0
    assert any(r.is_flag for r in rep.flags)
    assert out["results"][0]["kind"] in ("fuzzy", "none")


def test_duplicates_are_flagged():
    cats = [{"id": "c1", "dit_number": "e", "name": BY["e"]["name"]},
            {"id": "c2", "dit_number": "", "name": BY["e"]["name"]}]
    rep = Report()
    out = skills.classify_categories(cats, TAX, report=rep, log=_silent)
    assert any(d["letter"] == "e" and set(d["members"]) == {"c1", "c2"}
               for d in out["duplicates"])
    assert any(r.is_flag and "merge" in r.summary.lower() for r in rep.flags)


def test_finalize_uppercases_sorts_and_keeps_x_block_titles():
    # deliberately messy / out-of-order, with stale letters and unclassified rows
    cats = [
        {"dit_number": "x", "name": "Professional IT Services not listed above"},  # placeholder -> dropped
        {"dit_number": "d", "name": BY["e"]["name"], "description": "web apps"},    # stale d -> E
        {"dit_number": "a", "name": BY["a"]["name"], "description": "db"},
        {"dit_number": "?", "name": "IT Portfolio and Project Management", "description": "PMP"},  # -> X row
        {"dit_number": "", "name": "Low Code Development", "description": "Power Apps"},            # -> X row
    ]
    rows = skills.finalize_categories(cats, TAX)
    letters = [r["dit_number"] for r in rows]
    assert letters == ["A", "E", "X", "X"], letters          # UPPERCASE, sorted, X block (2) last
    # non-X rows carry the canonical FY name
    assert next(r for r in rows if r["dit_number"] == "E")["name"] == BY["e"]["name"]
    # X block: each specialty keeps its OWN title (never the FY canonical) + description
    xs = [r for r in rows if r["catchall"]]
    xnames = [r["name"] for r in xs]
    assert "IT Portfolio and Project Management" in xnames
    assert "Low Code Development" in xnames
    assert all(r["name"] != BY["x"]["name"] for r in xs)     # never the FY canonical name
    assert next(r for r in xs if "Low Code" in r["name"])["description"] == "Power Apps"


def test_combined_rows_dedupe_description_items():
    # two skills forced onto the same non-catch-all letter, with overlapping techs
    cats = [
        {"dit_number": "n", "name": BY["n"]["name"], "description": "Angular, NodeJs\nFlutter\nPHP"},
        {"dit_number": "n", "name": "Internet and E-Commerce", "description": ".NET\nFlutter\nAngular"},
    ]
    rows = skills.finalize_categories(cats, TAX)
    n = next(r for r in rows if r["dit_number"] == "N")
    items = n["description"].split("\n")
    lowered = [i.lower() for i in items]
    assert lowered.count("flutter") == 1, items
    assert lowered.count("angular") == 1, items
    assert "PHP" in items and ".NET" in items         # everything else survives


def test_no_taxonomy_degrades_gracefully():
    rep = Report()
    out = skills.classify_categories([{"id": "c1", "name": "x", "dit_number": ""}],
                                     taxonomy=[], report=rep, log=_silent)
    assert out["no_taxonomy"] and out["applied"] == 0 and not rep.flags
