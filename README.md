# Free Fact-Check Directory

A directory of free fact-checking sources and tools, plus plain-English
checklists and a shareable "verify before you forward" card for group chats.

Built in the friendly, plain-English style of
[Dylan Asdale](https://dylanasdale.github.io/) and
**Asdale Dynamics, LLC**: step by step, never condescending, and always
free to use. Every entry was added by hand, links to official sites only,
and contains no affiliate links or tracking parameters.

## What is in here

| Page | What it covers |
| --- | --- |
| `content/sources.md` | Fact-check sites (Snopes, PolitiFact, AP, Reuters, FactCheck.org) and official-data pages (CDC, Census Bureau, IRS) |
| `content/tools.md` | Reverse-image search routes and archive/cache lookups |
| `content/checklists.md` | Media-frames checklists for health, money, and weather rumors |
| `content/share-card.md` | A group-chat card teaching "verify before you forward" |

## Run it

Requires Python 3 (standard library only, no installs):

```sh
python3 build.py          # builds the static site into site/
python3 build.py --test   # runs the build + render/quality checks
```

Then open `site/index.html` in a browser. Regenerate any time you edit
something under `content/`.

## How it differs from sibling projects

- **spot-fake-media-guide** explains *how* fake-media detection works.
  This directory is *where to check* — a lookup of free sources and tools.
- **link-safety-inspector-cli** is a command-line *tool* you run against a
  link. This directory is *docs plus a static HTML site*.

The three are complementary: read the guide to learn the method, use the
CLI to inspect a link, and use this directory to find the right source.

## Design rules

- All entries are curated manually; nothing is scraped or auto-listed.
- Only free resources. Free tiers are noted when a paid tier exists.
- No affiliate links, no referral parameters, no ads, no trackers.
- The site is fully static and works offline after you build it.

## License

MIT — see `LICENSE`. Copyright (c) 2026 Asdale Dynamics, LLC.
