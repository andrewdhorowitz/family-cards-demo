"""Unit tests for the demo generator's driver-decision logic.

Same settled rules as the live Family Cards engine, in the demo's
generic vocabulary (drivers are the ids "dad" / "mom"; kids Emma and
Noah are invented):

  (1) title tag / manual transport name on the event itself
  (2) travel-block proof (a tagged block proves its driver; an
      untagged block proves nothing; a Mom block is positive proof
      the leg is Mom's, so the leg is absent from the card)
  (3) exception lists
  (4) dad day -> Dad both ways; on Mom days the 4:20 PM cutoff
      decides (<= 4:20 Dad, later = "ask", omitted from the card)

Plus the named-transport guard regression: in "Noah Pickup" the
leading name is the kid being picked up, never a third-party driver.
"""

import pytest

from conftest import dt, ev

NOV = "-05:00"  # EST offset for the November fixture dates
OCT = "-04:00"  # EDT offset for the October fixture dates


@pytest.mark.parametrize(
    "summary,expected",
    [
        ("Grandma pick up Emma", "grandma"),
        ("Grandma drop off Noah", "grandma"),
        ("Uncle Joe pick up Emma", None),  # two-word name: no match
        ("Noah Pickup", None),  # regression: kid's name is not a driver
        ("Emma Pickup", None),
        ("Noah drop off", None),
        ("Dad pick up Emma", None),  # a parent is not a third party
        ("Mom drop off Noah", None),
        ("Pickup Emma", None),  # the verb itself is not a name
        ("Drop off Emma", None),
        ("Emma piano lesson", None),
        ("Dance recital", None),
    ],
)
def test_named_transport_driver(gc, summary, expected):
    assert gc.named_transport_driver(summary) == expected


def test_title_tag_beats_cutoff(gc):
    e = ev("Emma jazz band - mom", f"2026-11-02T17:00:00{NOV}", f"2026-11-02T19:00:00{NOV}")
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 2, 19, 0), set()) == "mom"
    e = ev("Emma jazz band - dad", f"2026-11-02T17:00:00{NOV}", f"2026-11-02T19:00:00{NOV}")
    # 7 PM on a Mom day would be "ask" by the rule; the tag wins.
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 2, 19, 0), set()) == "dad"


def test_manual_transport_name(gc):
    e = ev("Dad drop off Emma", f"2026-11-02T18:00:00{NOV}", f"2026-11-02T18:15:00{NOV}")
    assert gc.decide_kid_driver(e, "dropoff", dt(2026, 11, 2, 18, 0), set()) == "dad"
    e = ev("Mom pick up Emma", f"2026-11-02T18:00:00{NOV}", f"2026-11-02T18:15:00{NOV}")
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 2, 18, 0), set()) == "mom"


def test_third_party_named_driver(gc):
    e = ev("Grandma pick up Emma", f"2026-11-03T18:00:00{NOV}", f"2026-11-03T18:15:00{NOV}")
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 3, 18, 0), set()) == "grandma"


def test_kid_name_pickup_falls_through_to_rule(gc):
    # Regression, decide-level: "Noah Pickup" must resolve by the
    # normal rule, never to a driver named "noah".
    e = ev("Noah Pickup", f"2026-11-02T14:00:00{NOV}", f"2026-11-02T14:15:00{NOV}")
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 2, 14, 0), set()) == "dad"
    e = ev("Noah Pickup", f"2026-11-02T18:00:00{NOV}", f"2026-11-02T18:15:00{NOV}")
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 2, 18, 0), set()) == "ask"


def test_dad_day_both_ways(gc):
    e = ev("Emma soccer game", f"2026-11-07T17:00:00{NOV}", f"2026-11-07T19:00:00{NOV}")
    dad = {"2026-11-07"}
    assert gc.decide_kid_driver(e, "dropoff", dt(2026, 11, 7, 17, 0), dad) == "dad"
    # 7 PM would be "ask" on a Mom day; a dad day is Dad's both ways.
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 7, 19, 0), dad) == "dad"


@pytest.mark.parametrize(
    "hh,mm,expected",
    [(9, 0, "dad"), (16, 20, "dad"), (16, 21, "ask"), (20, 0, "ask")],
)
def test_mom_day_cutoff_boundary(gc, hh, mm, expected):
    e = ev("Emma book club", f"2026-11-04T15:00:00{NOV}", f"2026-11-04T16:20:00{NOV}")
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 11, 4, hh, mm), set()) == expected


def test_exception_no_pickup_blocks(gc):
    # NO_PICKUP_BLOCKS: this pickup is Mom's even at 3 PM, when the
    # cutoff rule alone would give Dad.
    e = ev(
        "Noah School Career/College",
        f"2026-10-14T14:00:00{OCT}",
        f"2026-10-14T15:00:00{OCT}",
    )
    assert gc.decide_kid_driver(e, "pickup", dt(2026, 10, 14, 15, 0), set()) == "mom"


def test_exception_dad_oneoff(gc):
    # DAD_ONEOFF: this drop-off is Dad's even at 6:30 PM, when the
    # cutoff rule alone would say "ask".
    e = ev(
        "Noah School Career/College",
        f"2026-10-14T14:00:00{OCT}",
        f"2026-10-14T15:00:00{OCT}",
    )
    assert gc.decide_kid_driver(e, "dropoff", dt(2026, 10, 14, 18, 30), set()) == "dad"


def _block(gc, summary, start_iso, end_iso, description=""):
    b = gc.parse_travel_block(
        ev(summary, start_iso, end_iso, description=description, _cal="primary")
    )
    assert b is not None
    return b


def test_parse_travel_block_tagged(gc):
    b = _block(
        gc,
        "Travel to Emma jazz band - dad",
        f"2026-11-02T14:30:00{NOV}",
        f"2026-11-02T15:00:00{NOV}",
    )
    assert b["driver"] == "dad"
    assert b["leg"] == "dropoff"
    assert b["target_norm"] == "emma jazz band"


def test_parse_travel_block_pickup_mom(gc):
    b = _block(
        gc,
        "Travel to Emma jazz band pickup - mom",
        f"2026-11-02T18:30:00{NOV}",
        f"2026-11-02T19:00:00{NOV}",
    )
    assert b["driver"] == "mom"
    assert b["leg"] == "pickup"


def test_parse_travel_block_untagged_proves_nothing(gc):
    b = _block(
        gc,
        "Travel to Emma jazz band pickup",
        f"2026-11-02T18:30:00{NOV}",
        f"2026-11-02T19:00:00{NOV}",
    )
    assert b["driver"] is None


def test_parse_travel_block_description_names_driver(gc):
    b = _block(
        gc,
        "Travel to Emma jazz band pickup",
        f"2026-11-02T18:30:00{NOV}",
        f"2026-11-02T19:00:00{NOV}",
        description="Pickup leg is Dad's run to school.",
    )
    assert b["driver"] == "dad"


def test_parse_travel_block_rejects_non_blocks(gc):
    assert (
        gc.parse_travel_block(
            ev("⚠ Travel to Emma jazz band", f"2026-11-02T14:30:00{NOV}", f"2026-11-02T15:00:00{NOV}")
        )
        is None
    )
    assert (
        gc.parse_travel_block(
            ev("Emma jazz band", f"2026-11-02T15:00:00{NOV}", f"2026-11-02T17:00:00{NOV}")
        )
        is None
    )


JAZZ_START = f"2026-11-02T17:00:00{NOV}"
JAZZ_END = f"2026-11-02T19:00:00{NOV}"


def _resolve(gc, event, leg, leg_dt, ev_start, ev_end, dad_dates, blocks):
    log = []
    drv = gc.resolve_driver(
        event, leg, leg_dt, ev_start, ev_end, dad_dates, blocks, "emma", "T", log
    )
    return drv, log[-1]


def test_resolve_event_tag_beats_block(gc):
    e = ev("Emma jazz band - mom", JAZZ_START, JAZZ_END)
    blocks = [
        _block(gc, "Travel to Emma jazz band pickup - dad", f"2026-11-02T18:30:00{NOV}", JAZZ_END)
    ]
    drv, rec = _resolve(gc, e, "pickup", dt(2026, 11, 2, 19, 0), dt(2026, 11, 2, 17, 0), dt(2026, 11, 2, 19, 0), set(), blocks)
    assert drv == "mom"
    assert rec["source"] == "title-tag"
    assert rec["conflict"] is not None


def test_resolve_block_beats_rule(gc):
    e = ev("Emma jazz band", JAZZ_START, JAZZ_END)
    blocks = [
        _block(gc, "Travel to Emma jazz band pickup - dad", f"2026-11-02T18:30:00{NOV}", JAZZ_END)
    ]
    # 7 PM Mom-day pickup: the rule says "ask"; the tagged block proves Dad.
    drv, rec = _resolve(gc, e, "pickup", dt(2026, 11, 2, 19, 0), dt(2026, 11, 2, 17, 0), dt(2026, 11, 2, 19, 0), set(), blocks)
    assert drv == "dad"
    assert rec["source"] == "travel-block"


def test_resolve_mom_block_means_leg_absent(gc):
    e = ev("Emma jazz band", f"2026-11-02T14:00:00{NOV}", f"2026-11-02T16:00:00{NOV}")
    blocks = [
        _block(
            gc,
            "Travel to Emma jazz band pickup - mom",
            f"2026-11-02T15:30:00{NOV}",
            f"2026-11-02T16:00:00{NOV}",
        )
    ]
    # 4 PM: the rule alone would give Dad; the Mom block is positive
    # proof the leg is Mom's (absent from the card).
    drv, rec = _resolve(gc, e, "pickup", dt(2026, 11, 2, 16, 0), dt(2026, 11, 2, 14, 0), dt(2026, 11, 2, 16, 0), set(), blocks)
    assert drv == "mom"
    assert rec["source"] == "travel-block"


def test_resolve_untagged_block_is_not_proof(gc):
    e = ev("Emma jazz band", JAZZ_START, JAZZ_END)
    blocks = [
        _block(gc, "Travel to Emma jazz band pickup", f"2026-11-02T18:30:00{NOV}", JAZZ_END)
    ]
    drv, rec = _resolve(gc, e, "pickup", dt(2026, 11, 2, 19, 0), dt(2026, 11, 2, 17, 0), dt(2026, 11, 2, 19, 0), set(), blocks)
    assert drv == "ask"
    assert rec["source"] == "cutoff-rule"


def test_resolve_exception_list(gc):
    e = ev(
        "Noah School Career/College",
        f"2026-10-14T14:00:00{OCT}",
        f"2026-10-14T15:00:00{OCT}",
    )
    drv, rec = _resolve(gc, e, "pickup", dt(2026, 10, 14, 15, 0), dt(2026, 10, 14, 14, 0), dt(2026, 10, 14, 15, 0), set(), [])
    assert drv == "mom"
    assert rec["source"] == "exception-list"


def test_resolve_dad_day(gc):
    e = ev("Emma soccer game", f"2026-11-07T17:00:00{NOV}", f"2026-11-07T19:00:00{NOV}")
    drv, rec = _resolve(
        gc, e, "pickup", dt(2026, 11, 7, 19, 0), dt(2026, 11, 7, 17, 0), dt(2026, 11, 7, 19, 0), {"2026-11-07"}, []
    )
    assert drv == "dad"
    assert rec["source"] == "dad-day"


def test_resolve_third_party_manual_transport(gc):
    e = ev("Grandma pick up Emma", f"2026-11-03T18:00:00{NOV}", f"2026-11-03T18:15:00{NOV}")
    drv, rec = _resolve(gc, e, "pickup", dt(2026, 11, 3, 18, 0), dt(2026, 11, 3, 18, 0), dt(2026, 11, 3, 18, 15), set(), [])
    assert drv == "grandma"
    assert rec["source"] == "manual-transport"


@pytest.mark.parametrize(
    "title",
    [
        "Emma therapy session",
        "Therapist appointment",
        "Support group meeting",
        "Dentist appointment",
        "Doctor visit",
    ],
)
def test_sensitive_titles_match(gc, title):
    assert gc.SENSITIVE_RE.search(title)


@pytest.mark.parametrize(
    "title", ["Emma piano lesson", "Soccer practice", "Emma jazz band", "Book club"]
)
def test_ordinary_titles_are_not_sensitive(gc, title):
    assert not gc.SENSITIVE_RE.search(title)


@pytest.mark.parametrize(
    "title,expected",
    [("Dad time", True), ("Dad's weekend", True), ("Dad busy", False), ("Weekend with Dad", False)],
)
def test_dad_day_detection(gc, title, expected):
    assert bool(gc.DAD_RE.search(title)) is expected
