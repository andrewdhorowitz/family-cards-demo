"""End-to-end build() tests (demo tree) with the calendar layer
stubbed out. fetch_events is replaced with invented fixtures in
Google API shape, so the full pipeline runs — filtering, Dad/Mom
framing, leg resolution, CHANGED tagging — with zero live calendar
access. Every kid, event and place here is fake.
"""

import json
from datetime import date

import pytest

from conftest import ev, find_entry

NOV = "-05:00"
START, END = date(2026, 11, 2), date(2026, 11, 8)  # Mon .. Sun


def fixture_events():
    return {
        "cal-primary": [
            # Dad-day framing for Saturday Nov 7.
            ev("Dad time", f"2026-11-07T00:00:00{NOV}", f"2026-11-07T23:59:00{NOV}"),
            # Sensitive: must never reach a card.
            ev("Emma therapy session", f"2026-11-02T16:00:00{NOV}", f"2026-11-02T17:00:00{NOV}"),
            ev("Noah support group meeting", f"2026-11-03T16:00:00{NOV}", f"2026-11-03T17:00:00{NOV}"),
            # Short event (< 60 min): no pickup leg is ever resolved;
            # its 5 PM drop-off on a Mom day is "ask" -> omitted.
            ev("Emma piano lesson", f"2026-11-02T17:00:00{NOV}", f"2026-11-02T17:30:00{NOV}"),
            # Mom day, 3-5 PM: drop-off is Dad's (before cutoff),
            # pickup at 5 PM is "ask" -> omitted.
            ev("Emma jazz band", f"2026-11-02T15:00:00{NOV}", f"2026-11-02T17:00:00{NOV}"),
            # Dad day: both legs are Dad's, even the 7 PM pickup.
            ev("Emma soccer game", f"2026-11-07T17:00:00{NOV}", f"2026-11-07T19:00:00{NOV}"),
            # Third-party exception: shown, named, CHANGED.
            ev("Grandma pick up Emma", f"2026-11-03T18:00:00{NOV}", f"2026-11-03T18:15:00{NOV}"),
            # Travel-block proof beats the cutoff rule (6 PM pickup).
            ev("Noah voice lesson", f"2026-11-05T17:00:00{NOV}", f"2026-11-05T18:00:00{NOV}"),
            ev(
                "Travel to Noah voice lesson pickup - dad",
                f"2026-11-05T17:25:00{NOV}",
                f"2026-11-05T18:00:00{NOV}",
                description="Pickup from the lesson. [src-event: fixture]",
            ),
            # Cutoff boundary: pickup at exactly 4:30 PM is Dad's...
            ev("Emma book club", f"2026-11-04T15:20:00{NOV}", f"2026-11-04T16:30:00{NOV}"),
            # ...one minute later it is "ask" and omitted.
            ev("Emma chess club", f"2026-11-04T15:21:00{NOV}", f"2026-11-04T16:31:00{NOV}"),
            # A Mom travel block is positive proof: no pickup leg,
            # even though 4 PM is before the cutoff.
            ev("Emma dance class", f"2026-11-06T14:00:00{NOV}", f"2026-11-06T16:00:00{NOV}"),
            ev(
                "Travel to Emma dance class pickup - mom",
                f"2026-11-06T15:30:00{NOV}",
                f"2026-11-06T16:00:00{NOV}",
            ),
        ],
        "cal-family": [],
        "cal-kids": [],
    }


@pytest.fixture()
def built(gc, tmp_path):
    events = fixture_events()
    gc.CALENDARS = {"primary": "cal-primary", "family": "cal-family", "kids": "cal-kids"}
    gc.fetch_events = lambda cal_id, s, e: [dict(x) for x in events.get(cal_id, [])]
    cards, filtered, context, counts, evidence = gc.build(START, END, str(tmp_path))
    return cards, filtered


def test_dad_mom_framing(built):
    cards, _ = built
    days = {d["date"]: d for d in cards["emma"]["days"]}
    assert days["2026-11-07"]["with"] == "Dad"
    assert days["2026-11-02"]["with"] == "Mom"
    assert days["2026-11-08"]["with"] == "Mom"


def test_sensitive_events_never_reach_cards(built):
    cards, filtered = built
    reasons = dict(filtered)
    assert reasons.get("Emma therapy session") == "sensitive category"
    assert reasons.get("Noah support group meeting") == "sensitive category"
    blob = json.dumps(cards).lower()
    assert "therapy" not in blob
    assert "support group" not in blob


def test_short_event_has_no_pickup_leg(built):
    cards, _ = built
    _, entry = find_entry(cards, "emma", "2026-11-02", "piano")
    assert entry is not None
    assert entry["legs"] == []


def test_mom_day_legs_follow_cutoff(built):
    cards, _ = built
    _, entry = find_entry(cards, "emma", "2026-11-02", "jazz")
    assert entry["legs"] == [
        {"kind": "dropoff", "driver": "Dad", "time_label": "3:00 PM"}
    ]


def test_dad_day_both_legs(built):
    cards, _ = built
    _, entry = find_entry(cards, "emma", "2026-11-07", "soccer")
    assert entry["legs"] == [
        {"kind": "dropoff", "driver": "Dad", "time_label": "5:00 PM"},
        {"kind": "pickup", "driver": "Dad", "time_label": "7:00 PM"},
    ]


def test_third_party_leg_is_changed_and_named(built):
    cards, _ = built
    _, entry = find_entry(cards, "emma", "2026-11-03", "grandma pick up")
    assert entry is not None
    assert entry["changed"] is True
    assert entry["changed_note"] == "Pickup: Grandma"
    assert entry["legs"] == [
        {"kind": "pickup", "driver": "Grandma", "time_label": "6:00 PM"}
    ]


def test_travel_block_proof_beats_cutoff(built):
    cards, _ = built
    _, entry = find_entry(cards, "noah", "2026-11-05", "voice")
    assert entry["legs"] == [
        {"kind": "pickup", "driver": "Dad", "time_label": "6:00 PM"}
    ]


def test_cutoff_boundary_in_build(built):
    cards, _ = built
    _, book = find_entry(cards, "emma", "2026-11-04", "book")
    assert {"kind": "pickup", "driver": "Dad", "time_label": "4:30 PM"} in book["legs"]
    _, chess = find_entry(cards, "emma", "2026-11-04", "chess")
    assert [l["kind"] for l in chess["legs"]] == ["dropoff"]


def test_mom_block_removes_pickup_leg(built):
    cards, _ = built
    _, entry = find_entry(cards, "emma", "2026-11-06", "dance")
    assert entry["legs"] == [
        {"kind": "dropoff", "driver": "Dad", "time_label": "2:00 PM"}
    ]
