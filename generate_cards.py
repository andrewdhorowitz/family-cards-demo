#!/usr/bin/env python3
"""Family Cards generator — demo edition.

Builds one kid-simple JSON data file per kid (emma.json, noah.json)
from calendar events. The kids and events in this public demo are
invented; the card files committed here were written by hand to match
the schema, and this script shows how such files are produced.

Rules implemented:
- Two-week rolling window (default: today .. today+13 days,
  America/New_York).
- Each day is framed "With Dad" when a dad-day event ("Dad time" /
  "Dad's weekend") covers that date, else "With Mom".
- Only the kid's own events appear; non-school events are flagged
  `big`.
- Pickup / drop-off legs are shown only when the driver resolves to
  Dad. Driver precedence: (1) an explicit title tag or manual
  transport name on the event itself, (2) driver evidence from a
  matching "Travel to ..." block (travel blocks are parsed for their
  assigned driver before being filtered out as entries), (3)
  exception lists, (4) the day rule — Dad days resolve to Dad; on
  Mom days a late-afternoon cutoff decides, and "ask" legs are
  omitted (the kid's default assumption is Mom). A travel block
  assigned to Mom is positive proof of Mom, so the leg stays off
  the card.
- A leg driven by a third party (named in a manual transport title)
  is an exception: it is shown, names the driver, and carries the
  CHANGED tag.
- Entries that differ in time from the previous generated card
  (a snapshot kept outside this repo) get a single CHANGED tag;
  the new time only is shown.
- Sensitive-category events (therapy / medical / dental / financial /
  legal / support-group etc.) are excluded entirely.
- Output contains no street addresses, emails, or phone numbers:
  locations are reduced to a simple place name or a town.

Calendar IDs come from the environment so no account identifiers
are ever committed: FAMILY_CARDS_CAL_PRIMARY / _FAMILY / _KIDS.

The page (index.html) never calls any calendar API; it only renders
these JSON files.
"""

import argparse
import json
import re
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/New_York")

# Calendar IDs come from the environment so no account identifiers are
# ever committed: FAMILY_CARDS_CAL_PRIMARY / _FAMILY / _KIDS.
import os

CALENDARS = {
    name: os.environ[f"FAMILY_CARDS_CAL_{name.upper()}"]
    for name in ("primary", "family", "kids")
    if os.environ.get(f"FAMILY_CARDS_CAL_{name.upper()}")
}
KIDS = {"emma": "Emma", "noah": "Noah"}

# --- driver logic -------------------------------------------------------
DAD_RE = re.compile(r"\bdad(?:'s)?\s+(?:time|weekend)\b", re.I)
KID_EVENT_RE = re.compile(r"emma|noah|\bkids?\b", re.I)
TRANSPORT_RE = re.compile(r"^\s*(dad|mom)\s+(drop\s?off|pick\s?up)\b", re.I)
TRANSPORT_ANY_RE = re.compile(r"^\s*(?:(?:dad|mom)\s+)?(drop\s?off|pick\s?up)\b", re.I)
TRANSPORT_NAMED_RE = re.compile(r"^\s*([A-Za-z]+)\s+(drop\s?off|pick\s?up)\b", re.I)
KID_NAMES = frozenset(KIDS)  # lowercase kid keys (emma / noah)


def named_transport_driver(summary):
    """Third-party driver named by a manual transport title ('Grandma
    pick up ...'), or None. A capture that is a kid's own name is NOT a
    driver — in 'Noah Pickup' the name is the kid being picked up —
    so it is discarded here and resolution falls through to the next
    precedence level (travel-block proof, exceptions, day/cutoff rule).
    Parent names and the verb itself are likewise not third parties."""
    m = TRANSPORT_NAMED_RE.match(summary or "")
    if not m:
        return None
    name = m.group(1).lower()
    if name in ("dad", "mom", "pick", "drop") or name in KID_NAMES:
        return None
    return name


TITLE_TAG_RE = re.compile(r"-\s*(dad|mom)\s*$", re.I)
AFTER_HOURS = (16, 20, 0)  # late-afternoon cutoff on Mom days
PICKUP_MIN_DURATION = timedelta(minutes=60)
NO_PICKUP_BLOCKS = {("2026-10-14", "noah school career/college")}
DAD_ONEOFF = {("2026-10-14", "noah school career/college")}
NO_TRAVEL_BLOCKS = {
    ("2026-10-28", "emma teen time"),
    ("2026-10-29", "noah voice lesson"),
    ("2026-10-29", "emma full ensemble 6-9pm"),
}


def transport_driver(ev):
    m = TRANSPORT_RE.match(ev.get("summary") or "")
    return m.group(1).lower() if m else None


def decide_kid_driver(ev, leg, leg_dt, dad_dates):
    """'dad' / 'mom' / 'ask' / third-party name / None.
    Same precedence as travel_blocks.py, plus a generic named-driver
    transport title yields that name (a third-party exception)."""
    summary = ev.get("summary") or ""
    named = transport_driver(ev)
    if not KID_EVENT_RE.search(summary) and named is None:
        return named_transport_driver(summary)
    m = TITLE_TAG_RE.search(summary.strip())
    if m:
        return m.group(1).lower()
    if named is not None:
        return named
    named3 = named_transport_driver(summary)
    if named3 is not None:
        return named3
    try:
        ev_date = parse_dt(ev["start"]).date().isoformat()
    except (KeyError, ValueError):
        ev_date = leg_dt.astimezone(LOCAL_TZ).date().isoformat()
    summary_lower = summary.strip().lower()
    if leg == "pickup" and (ev_date, summary_lower) in NO_PICKUP_BLOCKS:
        return "mom"
    if any(d == ev_date and s in summary_lower for d, s in DAD_ONEOFF):
        return "dad"
    if ev_date in dad_dates:
        return "dad"
    local = leg_dt.astimezone(LOCAL_TZ)
    if (local.hour, local.minute, local.second) <= AFTER_HOURS:
        return "dad"
    return "ask"


# --- travel blocks as driver proof (Oct 28 enhancement) ----------------------
TRAVEL_BLOCK_RE = re.compile(r"^travel to\s+(.+)$", re.I | re.S)
SRC_EVENT_RE = re.compile(r"\[src-event:\s*([^\]]+)\]")
DESC_LEG_DRIVER_RE = re.compile(
    r"\b(?:pickup|drop-?off|leg)\b[^.]{0,60}?\b(dad|mom)(?:'s)?\b", re.I
)
DESC_FOR_TAG_RE = re.compile(r"-\s*(dad|mom)\s*\.?\s*$", re.I)


def normalize_title(s):
    t = (s or "").strip().lower()
    while TITLE_TAG_RE.search(t):
        t = TITLE_TAG_RE.sub("", t).strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def block_driver(ev):
    """Explicit driver named by a travel block: trailing '- dad' /
    '- mom' tag(s) on the title, else an explicit naming in the
    description ('Pickup leg is Dad's ...', '... for X - dad')."""
    t = (ev.get("summary") or "").strip()
    drv = None
    while TITLE_TAG_RE.search(t):
        drv = TITLE_TAG_RE.search(t).group(1).lower()
        t = TITLE_TAG_RE.sub("", t).strip()
    if drv:
        return drv
    desc = ev.get("description") or ""
    m = DESC_LEG_DRIVER_RE.search(desc)
    if m:
        return m.group(1).lower()
    m = DESC_FOR_TAG_RE.search(desc.strip())
    if m:
        return m.group(1).lower()
    return None


def parse_travel_block(ev):
    """Parse a 'Travel to ...' block into driver evidence, or None.
    Leg: 'pickup' when the block title says pickup, else 'dropoff'.
    Target: the event title with 'Travel to', the pickup marker and any
    driver tags stripped, normalized for matching."""
    summary = (ev.get("summary") or "").strip()
    if summary.startswith("⚠"):
        return None
    m = TRAVEL_BLOCK_RE.match(summary)
    if not m:
        return None
    rest = m.group(1).strip()
    leg = "pickup" if re.search(r"\bpickup\b", rest, re.I) else "dropoff"
    target = re.sub(r"\bpickup\b", "", rest, flags=re.I)
    try:
        bend = parse_dt(ev["end"])
        bstart = parse_dt(ev["start"])
    except (KeyError, ValueError):
        return None
    desc = ev.get("description") or ""
    sm = SRC_EVENT_RE.search(desc)
    return {
        "target_norm": normalize_title(target),
        "leg": leg,
        "driver": block_driver(ev),
        "cal": ev.get("_cal"),
        "summary": summary,
        "block_start": bstart,
        "block_end": bend,
        "src_event": sm.group(1) if sm else None,
    }


def match_travel_block(blocks, ev, leg, ev_start, ev_end):
    """Find a travel block proving this leg of this event: same
    normalized target title, same date, and the block ends at/near the
    leg time (event start for drop-off, event end for pickup)."""
    summary = ev.get("summary") or ""
    # A standalone pickup event's own title carries the word 'pickup'
    # ('Noah Pickup'), which block targets have stripped — try the
    # title both ways so its '- dad' pickup block can prove the leg.
    target_norms = {
        normalize_title(summary),
        normalize_title(re.sub(r"\bpickup\b", "", summary, flags=re.I)),
    }
    leg_dt = ev_start if leg == "dropoff" else ev_end
    for b in blocks:
        if b["leg"] != leg or b["target_norm"] not in target_norms:
            continue
        if b["block_end"].date() != leg_dt.astimezone(LOCAL_TZ).date():
            continue
        if abs((b["block_end"] - leg_dt).total_seconds()) <= 3600:
            return b
    return None


def event_explicit_driver(ev):
    """Precedence step 1: title tag or manual transport name on the
    event itself (a generic named transport title = third party)."""
    summary = ev.get("summary") or ""
    m = TITLE_TAG_RE.search(summary.strip())
    if m:
        return m.group(1).lower(), "title-tag"
    named = transport_driver(ev)
    if named is not None:
        return named, "manual-transport"
    named3 = named_transport_driver(summary)
    if named3 is not None:
        return named3, "manual-transport"
    return None, None


def exception_driver(ev, leg, leg_dt):
    """Precedence step 3: travel_blocks.py exception lists."""
    try:
        ev_date = parse_dt(ev["start"]).date().isoformat()
    except (KeyError, ValueError):
        ev_date = leg_dt.astimezone(LOCAL_TZ).date().isoformat()
    summary_lower = (ev.get("summary") or "").strip().lower()
    if leg == "pickup" and (ev_date, summary_lower) in NO_PICKUP_BLOCKS:
        return "mom"
    if any(d == ev_date and s in summary_lower for d, s in DAD_ONEOFF):
        return "dad"
    return None


def resolve_driver(
    ev, leg, leg_dt, ev_start, ev_end, dad_dates, blocks, kid, title, evidence_log
):
    """Full precedence: (1) event tag / manual transport, (2) travel
    block proof, (3) exception lists, (4) dad-day / 4:20 PM rule.
    Appends one record per leg to evidence_log; returns the driver."""
    explicit, explicit_src = event_explicit_driver(ev)
    block = match_travel_block(blocks, ev, leg, ev_start, ev_end)
    block_drv = block["driver"] if block else None
    fallback = decide_kid_driver(ev, leg, leg_dt, dad_dates)
    exc = exception_driver(ev, leg, leg_dt)
    conflict = None
    if explicit is not None:
        chosen, source = explicit, explicit_src
        if block_drv and block_drv != explicit:
            conflict = {
                "with": "travel-block",
                "block_driver": block_drv,
                "chosen": explicit,
                "note": "event tag/manual wins",
            }
    elif block_drv:
        chosen, source = block_drv, "travel-block"
        if fallback != block_drv:
            conflict = {
                "with": "rule",
                "rule_driver": fallback,
                "chosen": block_drv,
                "note": "block wins over rule",
            }
    elif exc is not None:
        chosen, source = exc, "exception-list"
    else:
        chosen = fallback
        source = (
            "dad-day"
            if leg_dt.astimezone(LOCAL_TZ).date().isoformat() in dad_dates
            else "cutoff-rule"
        )
    evidence_log.append(
        {
            "kid": kid,
            "event": title,
            "date": leg_dt.astimezone(LOCAL_TZ).date().isoformat(),
            "leg": leg,
            "driver": chosen,
            "source": source,
            "block": (
                {
                    "cal": block["cal"],
                    "summary": block["summary"],
                    "driver": block_drv,
                    "src_event": block["src_event"],
                }
                if block
                else None
            ),
            "rule_driver": fallback,
            "conflict": conflict,
        }
    )
    return chosen


# --- filtering ---------------------------------------------------------------
SENSITIVE_RE = re.compile(
    r"therapy|therapist|counsel|psych|support group|oa group|"
    r"doctor|\bdr\b|appointment with dr|dentist|dental|orthodon|"
    r"medical|clinic|hospital|insurance|autopay|bank|"
    r"zelle|payment|legal|court|custody|divorce|attorney|law\b|"
    r"prescriber|pharmacy|medication",
    re.I,
)
SKIP_RE = re.compile(
    r"^(travel to|travel:|get ready|⚠)|\btravel short\b|"
    r"^dad busy|tentative — holding|kid driving plan|"
    r"birthday$|'s birthday$",
    re.I,
)
SCHOOL_RE = re.compile(r"\bschool\b|school day|classes\b", re.I)


def parse_dt(node):
    if "dateTime" in node:
        return datetime.fromisoformat(node["dateTime"].replace("Z", "+00:00"))
    return datetime.combine(date.fromisoformat(node["date"]), time.min, LOCAL_TZ)


def fetch_events(cal_id, start, end):
    params = {
        "calendarId": cal_id,
        "timeMin": start.astimezone(LOCAL_TZ).isoformat(),
        "timeMax": end.astimezone(LOCAL_TZ).isoformat(),
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 250,
    }
    out = subprocess.run(
        ["hatch_gws_cli", "calendar", "events", "list", "--params", json.dumps(params)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout).get("items", [])


def simple_place(ev, title):
    blob = f"{title} {ev.get('location') or ''}"
    if re.search(r"riverside high|color guard|state cup", blob, re.I) and not re.search(
        r"state college", blob, re.I
    ):
        place = "Riverside High"
    elif re.search(r"state college", blob, re.I):
        place = "State College"
    elif re.search(r"middle school|maple dr", blob, re.I):
        place = "Middle School"
    else:
        m = re.search(r",\s*([A-Z][a-zA-Z ]+?),\s*NJ", ev.get("location") or "")
        place = m.group(1).strip() if m else None
    return place


def clean_title(summary, kid):
    t = summary.strip()
    while TITLE_TAG_RE.search(t):
        t = TITLE_TAG_RE.sub("", t).strip()
    t = re.sub(rf"^{kid}\s+cg\s+", "", t, flags=re.I)
    t = re.sub(rf"^{kid}\s+", "", t, flags=re.I)
    t = re.sub(rf"\s+{kid}\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*dad\s*$", "", t, flags=re.I)
    return t[:1].upper() + t[1:] if t else t


def fmt_time(dt):
    return dt.astimezone(LOCAL_TZ).strftime("%-I:%M %p")


def build(start_d, end_d, snapshot_dir, suppress_diff_changed=False):
    if len(CALENDARS) < 3:
        raise SystemExit(
            "Set FAMILY_CARDS_CAL_PRIMARY, FAMILY_CARDS_CAL_FAMILY "
            "and FAMILY_CARDS_CAL_KIDS environment variables."
        )
    win_start = datetime.combine(start_d, time.min, LOCAL_TZ)
    win_end = datetime.combine(end_d + timedelta(days=1), time.min, LOCAL_TZ)
    raw, seen = [], set()
    for cal_name, cal_id in CALENDARS.items():
        for ev in fetch_events(cal_id, win_start, win_end):
            canon = (ev.get("summary") or "").strip().lower()
            while TITLE_TAG_RE.search(canon):
                canon = TITLE_TAG_RE.sub("", canon).strip()
            key = (canon, json.dumps(ev.get("start")), json.dumps(ev.get("end")))
            if key in seen:
                continue
            seen.add(key)
            ev["_cal"] = cal_name
            raw.append(ev)

    # Parse travel blocks as driver evidence BEFORE they are filtered
    # out as entries. Sensitive targets are skipped (their events never
    # become card entries anyway).
    travel_blocks = []
    for ev in raw:
        b = parse_travel_block(ev)
        if b and not SENSITIVE_RE.search(b["target_norm"]):
            travel_blocks.append(b)
    evidence_log = []

    dad_dates = set()
    for ev in raw:
        if DAD_RE.search(ev.get("summary") or ""):
            try:
                ds, de = parse_dt(ev["start"]).date(), parse_dt(ev["end"]).date()
            except (KeyError, ValueError):
                continue
            d = ds
            while d <= de:
                dad_dates.add(d.isoformat())
                d += timedelta(days=1)

    days = []
    d = start_d
    while d <= end_d:
        days.append(
            {
                "date": d.isoformat(),
                "label": d.strftime("%a %b %-d"),
                "with": "Dad" if d.isoformat() in dad_dates else "Mom",
                "entries": [],
            }
        )
        d += timedelta(days=1)
    by_date = {x["date"]: x for x in days}

    filtered, context = [], []
    counts = {k: 0 for k in KIDS}
    for ev in sorted(raw, key=lambda e: json.dumps(e.get("start"))):
        summary = (ev.get("summary") or "").strip()
        if ev.get("status") == "cancelled":
            filtered.append((summary, "cancelled"))
            continue
        if DAD_RE.search(summary):
            context.append((summary, "dad-day framing"))
            continue
        if "date" in ev.get("start", {}):  # all-day: birthdays, closures
            context.append((summary, "all-day / not a kid activity"))
            continue
        if SENSITIVE_RE.search(summary):
            filtered.append((summary, "sensitive category"))
            continue
        if SKIP_RE.search(summary):
            filtered.append((summary, "travel/get-ready/administrative block"))
            continue
        try:
            start, end = parse_dt(ev["start"]), parse_dt(ev["end"])
        except (KeyError, ValueError):
            filtered.append((summary, "unparseable time"))
            continue
        low = summary.lower()
        kid_keys = [k for k in KIDS if k in low]
        if not kid_keys:
            context.append((summary, "not specific to Emma or Noah"))
            continue
        if (start.date().isoformat(), low) in NO_TRAVEL_BLOCKS:
            pass  # settled legs in travel_blocks; card still lists the event

        for kid in kid_keys:
            title = clean_title(summary, kid)
            entry = {
                "id": f"{kid}-{start.date().isoformat()}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}",
                "title": title,
                "date": start.date().isoformat(),
                "start": start.astimezone(LOCAL_TZ).isoformat(),
                "end": end.astimezone(LOCAL_TZ).isoformat(),
                "time_label": f"{fmt_time(start)}–{fmt_time(end)}",
                "place": simple_place(ev, summary),
                "big": not bool(SCHOOL_RE.search(summary)),
                "changed": False,
                "changed_note": None,
                "changed_at": None,
                "legs": [],
            }
            tm = TRANSPORT_ANY_RE.match(summary)
            verb = tm.group(1) if tm else None
            if tm is None:
                # A named third-party transport title ("Grandma pick up
                # Emma") is a manual transport event too; its verb is
                # group 2 of TRANSPORT_NAMED_RE. Titles that END at the
                # verb ("Emma Pickup") stay on the standalone-pickup
                # path below so they still merge into the activity entry.
                nm = TRANSPORT_NAMED_RE.match(summary)
                if nm and summary[nm.end() :].strip():
                    tm, verb = nm, nm.group(2)
            standalone_pickup = (
                bool(re.search(r"\bpickup\s*$", summary, re.I)) and not tm
            )
            if tm:
                kind = "pickup" if "pick" in verb.lower() else "dropoff"
                drv = resolve_driver(
                    ev,
                    kind,
                    start,
                    start,
                    end,
                    dad_dates,
                    travel_blocks,
                    kid,
                    title,
                    evidence_log,
                )
                if drv == "dad":
                    entry["legs"].append(
                        {"kind": kind, "driver": "Dad", "time_label": fmt_time(start)}
                    )
                elif drv not in ("mom", "ask", None):
                    entry["changed"] = True
                    entry["changed_note"] = f"{kind.capitalize()}: {drv.capitalize()}"
                    entry["legs"].append(
                        {
                            "kind": kind,
                            "driver": drv.capitalize(),
                            "time_label": fmt_time(start),
                        }
                    )
                entry["time_label"] = fmt_time(start)
            elif standalone_pickup:
                entry["_standalone_pickup"] = True
                drv = resolve_driver(
                    ev,
                    "pickup",
                    start,
                    start,
                    end,
                    dad_dates,
                    travel_blocks,
                    kid,
                    title,
                    evidence_log,
                )
                if drv == "dad":
                    entry["legs"].append(
                        {
                            "kind": "pickup",
                            "driver": "Dad",
                            "time_label": fmt_time(start),
                        }
                    )
                elif drv not in ("mom", "ask", None):
                    entry["changed"] = True
                    entry["changed_note"] = f"Pickup: {drv.capitalize()}"
                    entry["legs"].append(
                        {
                            "kind": "pickup",
                            "driver": drv.capitalize(),
                            "time_label": fmt_time(start),
                        }
                    )
                entry["time_label"] = fmt_time(start)
            else:
                drv_d = resolve_driver(
                    ev,
                    "dropoff",
                    start,
                    start,
                    end,
                    dad_dates,
                    travel_blocks,
                    kid,
                    title,
                    evidence_log,
                )
                if drv_d == "dad":
                    entry["legs"].append(
                        {
                            "kind": "dropoff",
                            "driver": "Dad",
                            "time_label": fmt_time(start),
                        }
                    )
                elif drv_d not in ("mom", "ask", None):
                    entry["changed"] = True
                    entry["changed_note"] = f"Drop-off: {drv_d.capitalize()}"
                    entry["legs"].append(
                        {
                            "kind": "dropoff",
                            "driver": drv_d.capitalize(),
                            "time_label": fmt_time(start),
                        }
                    )
                if end - start >= PICKUP_MIN_DURATION:
                    drv_p = resolve_driver(
                        ev,
                        "pickup",
                        end,
                        start,
                        end,
                        dad_dates,
                        travel_blocks,
                        kid,
                        title,
                        evidence_log,
                    )
                    if drv_p == "dad":
                        entry["legs"].append(
                            {
                                "kind": "pickup",
                                "driver": "Dad",
                                "time_label": fmt_time(end),
                            }
                        )
                    elif drv_p not in ("mom", "ask", None):
                        entry["changed"] = True
                        entry["changed_note"] = f"Pickup: {drv_p.capitalize()}"
                        entry["legs"].append(
                            {
                                "kind": "pickup",
                                "driver": drv_p.capitalize(),
                                "time_label": fmt_time(end),
                            }
                        )
            day = by_date.get(entry["date"])
            if day is not None:
                day["entries"].append(entry)
                counts[kid] += 1

    # Merge a standalone "… Pickup" event into the matching activity entry
    # when that entry already shows the same Dad pickup time (keep it simple:
    # one pickup line, not two).
    for day in days:
        entries = day["entries"]
        for e in list(entries):
            if e.pop("_standalone_pickup", False):
                dup = any(
                    o is not e
                    and o["id"].split("-")[0] == e["id"].split("-")[0]
                    and any(
                        l["kind"] == "pickup" and l["time_label"] == e["time_label"]
                        for l in o["legs"]
                    )
                    for o in entries
                )
                if dup:
                    entries.remove(e)
                    counts[e["id"].split("-")[0]] -= 1
                    context.append(
                        (e["title"], "standalone pickup merged into activity")
                    )

    result = {}
    for kid, name in KIDS.items():
        kid_days = []
        for day in days:
            entries = [e for e in day["entries"] if e["id"].startswith(kid + "-")]
            entries.sort(key=lambda e: e["start"])
            kid_days.append({**day, "entries": entries})
        card = {
            "kid": name,
            "generated_at": datetime.now(LOCAL_TZ).isoformat(),
            "window": {"start": start_d.isoformat(), "end": end_d.isoformat()},
            "days": kid_days,
        }
        # Diff vs previous snapshot -> CHANGED on time changes (new time
        # only). suppress_diff_changed is for logic-change regenerations:
        # the method switch itself must not tag entries as CHANGED.
        snap = Path(snapshot_dir) / f"{kid}.json"
        prev_card = json.loads(snap.read_text()) if snap.exists() else None
        prev = (
            {e["id"]: e for day in prev_card["days"] for e in day["entries"]}
            if prev_card
            else {}
        )
        if prev_card and not suppress_diff_changed:
            for day in card["days"]:
                for e in day["entries"]:
                    p = prev.get(e["id"])
                    if p and (p["start"] != e["start"] or p["end"] != e["end"]):
                        e["changed"] = True
        # changed_at: when this run first detected the change. A still-
        # changed entry whose change itself is unchanged vs the snapshot
        # (same times/note/legs) keeps its ORIGINAL detection time; a new
        # or altered change gets this run's generation time. Entries that
        # are no longer changed simply carry changed_at=None.
        gen_at = card["generated_at"]
        for day in card["days"]:
            for e in day["entries"]:
                if not e["changed"]:
                    continue
                p = prev.get(e["id"])
                if (
                    p
                    and p.get("changed")
                    and p.get("changed_at")
                    and p["start"] == e["start"]
                    and p["end"] == e["end"]
                    and p.get("changed_note") == e.get("changed_note")
                    and p.get("legs") == e.get("legs")
                ):
                    e["changed_at"] = p["changed_at"]
                else:
                    e["changed_at"] = gen_at

        # last_changed_at: when the card's CONTENT last actually changed
        # vs the previous snapshot (entries/legs; the generated_at /
        # last_changed_at / changed_at fields themselves don't count).
        # A rebuild with identical content carries it over untouched, so
        # the page stamp means "last changed", not "last rebuilt". First
        # tracked run initializes it to that run's generation time.
        def _sig_entries(c):
            days = []
            for day in c["days"]:
                es = [
                    {k: v for k, v in e.items() if k != "changed_at"}
                    for e in day["entries"]
                ]
                days.append({**day, "entries": es})
            return json.dumps(days, sort_keys=True, default=str)

        if prev_card is None:
            card["last_changed_at"] = gen_at
        elif _sig_entries(card) != _sig_entries(prev_card):
            card["last_changed_at"] = gen_at
        else:
            card["last_changed_at"] = prev_card.get("last_changed_at") or gen_at
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(json.dumps(card, indent=2))
        result[kid] = card
    return result, filtered, context, counts, evidence_log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (default today)")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument(
        "--suppress-diff-changed",
        action="store_true",
        help="logic-change regeneration: do not tag entries "
        "CHANGED from the snapshot time diff this run",
    )
    args = ap.parse_args()
    start_d = (
        date.fromisoformat(args.start) if args.start else datetime.now(LOCAL_TZ).date()
    )
    end_d = start_d + timedelta(days=args.days - 1)
    cards, filtered, context, counts, evidence = build(
        start_d, end_d, args.snapshot_dir, args.suppress_diff_changed
    )
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for kid, card in cards.items():
        (out / f"{kid}.json").write_text(json.dumps(card, indent=2))
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "cards": [f"{kid}.json" for kid in cards],
                "generated_at": next(iter(cards.values()))["generated_at"],
            },
            indent=2,
        )
    )
    ev_path = Path(args.snapshot_dir).parent / (
        f"driver-evidence-{start_d.isoformat()}_{end_d.isoformat()}.json"
    )
    ev_path.write_text(
        json.dumps(
            {
                "window": {"start": start_d.isoformat(), "end": end_d.isoformat()},
                "legs": evidence,
                "conflicts": [e for e in evidence if e["conflict"]],
            },
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "counts": counts,
                "filtered": filtered,
                "context": context,
                "evidence_log": str(ev_path),
                "last_changed_at": {k: c["last_changed_at"] for k, c in cards.items()},
                "changed_entries": [
                    {"kid": k, "id": e["id"], "changed_at": e.get("changed_at")}
                    for k, c in cards.items()
                    for d in c["days"]
                    for e in d["entries"]
                    if e["changed"]
                ],
                "conflicts": [e for e in evidence if e["conflict"]],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
