"""Dependency-free parsing helpers for the Torrentio scraper.

This module deliberately imports only the Python standard library so the
regex-based parsing of Torrentio stream titles can be unit-tested without
loading the full application (which requires third-party packages such as
requests). scraper/services/torrentio.py consumes parse_stream().
"""

import re

_SIZE_GB = re.compile(r"(?<=💾 )([0-9]+.?[0-9]+)(?= GB)")
_SIZE_MB = re.compile(r"(?<=💾 )([0-9]+.?[0-9]+)(?= MB)")
_SEEDS = re.compile(r"(?<=👤 )([0-9]+)")
_SEEDS_GUARD = re.compile(r"(?<=👤 )([1-9]+)")
_SOURCE = re.compile(r"(?<=⚙️ )(.*)(?=\n|$)")


def _extract_size(title):
    match = _SIZE_GB.search(title)
    if match:
        return float(match.group())
    match = _SIZE_MB.search(title)
    if match:
        return float(match.group()) / 1000
    return 0


def _extract_seeds(title):
    # Guard matches 1-9 so a literal "0" seeder count is read as 0,
    # while still extracting the full number (e.g. "10") when present.
    if _SEEDS_GUARD.search(title):
        return int(_SEEDS.search(title).group())
    return 0


def _extract_source(title):
    match = _SOURCE.search(title)
    return match.group() if match else "unknown"


def _extract_title(title):
    return title.split("\n")[0].replace(" ", ".")


def parse_stream(stream):
    """Parse a single Torrentio stream entry into a release description.

    Accepts either a dict or an object with attributes (the application
    passes a SimpleNamespace from json.loads). Returns a dict with the
    keys source, title, size, seeds and link, or None when the entry
    cannot be parsed (for example when the infoHash is missing).
    """
    if isinstance(stream, dict):
        info_hash = stream.get("infoHash")
        title = stream.get("title", "")
    else:
        info_hash = getattr(stream, "infoHash", None)
        title = getattr(stream, "title", "")
    if not info_hash or not title:
        return None
    try:
        return {
            "source": _extract_source(title),
            "title": _extract_title(title),
            "size": _extract_size(title),
            "seeds": _extract_seeds(title),
            "link": "magnet:?xt=urn:btih:" + info_hash + "&dn=&tr=",
        }
    except Exception:
        return None
