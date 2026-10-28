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

## Level 1 — System Context (inset)

Who uses Family Cards, and which outside systems it touches.

```mermaid
flowchart LR
    kid["Emma / Noah<br/>[Person — kid viewers]<br/>Each reads only her or his own card"]
    owner["Dad<br/>[Person — owner]<br/>Reads both cards, tabbed"]
    parent["Parent viewer<br/>[Person — read-only]<br/>Both cards, logistics only"]
    fc["Family Cards<br/>[Software System]<br/>Per-kid two-week cards<br/>behind expiring access codes"]
    cal["Google Calendar<br/>[External system]<br/>Source calendars, read<br/>on the assistant side only"]
    form["Google Form<br/>[External system]<br/>Kid-notes inbox<br/>(full flow — stubbed in demo)"]
    gh["GitHub<br/>[External system]<br/>This repo: page, generator,<br/>and generated card data"]
    cf["Cloudflare Pages<br/>[External system]<br/>Hosting and the<br/>server-side gate"]

    kid -->|"Views own card<br/>and can send a note"| fc
    owner -->|"Views both cards"| fc
    parent -->|"Views both cards"| fc
    fc -->|"Generator reads events<br/>(no calendar credential<br/>ever lives on the web host)"| cal
    fc -.->|"Notes are stored as<br/>form responses"| form
    fc -->|"Generated files are<br/>pushed to the repo"| gh
    gh -->|"Deploys"| cf
    cf -->|"Serves the gated site"| fc

    classDef person fill:#08427b,color:#ffffff,stroke:#052e56
    classDef system fill:#1168bd,color:#ffffff,stroke:#0b4884
    classDef external fill:#999999,color:#ffffff,stroke:#666666
    class kid,owner,parent person
    class fc system
    class cal,form,gh,cf external
```

## Level 2 — Container

The deployable and runnable pieces inside Family Cards, and how they
talk to each other. Solid arrows are live in the demo. The dashed notes
path is the designed full flow: in this demo repo the note box is shown
disabled and the `/note` endpoint is a stub that acknowledges and
discards, so no form is referenced here.

```mermaid
flowchart TB
    kid["Emma / Noah<br/>[Person — kid viewers]"]
    owner["Dad<br/>[Person — owner]"]
    parent["Parent viewer<br/>[Person — read-only]"]

    subgraph fc["Family Cards — Software System"]
        subgraph hosting["Hosted on Cloudflare Pages"]
            gate["Gate Middleware<br/>[Container — Pages Function, JavaScript]<br/>Checks every request: redeems an access<br/>code against stored hashes, sets a signed<br/>cookie, enforces scope per file, serves<br/>/scope.json, and handles /note"]
            page["Card Page<br/>[Container — static HTML / JavaScript]<br/>Renders one kid card, or both cards<br/>with tabs for owner / parent scopes;<br/>shows Big and CHANGED tags and<br/>the kid-notes box"]
            noteep["Note Endpoint<br/>[Container — /note, in the gate]<br/>Attributes a note from the verified<br/>cookie — never from client input —<br/>and validates the text"]
            carddata[("Per-kid Card Data<br/>[Container — JSON: emma.json, noah.json]<br/>One file per kid: two-week window,<br/>With Dad / With Mom days, entries,<br/>legs, CHANGED tags, own notes only")]
            codes[("Access Code Hashes<br/>[Container — JSON: codes.json]<br/>SHA-256 hashes and expiries only;<br/>no plain codes are stored")]
        end

        subgraph assistant["Assistant side — scheduled automation, off the web host"]
            sched["Scheduled Rebuilds and Watches<br/>[Container — scheduled jobs]<br/>Morning and nightly rebuilds, plus<br/>rebuilds when a change is spotted"]
            gen["Card Generator<br/>[Container — Python]<br/>Filters sensitive and admin events out,<br/>resolves drivers, applies the Big and<br/>CHANGED rules, folds in kid notes,<br/>and writes the per-kid JSON"]
            minter["Code Minter<br/>[Container — Python]<br/>Mints random per-scope expiring<br/>codes in batches; only hashes<br/>are committed"]
            watch["Notes Watch<br/>[Container — scheduled job]<br/>Polls the notes inbox, reports each<br/>new note to Dad verbatim, then<br/>triggers a regeneration"]
            snap[("Snapshots and Notes State<br/>[Container — files, kept outside the repo]<br/>Previous card per kid for the<br/>CHANGED diff; seen-note IDs<br/>for dedupe")]
        end
    end

    cal["Google Calendar<br/>[External system]<br/>Primary, Family, and Kids<br/>calendars (generic labels)"]
    form["Google Form<br/>[External system]<br/>Kid-notes inbox<br/>(full flow only)"]
    repo["GitHub Repository — this repo<br/>[External system]<br/>Canonical source for the page,<br/>gate, generator, and card data"]

    kid -->|"Opens link with code,<br/>then browses with cookie"| gate
    owner -->|"Opens owner link"| gate
    parent -->|"Opens parent link"| gate
    gate -->|"Scope allowed"| page
    gate -->|"Reads hashes and expiry"| codes
    page -->|"Fetches own JSON (kid scope)<br/>or all card JSON (owner / parent)"| carddata
    page -.->|"POST /note — note text plus<br/>optional date and time guess"| noteep
    noteep -.->|"Forwards the attributed note"| form
    watch -.->|"Reads new responses,<br/>dedupes by response ID"| form
    watch -.->|"New note: notify Dad,<br/>then regenerate"| gen
    sched -->|"Triggers"| gen
    gen -->|"Reads events for the<br/>rolling two-week window"| cal
    gen <-->|"Diff vs previous card<br/>drives CHANGED tags<br/>and the Last changed stamp"| snap
    gen -->|"Writes per-kid JSON,<br/>each kid's notes in her<br/>or his file only"| carddata
    minter -->|"Writes hashes only"| codes
    gen -->|"Pushes updated<br/>card data"| repo
    minter -->|"Pushes updated hashes"| repo
    repo -->|"Deploys page, gate,<br/>and data"| hosting

    classDef person fill:#08427b,color:#ffffff,stroke:#052e56
    classDef container fill:#1168bd,color:#ffffff,stroke:#0b4884
    classDef db fill:#1168bd,color:#ffffff,stroke:#0b4884
    classDef external fill:#999999,color:#ffffff,stroke:#666666
    class kid,owner,parent person
    class gate,page,noteep,sched,gen,minter,watch container
    class carddata,codes,snap db
    class cal,form,repo external
```

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

| Container | Runs on | Responsibility |
|---|---|---|
| Card Page | Cloudflare Pages (static) | Render one card, or both with tabs; Big / CHANGED display; note box |
| Gate Middleware | Cloudflare Pages Function | Code redemption, signed scoped cookies, per-file scope enforcement, `/scope.json`, `/note` |
| Note Endpoint | In the gate (`/note`) | Attribute from the cookie, validate, forward (stub in demo) |
| Per-kid Card Data | Static JSON in this repo | The only thing the page renders; one file per kid |
| Access Code Hashes | Static JSON in this repo | Hashes and expiries for scoped codes; nothing plain |
| Card Generator | Assistant side (Python) | Calendars in, per-kid JSON out; all card rules live here |
| Code Minter | Assistant side (Python) | Mint expiring scoped codes; commit hashes only |
| Scheduled Rebuilds and Watches | Assistant side (scheduled jobs) | Morning / nightly / on-change regeneration triggers |
| Notes Watch | Assistant side (scheduled job) | New-note alerts to Dad, then regeneration (full flow only) |
| Snapshots and Notes State | Assistant side (files, outside the repo) | CHANGED diff baseline; note dedupe |

## Demo vs private

The demo and the private system run the same page, gate, minter, and
generator code. They differ only in data and in the notes endpoint:
the demo's card JSON is hand-written fake data for Emma and Noah, its
one public code is fixed and owner-scoped, and its notes flow stops at
the stub. Nothing about the private system's data, codes, calendars,
or form appears in this repo.
