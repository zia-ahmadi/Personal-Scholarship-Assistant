"""Simple webpage extraction helpers.

This module downloads one webpage and extracts readable text. It intentionally
does not use browser automation or external scraping services.
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT = 15
MIN_TEXT_LENGTH = 100

REMOVED_TAGS = [
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "noscript",
    "iframe",
    "svg",
]


def scrape_webpage_text(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, str | bool | None]:
    """Download a URL and return clean readable text.

    The return value always has the same shape:
    {
        "ok": bool,
        "text": str | None,
        "error": str | None,
        "source_url": str,
    }
    """
    clean_url = url.strip()

    if not is_valid_url(clean_url):
        return {
            "ok": False,
            "text": None,
            "error": "Invalid URL. Please enter a full URL starting with http:// or https://.",
            "source_url": clean_url,
        }

    try:
        response = requests.get(
            clean_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.Timeout:
        return {
            "ok": False,
            "text": None,
            "error": "The website took too long to respond.",
            "source_url": clean_url,
        }
    except requests.HTTPError as error:
        status_code = error.response.status_code if error.response else "unknown"
        return {
            "ok": False,
            "text": None,
            "error": f"The website returned an HTTP error: {status_code}.",
            "source_url": clean_url,
        }
    except requests.RequestException as error:
        return {
            "ok": False,
            "text": None,
            "error": f"Could not download the webpage: {error}",
            "source_url": clean_url,
        }

    text = extract_readable_text(response.text)

    if len(text) < MIN_TEXT_LENGTH:
        return {
            "ok": False,
            "text": None,
            "error": (
                "Could not extract useful content from this webpage. "
                "The site may block automated requests or require JavaScript."
            ),
            "source_url": clean_url,
        }

    return {
        "ok": True,
        "text": text,
        "error": None,
        "source_url": clean_url,
    }


def is_valid_url(url: str) -> bool:
    """Check that the URL has a supported scheme and a domain."""
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def extract_readable_text(html: str) -> str:
    """Remove obvious non-content HTML and normalize whitespace."""
    soup = BeautifulSoup(html, "html.parser")

    for tag_name in REMOVED_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Common layout elements are often marked by role or class/id names.
    for tag in soup.select(
        "[role='navigation'], [role='banner'], [role='contentinfo'], "
        ".nav, .navbar, .menu, .sidebar, .footer, .header, "
        "#nav, #navbar, #menu, #sidebar, #footer, #header"
    ):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    useful_lines = [line for line in lines if line]

    return "\n".join(useful_lines)


if __name__ == "__main__":
    sample_url = "https://www.python.org/"
    result = scrape_webpage_text(sample_url)

    if not result["ok"]:
        print(f"Error: {result['error']}")
    else:
        print(f"Source: {result['source_url']}")
        print()
        print(result["text"][:2000])
