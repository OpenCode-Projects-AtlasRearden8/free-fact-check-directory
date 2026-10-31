import argparse
import html as html_mod
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
SITE = ROOT / "site"

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

TITLE = "Free Fact-Check Directory"
DESCRIPTION = ("Free fact-checking sources, verification tools, "
               "media-frames checklists, and a group-chat share card.")
FOOTER = ('This directory is a project of Asdale Dynamics, LLC — '
          'MIT licensed, no affiliate links, no tracking.')

PAGES = [
    ("sources", "Fact-checking sources",
     "Snopes, PolitiFact, AP and Reuters fact checks, plus official "
     "CDC, Census, and IRS data pages."),
    ("tools", "Verification tools",
     "Reverse-image search routes and archive or cache lookups."),
    ("checklists", "Media-frames checklists",
     "Five-question frame checks for health, money, and weather rumors."),
    ("share-card", "Group-chat share card",
     "A copy-paste card that teaches verify-before-forward."),
]

STYLE = """
:root { --ink:#1c2733; --paper:#fdfcf9; --accent:#0b66c3; --line:#e3ded4; }
* { box-sizing: border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
  font:17px/1.65 Georgia, "Times New Roman", serif; }
a { color:var(--accent); text-decoration-thickness:1px; text-underline-offset:2px; }
a:hover { text-decoration-thickness:2px; }
code { background:#f1ede4; border:1px solid var(--line); border-radius:4px;
  padding:.1em .35em; font:0.88em/1.4 ui-monospace, Menlo, Consolas, monospace; }
pre { background:#f1ede4; border:1px solid var(--line); border-radius:6px;
  padding:.8em 1em; overflow-x:auto; }
pre code { border:none; background:none; padding:0; }
header.site { border-bottom:2px solid var(--accent); background:#fff; }
.site-inner { max-width:760px; margin:0 auto; padding:1rem; display:flex;
  flex-wrap:wrap; align-items:baseline; gap:1rem; justify-content:space-between; }
.brand { font-family:ui-monospace, Menlo, monospace; font-size:.95rem;
  font-weight:bold; text-decoration:none; color:var(--ink); }
nav a { margin-left:1rem; font-size:.92rem; text-decoration:none;
  font-family:ui-monospace, Menlo, monospace; }
nav a:hover { text-decoration:underline; }
main { max-width:760px; margin:0 auto; padding:1.5rem 1rem 3rem; }
h1 { font-size:1.9rem; line-height:1.25; margin:.4rem 0 1rem; }
h2 { margin-top:2.4rem; border-bottom:1px solid var(--line); padding-bottom:.3rem; }
h3 { margin-top:1.8rem; }
blockquote { border-left:3px solid var(--accent); margin:1rem 0; padding:.2rem 1rem; color:#3c4a58; }
table { border-collapse:collapse; width:100%; font-size:.95rem; }
th, td { border:1px solid var(--line); padding:.45rem .6rem; text-align:left; }
th { background:#f1ede4; }
li { margin:.3rem 0; }
hr { border:none; border-top:1px dashed var(--line); margin:2rem 0; }
footer { border-top:1px solid var(--line); text-align:center; font-size:.85rem;
  color:#5a6674; padding:1rem; font-family:ui-monospace, Menlo, monospace; }
.entry { background:#fff; border:1px solid var(--line); border-radius:8px;
  padding:1rem 1.2rem; margin:1.2rem 0; }
.entry h2 { border:none; margin:.1rem 0 .4rem; }
.toc { columns:2; gap:1.5rem; padding-left:1.2rem; font-size:.93rem; }
.toc li { margin:.2rem 0; }
.tagline { color:#3c4a58; }
.lead { font-size:1.05rem; }
"""

SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site">
  <div class="site-inner">
    <a class="brand" href="index.html">free-fact-check-directory</a>
    <nav>{nav}</nav>
  </div>
</header>
<main>
{body}
</main>
<footer>{footer}</footer>
</body>
</html>
"""


def esc(text):
    return html_mod.escape(text, quote=False)


def slug(text):
    t = re.sub(r"[^a-z0-9\s-]", "", text.lower())
    t = re.sub(r"\s+", "-", t).strip("-")
    return t or "section"


URL_RE = re.compile(r"https?://[^\s<>`\"']+")


def trim_url_tail(url):
    trail = ""
    while url:
        last = url[-1]
        if last in ".,;:!?":
            trail = last + trail
            url = url[:-1]
            continue
        if last == ")" and url.count("(") < url.count(")"):
            trail = ")" + trail
            url = url[:-1]
            continue
        break
    return url, trail


def autolink(text):
    def repl(match):
        url, trail = trim_url_tail(match.group(0))
        if not url:
            return match.group(0)
        return '<a href="%s">%s</a>%s' % (url, esc(url), trail)
    return URL_RE.sub(repl, text)


def inline(text):
    codes = []
    def stash(match):
        codes.append(match.group(1))
        return "\x00%d\x00" % (len(codes) - 1)
    text = esc(text)
    text = re.sub(r"`([^`]+)`", stash, text)
    text = autolink(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>"
                  % esc(codes[int(m.group(1))]), text)
    return text


TABLE_SEP = re.compile(r"^\|[\s:|-]+\|$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^[-*]\s+(.*)$")
ORDERED = re.compile(r"^\d+\.\s+(.*)$")


def render_markdown(source):
    lines = source.splitlines()
    out = []
    i = 0
    n = len(lines)
    para = []
    list_tag = None
    list_items = []

    def close_para():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []

    def close_list():
        nonlocal list_tag, list_items
        if list_tag:
            out.append("".join("<li>%s</li>" % inline(item)
                               for item in list_items))
            out.append("</%s>" % list_tag)
            list_tag = None
            list_items = []

    while i < n:
        line = lines[i]
        stripped = line.strip()
        raw_bullet = re.match(r"^([-*])\s+(.*)$", line)
        raw_ordered = re.match(r"^(\d+)\.\s+(.*)$", line)
        indented = len(line) - len(line.lstrip()) > 0

        if not stripped:
            close_para()
            close_list()
            i += 1
            continue

        fence = re.match(r"^```(\w*)\s*$", stripped)
        if fence:
            close_para()
            close_list()
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % esc("\n".join(block)))
            continue

        heading = HEADING.match(stripped)
        if heading:
            close_para()
            close_list()
            level = len(heading.group(1))
            text = heading.group(2)
            out.append('<h%d id="%s">%s</h%d>'
                       % (level, slug(text), inline(text), level))
            i += 1
            continue

        if stripped == "---":
            close_para()
            close_list()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < n and TABLE_SEP.match(lines[i + 1].strip()):
            close_para()
            close_list()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            thead = "".join("<th>%s</th>" % inline(c) for c in header)
            tbody = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c)
                                                    for c in row) for row in rows)
            out.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>"
                       % (thead, tbody))
            continue

        in_list = (raw_bullet or raw_ordered) and not indented
        if in_list:
            close_para()
            tag = "ol" if raw_ordered else "ul"
            if list_tag != tag:
                close_list()
                out.append("<%s>" % tag)
                list_tag = tag
            text = (raw_bullet.group(2) if raw_bullet else raw_ordered.group(2))
            checkbox = re.match(r"^\[( |x)\]\s*(.*)$", text, re.IGNORECASE)
            if checkbox:
                mark = "☑" if checkbox.group(1).lower() == "x" else "☐"
                text = "%s %s" % (mark, checkbox.group(2))
            list_items.append(text)
            i += 1
            continue

        if indented and list_tag and not raw_bullet and not raw_ordered:
            list_items[-1] += " " + stripped
            i += 1
            continue

        close_list()
        para.append(stripped)
        i += 1

    close_para()
    close_list()
    return "\n".join(out)


def nav_links(current_slug):
    links = ['<a href="index.html"%s>Home</a>'
             % (' class="on"' if current_slug == "index" else "")]
    for slug_, title, _ in PAGES:
        on = ' class="on"' if slug_ == current_slug else ""
        links.append('<a href="%s.html"%s>%s</a>' % (slug_, on, title))
    return "".join(links)


def page(title, description, body):
    return SHELL.format(title=esc(title), desc=esc(description),
                        body=body, footer=esc(FOOTER),
                        nav="")


def main_body(title, html):
    intro = ('<p class="lead">A hand-checked directory of free sources '
             "and tools for verifying viral posts — and the checklists "
             "worth saving before you forward anything. Every link goes "
             "to an official site or a free tool; nothing here is an "
             "affiliate link.</p>")
    return "<h1>%s</h1>%s%s" % (esc(title), intro, html)


def collect_hrefs_and_ids(path):
    checker = StructureChecker()
    checker.feed(path.read_text(encoding="utf-8"))
    return checker


def collect_h1(path):
    checker = collect_hrefs_and_ids(path)
    joined = "".join(checker.text)
    return checker


class StructureChecker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.hrefs = []
        self.ids = set()
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if "href" in attrs:
            self.hrefs.append(attrs["href"])
        if tag in VOID:
            return
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append("stray closing tag </%s>" % tag)
            return
        opened = self.stack.pop()
        if opened != tag:
            self.errors.append("tag <%(o)s> closed by </%(c)s>"
                               % {"o": opened, "c": tag})

    def handle_data(self, data):
        self.text.append(data)

    def close(self):
        super().close()
        if self.stack:
            self.errors.append("unclosed tags: %s" % ", ".join(self.stack))


def build():
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "assets").mkdir(parents=True)
    (SITE / "assets" / "style.css").write_text(STYLE, encoding="utf-8")

    rendered = {}
    for slug_, _title, _desc in PAGES:
        source_file = CONTENT / ("%s.md" % slug_)
        body_html = render_markdown(source_file.read_text(encoding="utf-8"))
        first_heading = re.search(r"<h1[^>]*>(.*?)</h1>", body_html, re.DOTALL)
        page_title = "%s — %s" % (first_heading.group(1), TITLE) if first_heading else TITLE
        rendered[slug_] = page_title.replace("</strong>", "").replace("<strong>", "")
        doc = SHELL.format(title=esc(page_title), desc=esc(_desc), body=body_html,
                           footer=esc(FOOTER), nav=nav_links(slug_))
        (SITE / ("%s.html" % slug_)).write_text(doc, encoding="utf-8")

    cards = []
    for slug_, title, desc in PAGES:
        headings = re.findall(r'<h[23] id="([^"]+)">(.*?)</h[23]>', rendered.get(slug_, "") or "")
        body_file = SITE / ("%s.html" % slug_)
        body_text = body_file.read_text(encoding="utf-8")
        headings = re.findall(r'<h([23]) id="([^"]+)">(.*?)</h\1>',
                              body_text, re.DOTALL)
        toc = "".join('<li><a href="%s.html#%s">%s</a></li>'
                      % (slug_, hid, html_mod.unescape(re.sub("<[^>]+>", "", text)))
                      for _, hid, text in headings) or "<li>One short guide</li>"
        cards.append('<div class="entry"><h2><a href="%s.html">%s</a></h2>'
                     "<p>%s</p><ul class=\"toc\">%s</ul></div>"
                     % (slug_, esc(title), esc(desc), toc))
    index_body = ("<h1>%s</h1>"
                  '<p class="lead">Every entry was added by hand and checked: '
                  "free to use, official links only, no affiliate links, no "
                  "tracking. Pick a page below — or start with the "
                  '<a href="share-card.html">share card</a> if someone in '
                  "your group chat needs it.</p>%s"
                  % (TITLE, "".join(cards)))
    index_doc = SHELL.format(title=TITLE, desc=DESCRIPTION, body=index_body,
                             footer=esc(FOOTER), nav=nav_links("index"))
    (SITE / "index.html").write_text(index_doc, encoding="utf-8")
    return sorted(str(p) for p in SITE.glob("*.html"))


def validate(all_pages, strict):
    failures = []
    for rel in all_pages:
        path = SITE / Path(rel).name
        checker = StructureChecker()
        checker.feed(path.read_text(encoding="utf-8"))
        checker.close()
        for error in checker.errors:
            failures.append("%s: %s" % (path.name, error))
        text = "".join(checker.text)
        if "Asdale Dynamics, LLC" not in text:
            failures.append("%s: missing LLC credit in footer" % path.name)
        for href in checker.hrefs:
            if href.startswith("http:") and not href.startswith("http://localhost"):
                failures.append("%s: non-https link %s" % (path.name, href))
            lowered = href.lower()
            if any(marker in lowered for marker in
                   ("utm_", "affiliate", "amzn.to", "?tag=", "&tag=",
                    "ref=", "gclid", "/ref/")):
                failures.append("%s: affiliate/tracking link %s"
                                % (path.name, href))
            if href.endswith(".html"):
                target = SITE / href
                if not target.exists():
                    failures.append("%s: broken internal link %s"
                                    % (path.name, href))
            if href.startswith("#"):
                anchor = href[1:]
                if anchor and anchor not in checker.ids:
                    failures.append("%s: missing anchor #%s"
                                    % (path.name, anchor))
    external_count = 0
    for rel in all_pages:
        path = SITE / Path(rel).name
        checker = StructureChecker()
        checker.feed(path.read_text(encoding="utf-8"))
        checker.close()
        for href in checker.hrefs:
            if href.startswith("https://"):
                external_count += 1
    if external_count < 15:
        failures.append("expected 15+ external links, found %d" % external_count)

    if strict:
        spot = {
            "sources.html": ["Snopes", "PolitiFact", "Reuters", "cdc.gov",
                             "census.gov", "irs.gov", "FactCheck.org"],
            "tools.html": ["TinEye", "Yandex", "Wayback Machine",
                           "archive.today", "images.google.com"],
            "checklists.html": ["Health rumor checklist", "Money rumor checklist",
                                "Weather rumor checklist", "☐"],
            "share-card.html": ["2-minute check", "images.google.com"],
        }
        spots_by_text = {}
        spots_by_href = {
            "index.html": ["share-card.html", "sources.html", "tools.html",
                           "checklists.html", "assets/style.css"],
        }
        for name in set(list(spot) + list(spots_by_href)):
            page_path = SITE / name
            checker = StructureChecker()
            checker.feed(page_path.read_text(encoding="utf-8"))
            checker.close()
            spots_by_text[name] = "".join(checker.text)
        for name, needles in spot.items():
            for needle in needles:
                if needle not in spots_by_text[name]:
                    failures.append("%s: missing content %r" % (name, needle))
        for name, needles in spots_by_href.items():
            page_path = SITE / name
            checker = StructureChecker()
            checker.feed(page_path.read_text(encoding="utf-8"))
            checker.close()
            for needle in needles:
                if needle not in checker.hrefs:
                    failures.append("%s: missing link %r" % (name, needle))

    if failures:
        print("FAIL (%d):" % len(failures))
        for failure in failures:
            print("  - %s" % failure)
        sys.exit(1)
    print("Render check: %s pages well-formed" % len(all_pages))
    print("Link check: %d external links (all https, no tracking)"
          % external_count)


def main():
    parser = argparse.ArgumentParser(
        description="Build the Free Fact-Check Directory static site.")
    parser.add_argument("--test", action="store_true",
                        help="run the build plus content/render spot checks")
    args = parser.parse_args()
    pages = build()
    validate(pages, strict=args.test)
    print("Built %d pages into site/" % (len(pages)))
    if args.test:
        print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
