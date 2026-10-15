#!/usr/bin/env python3
"""Create Zotero-friendly RSS feeds enriched with available article abstracts."""
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote, unquote

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ZoteroAbstractRSS/1.0 (academic personal RSS aggregation; contact: https://github.com/)", "Accept": "application/json, application/xml, text/xml, */*"})
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s<>\"'?#]+", re.I)


def clean_markup(value):
    if not value:
        return ""
    text = BeautifulSoup(html.unescape(str(value)), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def find_doi(entry):
    candidates = [entry.get("doi", ""), entry.get("id", ""), entry.get("link", "")]
    candidates += [item.get("href", "") for item in entry.get("links", [])]
    for value in candidates:
        found = DOI_RE.search(unquote(str(value)))
        if found:
            return found.group(0).rstrip(".,;)]}").lower()
    return None


def invert_openalex(index):
    if not index:
        return ""
    positions = [(p, word) for word, indices in index.items() for p in indices]
    positions.sort()
    return clean_markup(" ".join(word for _, word in positions))


def fetch_abstract(doi):
    # Prefer publisher-deposited abstract, then OpenAlex abstract when accessible.
    try:
        r = SESSION.get("https://api.crossref.org/works/" + quote(doi, safe=""), timeout=17)
        if r.ok:
            abstract = clean_markup(r.json().get("message", {}).get("abstract"))
            if abstract:
                return abstract
    except (requests.RequestException, ValueError):
        pass
    try:
        params = {}
        if os.getenv("OPENALEX_API_KEY"):
            params["api_key"] = os.environ["OPENALEX_API_KEY"]
        r = SESSION.get("https://api.openalex.org/works/https://doi.org/" + quote(doi, safe="/"), params=params, timeout=17)
        if r.ok:
            return invert_openalex(r.json().get("abstract_inverted_index"))
    except (requests.RequestException, ValueError):
        pass
    return ""


def get_entries(url):
    response = SESSION.get(url, timeout=35, headers={"Accept": "application/rss+xml, application/atom+xml, application/rdf+xml, application/xml, text/xml, */*"})
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if not parsed.entries:
        raise RuntimeError("订阅源没有返回条目。请检查 URL 是否是 RSS/Atom，以及能否从 GitHub 访问。")
    return parsed.entries


def generate(feed):
    name, url, filename = feed["name"], feed["url"], feed["file"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+\.xml", filename):
        raise ValueError("file 必须是例如 science.xml 的安全文件名")
    entries = get_entries(url)
    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    for k, v in (("title", name + " | Abstract Enhanced"), ("link", url),
                 ("description", "RSS with available scholarly abstracts, enriched via Crossref/OpenAlex"),
                 ("language", "en"), ("lastBuildDate", format_datetime(datetime.now(timezone.utc)))):
        ET.SubElement(channel, k).text = v

    enriched = 0
    for entry in entries[:int(feed.get("max_items", 40))]:
        item = ET.SubElement(channel, "item")
        title = clean_markup(entry.get("title", "Untitled"))
        link = entry.get("link", "")
        doi = find_doi(entry)
        summary = clean_markup(entry.get("summary", ""))
        abstract = fetch_abstract(doi) if doi else ""
        if abstract:
            enriched += 1
        # Never label a short RSS teaser as a complete abstract.
        description = abstract or summary or "This record has no abstract available from the checked data sources."
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = entry.get("id") or doi or link or title
        ET.SubElement(item, "description").text = description
        if doi:
            ET.SubElement(item, "doi").text = doi
        for author in entry.get("authors", [])[:10]:
            if author.get("name"):
                ET.SubElement(item, "author").text = author["name"]
        date_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if date_struct:
            from calendar import timegm
            from email.utils import formatdate
            ET.SubElement(item, "pubDate").text = formatdate(timegm(date_struct), usegmt=True)
        time.sleep(0.15)

    OUT.mkdir(exist_ok=True)
    ET.ElementTree(root).write(OUT / filename, encoding="utf-8", xml_declaration=True)
    print(f"{name}: {len(entries)} source items; processed {min(len(entries), int(feed.get('max_items', 40)))}; complete abstract candidates {enriched}; saved {filename}")


def main():
    feeds = json.loads((ROOT / "feeds.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    failures = 0
    for feed in feeds:
        try:
            generate(feed)
        except Exception as exc:
            print(f"ERROR {feed.get('name', '')}: {exc}", file=sys.stderr)
            failures += 1
    (OUT / "index.html").write_text("<html><meta charset='utf-8'><title>Enhanced Zotero RSS</title><h1>Enhanced RSS feeds</h1>" + "".join(f"<p><a href='{feed['file']}'>{html.escape(feed['name'])}</a></p>" for feed in feeds if (OUT / feed['file']).exists()) + "</html>", encoding="utf-8")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
