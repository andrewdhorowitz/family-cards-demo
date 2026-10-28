# Family Cards — DEMO (fake data only)

Public demo of the Family Cards page using the same code as the private
live version, with fully invented kids ("Emma" / "Noah") and invented
events. Nothing here is real family data.

- What the page shows is decided by the access code's scope (see
  Phase 2 below): a kid scope renders only her own card; the demo's
  `owner` scope renders both cards with tabs.
- Emma's Nov 3 dance class shows a **CHANGED** tag with a third-party
  pickup ("Pickup: Grandma"); Noah's Nov 4 piano lesson shows a CHANGED
  tag for a moved time (new time only).
- `generate_cards.py` is the same generator logic as the live version
  (in the private repo it reads real calendars and writes the per-kid
  JSON files this page renders), with all names and places genericized
  for this public demo; the demo JSON files here were written by hand
  to match its schema.

First real links are handed to each kid in person by their dad.

## Phase 2 — the auth/code gate (demo)
This demo runs the same gate as the private version:
`functions/_middleware.js` checks every request for a signed
`fc_auth` cookie (HMAC-SHA256, keyed by the `CODE_SECRET` environment
variable, which must be set in the hosting project's settings or the
site fails closed with 401s). A link with `?c=<token>` whose SHA-256
hash matches an entry in `codes.json` mints that cookie and redirects
to the clean URL.

The demo's one fixed public code is the word **demo**, with `owner`
scope (both cards, with tabs). Link format:

```
<demo site>/?c=demo
```

`mint_codes.py` is the same minter the private version uses; the
private system instead uses random per-kid expiring codes, minted in
batches, with only hashes stored in its `codes.json`.
