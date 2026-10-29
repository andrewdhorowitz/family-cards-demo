"""Test harness for generate_cards.py (demo tree).

The generator is loaded straight from the repo root (the file next to
this tests/ directory) by path, so the suite tests the exact code that
ships. Nothing here ever touches a real calendar: the pure decision
functions are called directly, and build() runs with fetch_events
replaced by fixtures. No calendar CLI call can happen in this suite.
All kids, places and events in these tests are invented.
"""

import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

GEN_PATH = Path(__file__).resolve().parent.parent / "generate_cards.py"
TZ = ZoneInfo("America/New_York")


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_cards", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def gc():
    return load_generator()


def ev(summary, start_iso, end_iso, **extra):
    """A calendar event in Google API shape."""
    e = {
        "summary": summary,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    e.update(extra)
    return e


def dt(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def find_entry(cards, kid, date_iso, title_part):
    """(day, entry) for the entry whose title contains title_part."""
    for day in cards[kid]["days"]:
        if day["date"] != date_iso:
            continue
        for e in day["entries"]:
            if title_part.lower() in e["title"].lower():
                return day, e
    return None, None
