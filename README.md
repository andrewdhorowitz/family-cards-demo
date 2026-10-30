# Family Cards — DEMO (fake data only)

[![CI](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/ci.yml) [![Tests](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/tests.yml/badge.svg)](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/tests.yml) [![Smoke](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/smoke.yml/badge.svg)](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/smoke.yml) [![Lighthouse](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/lighthouse.yml/badge.svg)](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/lighthouse.yml) [![Links](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/links.yml/badge.svg)](https://github.com/andrewdhorowitz/family-cards-demo/actions/workflows/links.yml)

A public, self-contained demo of Family Cards — a small page that turns
the next two weeks into one simple card per kid. Everything here is
fake: invented kids ("Emma" / "Noah"), invented events, a fixed public
demo code. Nothing in this repo connects to a real calendar, account,
or family, and nothing here is a working copy of anything else.

> **Published:** Demo — https://demo.andrewdhorowitz.com/ · Interactive — https://demo.andrewdhorowitz.com/docs/interactive-architecture.html · Repo — https://github.com/andrewdhorowitz/family-cards-demo

**See it:** https://demo.andrewdhorowitz.com/ —
the demo's home is GitHub Pages (static hosting under the
`/family-cards-demo/` subpath). No code or sign-in is needed there:
with no gate answering, the page runs in open demo mode and shows both
cards with tabs, under a "Demo" banner.

- Where a gate does run (the Cloudflare-hosted variant, Phase 2
  below), what the page shows is decided by the access code's scope:
  a kid scope renders only that kid's card; an `owner` scope renders
  both cards with tabs — the same view the open mode shows.
- Emma's Nov 3 dance class shows a **CHANGED** tag with a third-party
  pickup ("Pickup: Grandma"); Noah's Nov 4 piano lesson shows a CHANGED
  tag for a moved time (new time only).
- `generate_cards.py` shows how the card files are produced: calendar
  events in (calendar IDs supplied through environment variables, so
  no account identifiers live in the repo), one JSON file per kid out.
  The demo JSON files committed here were written by hand to match its
  schema.
- The heading stamp reads **"Last changed: …"** — when the card's
  content last actually changed, not when it was last rebuilt. A
  CHANGED entry also carries its own "Updated …" time (visible on
  Emma's and Noah's CHANGED examples).

## Architecture

C4-lite diagrams (System Context inset + Container view, Mermaid,
diagrams-as-code) for this demo system — Emma / Noah only, generic
services, the three flows (publishing, access codes, kid notes):
[docs/architecture.md](docs/architecture.md). That file is the
canonical diagram source; it renders natively on GitHub, so there is
no second hand-maintained copy.

## Phase 2 — the auth/code gate (demo)
On GitHub Pages nothing server-side runs, so the gate below is inert
there: `functions/` and `codes.json` are plain static files (Jekyll
doesn't even copy the underscore-prefixed middleware), `codes.json`
holds only the hash of the public demo code, and the page's fetches
are all relative so they resolve under the subpath. Where the demo is
hosted on Cloudflare Pages, the gate in `functions/_middleware.js`
checks every request for a signed `fc_auth` cookie (HMAC-SHA256,
keyed by the `CODE_SECRET` environment variable, which must be set in
the hosting project's settings or the site fails closed with 401s).
A link with `?c=<token>` whose SHA-256 hash matches an entry in
`codes.json` mints that cookie and redirects to the clean URL.

The demo's one fixed public code is the word **demo**, with `owner`
scope (both cards, with tabs). Link format:

```
<demo site>/?c=demo
```

`mint_codes.py` is included so the minting mechanism is inspectable:
it generates tokens and stores only their hashes in `codes.json`.

## Kid-side notes (demo display only)
The cards show a "📝 Anything on your side?" note box (note text plus
optional date and optional estimated from/to times) **disabled**, with
"Demo — notes are turned off here." The endpoint behind it is a stub
that acknowledges and discards — nothing is stored or forwarded
anywhere in this repo.
