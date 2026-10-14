"""Static checks for the built site (site/dist). Exit code 1 if any check fails.

    python site/check_site.py

Checks: internal links and #anchors resolve, images exist and have alt text, every page has a
title, one <h1>, a lang attribute and a viewport meta, heading levels do not skip, external
links use https, and the built output contains no phone number, unlisted e-mail address or
secret-looking strings.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import json
import os

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
CONTENT = json.loads(Path(os.environ.get("PORTFOLIO_CONTENT", HERE.parent / "content/content.json")).read_text(encoding="utf-8"))


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.imgs, self.ids, self.headings = [], [], set(), []
        self.title, self._in_title, self.html_lang, self.viewport = "", False, None, False
        self._h = None

    def handle_starttag(self, tag, a):
        a = dict(a)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        elif tag == "a" and "href" in a:
            self.links.append(a["href"])
        elif tag in ("link", "script") and (a.get("href") or a.get("src")):
            self.links.append(a.get("href") or a.get("src"))
        elif tag == "img":
            self.imgs.append((a.get("src", ""), a.get("alt")))
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def main() -> int:
    problems = []
    pages = {p: Page() for p in DIST.rglob("*.html")}
    for p, parser in pages.items():
        parser.feed(p.read_text(encoding="utf-8"))
    for p, pg in pages.items():
        rel = p.relative_to(DIST)
        if not pg.title.strip():
            problems.append(f"{rel}: missing <title>")
        if pg.html_lang != "en":
            problems.append(f"{rel}: html lang is {pg.html_lang!r}")
        if not pg.viewport:
            problems.append(f"{rel}: missing viewport meta")
        if pg.headings.count(1) != 1:
            problems.append(f"{rel}: expected exactly one h1, found {pg.headings.count(1)}")
        for a, b in zip(pg.headings, pg.headings[1:]):
            if b > a + 1:
                problems.append(f"{rel}: heading level jumps h{a} -> h{b}")
        for src, alt in pg.imgs:
            if not alt or not alt.strip():
                problems.append(f"{rel}: image {src} has no alt text")
        for href in pg.links:
            u = urlparse(href)
            if u.scheme in ("http", "https"):
                if u.scheme != "https":
                    problems.append(f"{rel}: non-https link {href}")
                continue
            if u.scheme in ("mailto", "tel"):
                continue
            target = (p.parent / unquote(u.path)).resolve() if u.path else p
            if not target.exists():
                problems.append(f"{rel}: broken link {href}")
                continue
            if u.fragment and target.suffix == ".html":
                other = pages.get(target)
                if other is None or u.fragment not in other.ids:
                    problems.append(f"{rel}: missing anchor #{u.fragment} in {target.name}")
        for src, _ in pg.imgs:
            if not (p.parent / src).resolve().exists():
                problems.append(f"{rel}: missing image {src}")

    # privacy / secrets scan of everything shipped
    text = "".join(f.read_text(errors="ignore") for f in DIST.rglob("*") if f.suffix in {".html", ".css", ".js", ".svg"})
    if re.search(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b", text):
        problems.append("possible phone number in shipped files")
    email = CONTENT["person"].get("email")
    if email and not CONTENT["person"].get("show_email_on_site") and email in text:
        problems.append("email appears in built site although show_email_on_site is false")
    if re.search(r"ghp_|github_pat_|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|[0-9a-f]{100,}", text):
        problems.append("secret-looking string in shipped files")

    n_img = sum(len(pg.imgs) for pg in pages.values())
    print(f"checked {len(pages)} pages, {n_img} images")
    for pr in problems:
        print("FAIL:", pr)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
