"""Feature 9 — Web search tool (DuckDuckGo, no API key).

Real-time info fetch: search results ya ek URL ka text content.
"""
from __future__ import annotations
import re
import urllib.parse
import urllib.request
from .base import Tool

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class WebSearch(Tool):
    name = "web_search"
    description = (
        "Web se real-time info dhoondho (docs, errors, API usage). "
        "query = search terms. fetch = optional URL jise directly padhna hai."
    )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms."},
                "fetch": {"type": "string", "description": "Optional: ek URL ka content padho."},
            },
            "required": ["query"],
        }

    def run(self, workdir: str, query: str = "", fetch: str = "", **_) -> str:
        if fetch:
            return self._fetch(fetch)
        if not query:
            return "Error: query ya fetch chahiye"
        return self._search(query)

    def _search(self, query: str) -> str:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", errors="ignore")
        except Exception as e:
            return f"Error: search fail: {e}"
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html)
        if not links:
            return f"No results for: {query}"
        out = [f"🔍 {query}\n"]
        for i, (href, title) in enumerate(links[:6]):
            if "uddg=" in href:
                q = urllib.parse.urlparse(href).query
                real = urllib.parse.parse_qs(q).get("uddg", [href])[0]
                href = real
            snip = _strip(snips[i]) if i < len(snips) else ""
            out.append(f"{i+1}. {_strip(title)}\n   {href}\n   {snip}\n")
        return "\n".join(out)

    def _fetch(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read(500 * 1024).decode("utf-8", errors="ignore")
        except Exception as e:
            return f"Error: fetch fail: {e}"
        text = _extract(html)
        if len(text) > 6000:
            text = text[:6000] + "\n…[truncated]"
        return f"📄 {url}\n\n{text}"


def _strip(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def _extract(html: str) -> str:
    html = re.sub(r"(?s)<script.*?</script>", "", html)
    html = re.sub(r"(?s)<style.*?</style>", "", html)
    html = re.sub(r"<[^>]+>", " ", html)
    for a, b in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")]:
        html = html.replace(a, b)
    return re.sub(r"\s+", " ", html).strip()
