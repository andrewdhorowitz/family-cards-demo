# Family Cards — DEMO (fake data only)

Public demo of the Family Cards page using the same code as the private
live version, with fully invented kids ("Emma" / "Noah") and invented
events. Nothing here is real family data.

- Kid view: `?kid=emma` or `?kid=noah`; owner view with tabs: no query
  string, or `?view=owner`.
- Emma's Nov 3 dance class shows a **CHANGED** tag with a third-party
  pickup ("Pickup: Grandma"); Noah's Nov 4 piano lesson shows a CHANGED
  tag for a moved time (new time only).
- `generate_cards.py` is the same generator logic as the live version
  (in the private repo it reads real calendars and writes the per-kid
  JSON files this page renders), with all names and places genericized
  for this public demo; the demo JSON files here were written by hand
  to match its schema.

Phase 1 only: no auth / access-code layer, no hosting wired up.
First real links are handed to each kid in person by their dad.
