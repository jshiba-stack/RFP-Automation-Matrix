"""Tests for the DIT category taxonomy parser + cache.

The notice PDF is git-ignored (public repo), but the derived YAML cache is
committed, so `load_taxonomy` is testable everywhere; the PDF-parsing test skips
when the source PDF isn't present.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from proposal import config, dit_taxonomy  # noqa: E402


def test_letter_at_sequence():
    assert dit_taxonomy._letter_at(0) == "a"
    assert dit_taxonomy._letter_at(25) == "z"
    assert dit_taxonomy._letter_at(26) == "aa"
    assert dit_taxonomy._letter_at(27) == "ab"


def test_keywords_drop_stopwords_and_dedupe():
    kw = dit_taxonomy._keywords("Web Applications – Design and Development of Applications")
    assert "web" in kw and "applications" in kw
    assert "and" not in kw and "of" not in kw          # stopwords dropped
    assert kw.count("applications") == 1               # de-duped


def test_load_taxonomy_from_committed_cache():
    tax = dit_taxonomy.load_taxonomy()
    assert len(tax) >= 20, "FY2027 DIT list should parse to ~24 categories"
    by = dit_taxonomy.by_letter(tax)
    # the answer we quoted the user: category i = Network Support
    assert "i" in by
    assert "network support" in by["i"]["name"].lower()
    # letters are sequential and lowercased
    assert [c["letter"] for c in tax] == [dit_taxonomy._letter_at(i) for i in range(len(tax))]
    # every entry carries keywords
    assert all(c.get("keywords") for c in tax)


@pytest.mark.skipif(not config.notice_pdf_abspath(config.load_config()).exists(),
                    reason="FY2027 notice PDF not available")
def test_parse_taxonomy_from_pdf_matches_cache():
    pdf = config.notice_pdf_abspath(config.load_config())
    parsed = dit_taxonomy.parse_taxonomy(pdf)
    assert [c["letter"] for c in parsed] == [c["letter"] for c in dit_taxonomy.load_taxonomy()]
