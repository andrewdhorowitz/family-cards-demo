# Family Cards — Architecture (Demo)

C4-lite diagrams for the Family Cards **demo**, drawn from the demo
system only: invented kids (**Emma** / **Noah**), invented events, and
no external services at all. Everything in this repo is sample
content. The demo connects to no account, calendar, form, or other
service — its only input is a bundled file of invented events
(`sample_events.json`), and its note box is decorative: the endpoint
answers and discards, and nothing is collected anywhere.

The page itself is deliberately simple for its readers: a rolling
two-week card, framed **With Dad / With Mom**, showing a kid's own
events first, highlighting non-school events as **Big**, showing a
pickup or drop-off only when Dad drives (the reader assumes Mom
otherwise), and marking exceptions with a single **CHANGED** tag.

This file is the canonical diagram source. It renders natively on
GitHub, and the same source feeds the project site — there is no
second, hand-maintained copy.

**Canonical pattern (v3, adopted Oct 28, 2026):** three views —
System Context (L1), Container (L2), and a Deployment / host view —
with shapes keyed to the kind of thing (see the legend under the
Deployment view) and hosts drawn as their own deployment nodes. An
interactive, draggable rendering of the Deployment view lives beside
this file at
[docs/interactive-architecture.html](interactive-architecture.html):
dragging there explores the view and never changes this source.

## Level 1 — System Context (inset)

Who uses the demo, and where its pieces live.

```mermaid
C4Context
    title Family Cards Demo - System Context (Emma / Noah)

    Person(kid, "Emma / Noah", "Kid viewers. Each reads only their own card.")
    Person(owner, "Dad", "Demo owner. Reads both cards, tabbed; mints the demo codes.")
    Person(parent, "Parent viewer", "Read-only. Reads both cards, logistics only.")

    System(fc, "Family Cards Demo", "Per-kid two-week cards behind expiring demo access codes, generated from bundled sample events.")

    System_Ext(gh, "GitHub", "This repo: page, gate, generator, sample data, and generated card data.")
    System_Ext(cf, "Cloudflare Pages", "Hosting and the server-side gate.")

    Rel(kid, fc, "Views own card")
    Rel(owner, fc, "Views both cards")
    Rel(parent, fc, "Views both cards")
    Rel(fc, gh, "Source and generated files live in the repo")
    Rel(gh, cf, "Deploys")
    Rel(cf, fc, "Serves the gated demo")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Level 2 — Container

Shapes are the native C4 shapes, so a type reads at a glance: a
**person figure** is a person, a **box** is a running container (the
UI page, a server function, a Python script), and a **cylinder** is
a data store. The generator and minter are plain Python scripts in
this repo that you run by hand — nothing is scheduled, and nothing
runs anywhere else.

```mermaid
C4Container
    title Family Cards Demo - Container View (Emma / Noah)

    Person(kid, "Emma / Noah", "Kid viewers.")
    Person(owner, "Dad", "Demo owner.")
    Person(parent, "Parent viewer", "Read-only.")

    System_Ext(repo, "GitHub Repository", "This repo: canonical source for page, gate, generator, sample data, and card data.")

    System_Boundary(fc, "Family Cards Demo") {

        Boundary(hosting, "Cloudflare Pages", "Hosting") {
            Container(gate, "Gate Middleware", "Pages Function, JavaScript", "Checks every request: redeems a demo code against stored hashes, sets a signed scoped cookie, enforces scope per file, and answers the note endpoint with a stub that discards.")
            Container(page, "Card Page", "Static HTML / JavaScript - the UI", "Renders one kid card, or both cards with tabs for owner and parent scopes. Shows Big and CHANGED tags and the disabled notes box.")
            ContainerDb(carddata, "Per-kid Card Data", "JSON files: emma.json, noah.json", "One file per kid: two-week window, With Dad / With Mom days, entries, legs, CHANGED tags, and a few invented sample notes.")
            ContainerDb(codes, "Access Code Hashes", "JSON file: codes.json", "SHA-256 hashes and expiries only. No plain codes are stored.")
        }

        Boundary(local, "This repo, on any computer", "Local scripts, run by hand") {
            Container(gen, "Card Generator", "Python", "Reads the bundled sample events, drops the sensitive sample entries, resolves drivers, applies the Big and CHANGED rules, and writes the per-kid JSON plus a build report.")
            Container(minter, "Code Minter", "Python", "Mints random per-scope expiring demo codes. Only hashes are committed.")
            ContainerDb(sample, "Sample Events", "JSON file: sample_events.json", "The invented events the generator practices on, grouped into three sample calendars. The generator's only input.")
            ContainerDb(snap, "Snapshots and Build Reports", "Local files", "Previous card per kid for the CHANGED diff, and a per-run report of how each leg was decided.")
        }
    }

    Rel(kid, gate, "Opens link with code, then browses with cookie", "HTTPS")
    Rel(owner, gate, "Opens owner link", "HTTPS")
    Rel(parent, gate, "Opens parent link", "HTTPS")
    Rel(gate, page, "Allows the verified scope")
    Rel(gate, codes, "Reads hashes and expiry")
    Rel(page, carddata, "Fetches own JSON for a kid scope, or all card JSON for owner / parent")
    Rel(gen, sample, "Reads the sample events")
    BiRel(gen, snap, "Diff vs previous card drives CHANGED tags; writes the build report")
    Rel(gen, carddata, "Writes per-kid JSON")
    Rel(minter, codes, "Writes hashes only")
    Rel(gen, repo, "Generated files are committed to the repo")
    Rel(minter, repo, "Hashes are committed to the repo")
    Rel(repo, gate, "Deploys page, gate, and data")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Deployment — Host view (v3)

Where each container actually runs: **GitHub** (repository hosting),
**Cloudflare Pages** (edge hosting), and **any computer** (the local
scripts and sample files, straight from a checkout of this repo).
People stand outside every host. There is no fourth host: no
external service is involved in the demo.

```mermaid
C4Deployment
    title Family Cards Demo - Deployment View (Emma / Noah)

    Person(kid, "Emma / Noah", "Kid viewers. Each reads only their own card.")
    Person(owner, "Dad", "Demo owner. Reads both cards, tabbed.")
    Person(parent, "Parent viewer", "Read-only. Reads both cards.")

    Deployment_Node(github, "GitHub", "Repository hosting") {
        Container(repo, "Family Cards Demo Repo", "Git repository", "Canonical source: page, gate, generator, sample data, this diagram. Plus the generated card data.")
    }

    Deployment_Node(cloudflare, "Cloudflare Pages", "Edge hosting") {
        Container(page, "Card Page", "Static HTML / JavaScript - UI screen", "Renders one kid card, or both with tabs. Shows Big and CHANGED tags and the disabled notes box.")
        Container(gate, "Gate Middleware", "Pages Function - server", "Redeems demo codes against stored hashes, sets a signed scoped cookie, enforces scope, and stubs the note endpoint.")
        ContainerDb(carddata, "Per-kid Card Data", "JSON files", "emma.json and noah.json. One file per kid.")
        ContainerDb(codes, "Access Code Hashes", "JSON file", "SHA-256 hashes and expiries only.")
    }

    Deployment_Node(local, "Any computer", "A checkout of this repo") {
        Container(gen, "Card Generator", "Python - worker", "Reads the sample events, filters, resolves drivers, applies Big and CHANGED, writes per-kid JSON and a build report.")
        Container(minter, "Code Minter", "Python - worker", "Mints expiring scoped demo codes. Only hashes are committed.")
        ContainerDb(sample, "Sample Events", "JSON file", "sample_events.json — invented events in three sample calendars.")
        ContainerDb(snap, "Snapshots and Build Reports", "Local files", "CHANGED diff baseline; per-run leg-decision report.")
    }

    Rel(kid, gate, "Opens coded link, then browses with cookie", "HTTPS")
    Rel(owner, gate, "Opens owner link", "HTTPS")
    Rel(parent, gate, "Opens parent link", "HTTPS")
    Rel(gate, page, "Allows the verified scope")
    Rel(gate, codes, "Reads hashes and expiry")
    Rel(page, carddata, "Fetches card JSON by scope")
    Rel(gen, sample, "Reads the sample events")
    BiRel(gen, snap, "Diff drives CHANGED tags; writes the build report")
    Rel(gen, carddata, "Writes per-kid JSON")
    Rel(minter, codes, "Writes hashes only")
    Rel(gen, repo, "Generated files are committed")
    Rel(minter, repo, "Hashes are committed")
    Rel(repo, page, "Deploys page, gate, and data to Cloudflare")

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

### Shape and host legend

| Visual | Means | Family Cards Demo examples |
|---|---|---|
| Person figure | A human user | Emma / Noah, Dad, Parent viewer |
| Browser window | A user screen / UI | Card Page |
| Server rack | A server / server-side function | Gate Middleware |
| Gear | A worker / local script | Card Generator, Code Minter |
| Cylinder | A database / data store | Per-kid Card Data, Access Code Hashes, Sample Events, Snapshots |
| Repository | A source / code store | GitHub repo |

## The three flows

**1. Building a card (local, from sample data).** The generator
reads the bundled sample events for the rolling two-week window,
drops the sample entries in sensitive categories, frames each day
With Dad or With Mom, resolves pickup and drop-off drivers (an
explicit tag or transport name first, then driver proof from a
matching travel block in the sample data, then the sample exception
lists, then the day-and-cutoff rule), and keeps only the legs Dad
drives — plus any third-party leg, which is named and tagged
CHANGED. Entries whose time moved since the previous snapshot are
tagged CHANGED with the new time only. The generator writes one
JSON file per kid; the files are committed; the host deploys them;
the page just renders the latest file.

**2. Getting in (demo codes, not accounts).** Each demo link
carries a one-time access code. The gate hashes the code and
matches it against `codes.json`; on a match it sets a signed,
scoped, expiring cookie (HMAC-SHA256, keyed by a hosting secret)
and redirects to the clean URL. A kid scope can fetch only that
kid's JSON; owner and parent scopes can fetch both. An unknown or
expired code fails closed. When the hosting secret is not
configured, the gate fails closed for everyone. On plain static
hosting (GitHub Pages) no gate runs at all, and the demo simply
opens both cards with tabs — which is why the demo banner shows
there.

**3. Notes (decorative in the demo).** The note box on each card
shows how a kid would send a note — text plus an optional date and
optional estimated times, a guess being fine. In this demo the box
is disabled and the `/note` endpoint returns a stub acknowledgement
and discards the submission. There is no inbox, no forwarding, and
no collection of anything; the only notes visible are the invented
ones baked into the sample card files.

## Containers at a glance

| Container | Shape in diagram | Runs on | Responsibility |
|---|---|---|---|
| Card Page | Browser window - UI screen | Cloudflare Pages (static) | Render one card, or both with tabs; Big / CHANGED display; disabled note box |
| Gate Middleware | Server rack - server function | Cloudflare Pages Function | Demo-code redemption, signed scoped cookies, per-file scope enforcement, `/scope.json`, `/note` stub |
| Per-kid Card Data | Cylinder - data store | Static JSON in this repo | The only thing the page renders; one file per kid |
| Access Code Hashes | Cylinder - data store | Static JSON in this repo | Hashes and expiries for scoped demo codes; nothing plain |
| Card Generator | Gear - worker | Any computer (Python) | Sample events in, per-kid JSON out; all card rules live here |
| Code Minter | Gear - worker | Any computer (Python) | Mint expiring scoped demo codes; commit hashes only |
| Sample Events | Cylinder - data store | This repo (JSON file) | The generator's only input; invented events in three sample calendars |
| Snapshots and Build Reports | Cylinder - data store | Local files | CHANGED diff baseline; per-run leg-decision report |

## What this demo is — and is not

Everything here is invented: the kids, the events, the places, the
codes. The demo runs entirely from this repo — sample file in,
static cards out — and connects to no calendar, account, form, or
other service. It exists to show the card design, the code-gate
pattern, and the generator's rule set on data anyone can inspect.
