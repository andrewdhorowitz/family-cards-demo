# Family Cards — Architecture

C4-lite diagrams for Family Cards, drawn from the **demo** system only:
invented kids (**Emma** / **Noah**), invented events, and generic external
services. No real family data, addresses, calendar identifiers, or secrets
appear here — or anywhere in this repo.

The page itself is deliberately simple for its readers: a rolling two-week
card, framed **With Dad / With Mom**, showing a kid's own events first,
highlighting non-school events as **Big**, showing a pickup or drop-off
only when Dad drives (the reader assumes Mom otherwise), and marking
exceptions with a single **CHANGED** tag.

This file is the canonical diagram source. It renders natively on GitHub,
and the same Mermaid source feeds the showcase site — there is no second,
hand-maintained copy.

**Canonical pattern (v3, adopted Oct 28, 2026):** three views — System
Context (L1), Container (L2), and a Deployment / host view — with
shapes keyed to the kind of thing (see the legend under the Deployment
view) and hosts drawn as their own deployment nodes. An interactive,
draggable rendering of the Deployment view lives beside this file at
[docs/interactive-architecture.html](interactive-architecture.html):
dragging there explores the view and never changes this source.

## Level 1 — System Context (inset)

Who uses Family Cards, and which outside systems it touches.

```mermaid
C4Context
    title Family Cards - System Context (demo: Emma / Noah)

    Person(kid, "Emma / Noah", "Kid viewers. Each reads only their own card, and can send a note.")
    Person(owner, "Dad", "Owner. Reads both cards, tabbed.")
    Person(parent, "Parent viewer", "Read-only. Reads both cards, logistics only.")

    System(fc, "Family Cards", "Per-kid two-week cards behind expiring access codes.")

    System_Ext(cal, "Google Calendar", "Source calendars, read on the assistant side only.")
    System_Ext(form, "Google Form", "Kid-notes inbox. Full flow only; stubbed in the demo.")
    System_Ext(gh, "GitHub", "This repo: page, generator, and generated card data.")
    System_Ext(cf, "Cloudflare Pages", "Hosting and the server-side gate.")

    Rel(kid, fc, "Views own card, sends notes")
    Rel(owner, fc, "Views both cards")
    Rel(parent, fc, "Views both cards")
    Rel(fc, cal, "Generator reads events", "No calendar credential lives on the web host")
    Rel(fc, form, "Stores notes as form responses", "Full flow only")
    Rel(fc, gh, "Pushes generated files")
    Rel(gh, cf, "Deploys")
    Rel(cf, fc, "Serves the gated site")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Level 2 — Container

Shapes are the native C4 shapes, so a type reads at a glance: a
**person figure** is a person, a **box** is a running container (the
UI page, a server function, a Python job), a **cylinder** is a data
store, and a **grey system** is an external service. The notes path
is the designed full flow: in this demo repo the note box is shown
disabled and the `/note` endpoint is a stub that acknowledges and
discards, so no form is referenced here.

```mermaid
C4Container
    title Family Cards - Container View (demo: Emma / Noah)

    Person(kid, "Emma / Noah", "Kid viewers.")
    Person(owner, "Dad", "Owner.")
    Person(parent, "Parent viewer", "Read-only.")

    System_Ext(cal, "Google Calendar", "Primary, Family, and Kids calendars (generic labels).")
    System_Ext(form, "Google Form", "Kid-notes inbox. Full flow only.")
    System_Ext(repo, "GitHub Repository", "This repo: canonical source for page, gate, generator, and card data.")

    System_Boundary(fc, "Family Cards") {

        Boundary(hosting, "Cloudflare Pages", "Hosting") {
            Container(gate, "Gate Middleware", "Pages Function, JavaScript", "Checks every request: redeems a code against stored hashes, sets a signed scoped cookie, enforces scope per file, serves scope, and handles the note endpoint.")
            Container(page, "Card Page", "Static HTML / JavaScript - the UI", "Renders one kid card, or both cards with tabs for owner and parent scopes. Shows Big and CHANGED tags and the kid-notes box.")
            Container(noteep, "Note Endpoint", "Pages Function route, in the gate", "Attributes a note from the verified cookie, never from client input, and validates the text. Demo: stub that discards.")
            ContainerDb(carddata, "Per-kid Card Data", "JSON files: emma.json, noah.json", "One file per kid: two-week window, With Dad / With Mom days, entries, legs, CHANGED tags, own notes only.")
            ContainerDb(codes, "Access Code Hashes", "JSON file: codes.json", "SHA-256 hashes and expiries only. No plain codes are stored.")
        }

        Boundary(assistant, "Assistant side", "Scheduled automation, off the web host") {
            Container(sched, "Scheduled Rebuilds and Watches", "Scheduled jobs", "Morning and nightly rebuilds, plus rebuilds when a change is spotted.")
            Container(gen, "Card Generator", "Python", "Filters sensitive and admin events out, resolves drivers, applies the Big and CHANGED rules, folds in kid notes, and writes the per-kid JSON.")
            Container(minter, "Code Minter", "Python", "Mints random per-scope expiring codes in batches. Only hashes are committed.")
            Container(watch, "Notes Watch", "Scheduled job", "Polls the notes inbox, reports each new note to Dad verbatim, then triggers a regeneration. Full flow only.")
            ContainerDb(snap, "Snapshots and Notes State", "Files, kept outside the repo", "Previous card per kid for the CHANGED diff. Seen-note IDs for dedupe.")
        }
    }

    Rel(kid, gate, "Opens link with code, then browses with cookie", "HTTPS")
    Rel(owner, gate, "Opens owner link", "HTTPS")
    Rel(parent, gate, "Opens parent link", "HTTPS")
    Rel(gate, page, "Allows the verified scope")
    Rel(gate, codes, "Reads hashes and expiry")
    Rel(page, carddata, "Fetches own JSON for a kid scope, or all card JSON for owner / parent")
    Rel(page, noteep, "Posts a note: text plus optional date and time guess", "Demo: box disabled")
    Rel(noteep, form, "Forwards the attributed note", "Full flow only")
    Rel(watch, form, "Reads new responses, dedupes by response ID")
    Rel(watch, gen, "New note: notify Dad, then regenerate")
    Rel(sched, gen, "Triggers")
    Rel(gen, cal, "Reads events for the rolling two-week window")
    BiRel(gen, snap, "Diff vs previous card drives CHANGED tags and the Last changed stamp")
    Rel(gen, carddata, "Writes per-kid JSON, each kid notes in their own file only")
    Rel(minter, codes, "Writes hashes only")
    Rel(gen, repo, "Pushes updated card data")
    Rel(minter, repo, "Pushes updated hashes")
    Rel(repo, gate, "Deploys page, gate, and data")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Deployment — Host view (v3)

Where each container actually runs. Every host is its own deployment
node, in its own colour in the interactive rendering: **GitHub**
(repository hosting), **Cloudflare Pages** (edge hosting), **Muse —
assistant side** (automation runtime, off the web host), and **Google**
(external services). People stand outside every host.

```mermaid
C4Deployment
    title Family Cards - Deployment View (demo: Emma / Noah)

    Person(kid, "Emma / Noah", "Kid viewers. Each reads only their own card.")
    Person(owner, "Dad", "Owner. Reads both cards, tabbed.")
    Person(parent, "Parent viewer", "Read-only. Reads both cards.")

    Deployment_Node(github, "GitHub", "Repository hosting") {
        Container(repo, "Family Cards Demo Repo", "Git repository", "Canonical source: page, gate, generator, this diagram. Plus the generated card data.")
    }

    Deployment_Node(cloudflare, "Cloudflare Pages", "Edge hosting") {
        Container(page, "Card Page", "Static HTML / JavaScript - UI screen", "Renders one kid card, or both with tabs. Shows Big and CHANGED tags and the notes box.")
        Container(gate, "Gate Middleware", "Pages Function - server", "Redeems codes against stored hashes, sets a signed scoped cookie, enforces scope, serves scope, handles the note endpoint.")
        ContainerDb(carddata, "Per-kid Card Data", "JSON files", "emma.json and noah.json. One file per kid, own notes only.")
        ContainerDb(codes, "Access Code Hashes", "JSON file", "SHA-256 hashes and expiries only.")
    }

    Deployment_Node(muse, "Muse - assistant side", "Automation runtime, off the web host") {
        Container(gen, "Card Generator", "Python - worker", "Reads calendars, filters, resolves drivers, applies Big and CHANGED, folds notes, writes per-kid JSON.")
        Container(minter, "Code Minter", "Python - worker", "Mints expiring scoped codes. Only hashes are committed.")
        Container(watch, "Notes Watch and Scheduled Rebuilds", "Scheduled jobs - workers", "Morning and nightly rebuilds, on-change rebuilds, new-note alerts to Dad.")
        ContainerDb(snap, "Snapshots and Notes State", "Files, outside the repo", "CHANGED diff baseline. Seen-note IDs for dedupe.")
    }

    Deployment_Node(google, "Google", "External services") {
        Container_Ext(cal, "Google Calendar", "External service - cloud", "Source calendars, read on the assistant side only.")
        Container_Ext(form, "Google Form", "External service - cloud", "Kid-notes inbox. Full flow only; stubbed in the demo.")
    }

    Rel(kid, gate, "Opens coded link, then browses with cookie", "HTTPS")
    Rel(owner, gate, "Opens owner link", "HTTPS")
    Rel(parent, gate, "Opens parent link", "HTTPS")
    Rel(gate, page, "Allows the verified scope")
    Rel(gate, codes, "Reads hashes and expiry")
    Rel(page, carddata, "Fetches card JSON by scope")
    Rel(page, gate, "Posts a note to the note endpoint", "Demo: box disabled")
    Rel(gate, form, "Forwards the attributed note", "Full flow only")
    Rel(watch, form, "Polls new note responses")
    Rel(watch, gen, "New note: alert Dad, then regenerate")
    Rel(gen, cal, "Reads events, rolling two-week window")
    BiRel(gen, snap, "Diff drives CHANGED tags")
    Rel(gen, carddata, "Writes per-kid JSON")
    Rel(minter, codes, "Writes hashes only")
    Rel(gen, repo, "Pushes generated card data")
    Rel(minter, repo, "Pushes updated hashes")
    Rel(repo, page, "Deploys page, gate, and data to Cloudflare")

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

### Shape and host legend

| Visual | Means | Family Cards examples |
|---|---|---|
| Person figure | A human user | Emma / Noah, Dad, Parent viewer |
| Browser window | A user screen / UI | Card Page |
| Server rack | A server / server-side function | Gate Middleware, Note Endpoint |
| Gear | A worker / background or scheduled job | Card Generator, Code Minter, Notes Watch, Scheduled Rebuilds |
| Cylinder | A database / data store | Per-kid Card Data, Access Code Hashes, Snapshots and Notes State |
| Cloud | An external hosted service | Google Calendar, Google Form |
| Repository | A source / code store | GitHub repo |

## The three flows

**1. Publishing a card (push, never pull).** The page never calls a
calendar API and no calendar credential lives on the web host. On the
assistant side, the generator reads the source calendars for the rolling
two-week window, drops sensitive and administrative events, frames each
day With Dad or With Mom, resolves pickup and drop-off drivers (an
explicit tag or transport name first, then driver proof from a matching
travel block, then the day-and-time rule), and keeps only the legs Dad
drives — plus any third-party leg, which is named and tagged CHANGED.
Entries whose time moved since the previous snapshot are tagged CHANGED
with the new time only. The generator writes one JSON file per kid and
pushes it; the host deploys it; the page just renders the latest file.

**2. Getting in (codes, not accounts).** Each link carries a one-time
access code. The gate hashes the code and matches it against
`codes.json`; on a match it sets a signed, scoped, expiring cookie
(HMAC-SHA256, keyed by a hosting secret) and redirects to the clean URL.
A kid scope can fetch only that kid's JSON; owner and parent scopes can
fetch both. An unknown or expired code fails closed. When the hosting
secret is not configured, the gate fails closed for everyone.

**3. Notes from a kid (designed full flow; stubbed in the demo).** A kid
writes in the note box on her or his own card — text plus an optional
date and optional estimated times, a guess being fine. The page posts to
the same-origin `/note` endpoint; the gate attributes the note from the
verified cookie, never from anything the client sends, and forwards it
to a Google Form that is never linked publicly. The notes watch polls
for new responses, reports each one to Dad verbatim, and triggers a
regeneration; the generator folds each kid's own notes into that kid's
JSON only, so the two cards stay isolated from each other. In this demo
the box is disabled and `/note` returns a stub acknowledgement and
discards the submission.

## Containers at a glance

| Container | Shape in diagram | Runs on | Responsibility |
|---|---|---|---|
| Card Page | Browser window - UI screen | Cloudflare Pages (static) | Render one card, or both with tabs; Big / CHANGED display; note box |
| Gate Middleware | Server rack - server function | Cloudflare Pages Function | Code redemption, signed scoped cookies, per-file scope enforcement, `/scope.json`, `/note` |
| Note Endpoint | Server rack - server route | In the gate (`/note`) | Attribute from the cookie, validate, forward (stub in demo) |
| Per-kid Card Data | Cylinder - data store | Static JSON in this repo | The only thing the page renders; one file per kid |
| Access Code Hashes | Cylinder - data store | Static JSON in this repo | Hashes and expiries for scoped codes; nothing plain |
| Card Generator | Gear - worker | Assistant side (Python) | Calendars in, per-kid JSON out; all card rules live here |
| Code Minter | Gear - worker | Assistant side (Python) | Mint expiring scoped codes; commit hashes only |
| Scheduled Rebuilds and Watches | Gear - scheduled worker | Assistant side (scheduled jobs) | Morning / nightly / on-change regeneration triggers |
| Notes Watch | Gear - scheduled worker | Assistant side (scheduled job) | New-note alerts to Dad, then regeneration (full flow only) |
| Snapshots and Notes State | Cylinder - data store | Assistant side (files, outside the repo) | CHANGED diff baseline; note dedupe |

## Demo vs private

The demo and the private system run the same page, gate, minter, and
generator code. They differ only in data and in the notes endpoint:
the demo's card JSON is hand-written fake data for Emma and Noah, its
one public code is fixed and owner-scoped, and its notes flow stops at
the stub. Nothing about the private system's data, codes, calendars,
or form appears in this repo.
