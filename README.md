# Family Cards — DEMO (fake data only)

Public demo of the Family Cards page using the same code as the private
live version, with fully invented kids ("Emma" / "Noah") and invented
events. Nothing here is real family data.

**See it:** https://andrewdhorowitz.github.io/family-cards-demo/ —
the demo's home is GitHub Pages (static hosting under the
`/family-cards-demo/` subpath). No code or sign-in is needed there:
with no gate answering, the page runs in open demo mode and shows both
cards with tabs, under a "Demo" banner.

- Where a gate does run (the Cloudflare-hosted variant, Phase 2
  below), what the page shows is decided by the access code's scope:
  a kid scope renders only her own card; the demo's `owner` scope
  renders both cards with tabs — the same view the open mode shows.
- Emma's Nov 3 dance class shows a **CHANGED** tag with a third-party
  pickup ("Pickup: Grandma"); Noah's Nov 4 piano lesson shows a CHANGED
  tag for a moved time (new time only).
- `generate_cards.py` is the same generator logic as the live version
  (in the private repo it reads real calendars and writes the per-kid
  JSON files this page renders), with all names and places genericized
  for this public demo; the demo JSON files here were written by hand
  to match its schema.
- The heading stamp reads **"Last changed: …"** — when the card's content last actually changed, not when it was last rebuilt. A CHANGED entry also carries its own "Updated …" time (visible on Emma's and Noah's CHANGED examples).

First real links are handed to each kid in person by their dad.

## Architecture

C4-lite diagrams (System Context inset + Container view, Mermaid,
diagrams-as-code) for this demo system — Emma / Noah only, generic
services, the three flows (publishing, access codes, kid notes):
[docs/architecture.md](docs/architecture.md). That file is the
canonical diagram source; it renders natively on GitHub and feeds the
showcase site, so there is no second hand-maintained copy.

## Phase 2 — the auth/code gate (demo)
On GitHub Pages nothing server-side runs, so the gate below is inert
there: `functions/` and `codes.json` are plain static files (Jekyll
doesn't even copy the underscore-prefixed middleware), `codes.json`
holds only the hash of the public demo code, and the page's fetches
are all relative so they resolve under the subpath. Where the demo is
hosted on Cloudflare Pages, it runs the same gate as the private version:
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

## Kid-side notes (demo display only)
The cards show the "📝 Anything on your side?" note box (note text plus
optional date and optional estimated from/to times) **disabled**, with
"Demo — notes are turned off here." In the private version the box is
live on kid cards: submissions go to a same-origin endpoint that
attributes the note from the kid's verified sign-in and stores it for
Dad, and the kid's own notes list under the box. Here the endpoint is a
stub that acknowledges and discards — nothing is stored or forwarded,
and no real form or backend is referenced anywhere in this repo.
