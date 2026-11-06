"""Helpers for reading data from the Union Registry public website.

The website (https://union-registry-data.ec.europa.eu/report/welcome) is a
single-page app: its "Data Download" menu is not in the served HTML but is
built client-side from the JSON endpoint `DATA_DOWNLOAD_API`. Each entry in
that listing has a human-readable `name` (the menu label, e.g.
`"Transactions"`) and the current download `url`.

The provider occasionally moves files to new URLs while the old ones keep
serving stale snapshots, so download URLs must be resolved at runtime from
this listing rather than hard-coded. There is deliberately no fallback to a
known URL: a failed lookup raises instead of silently fetching outdated data.
"""

from loguru import logger

from eutl_scraper.settings import DownloadClient

BASE_URL = "https://union-registry-data.ec.europa.eu"
DATA_DOWNLOAD_API = f"{BASE_URL}/api/data-download"


def resolve_download_url(name: str, client: DownloadClient | None = None) -> str:
    """Resolve the current download URL of a "Data Download" menu entry.

    Args:
        name: Exact label of the entry as shown in the website's "Data
            Download" menu, e.g. `"Transactions"` or
            `"Operators Yearly Activity Daily"`. Matching is exact and
            case-sensitive.
        client: Shared HTTP client to reuse. If `None`, a client is created
            and closed for this call.

    Returns:
        The download URL currently listed for `name`.

    Raises:
        httpx.HTTPStatusError: If the listing endpoint returns an error status.
        ValueError: If the listing is not a list of objects, `name` matches no
            entry or more than one entry (the message lists the available
            names), or the matching entry has no `http(s)` URL.
    """
    own_client = client is None
    client = client or DownloadClient()
    try:
        entries = client.get_json(DATA_DOWNLOAD_API)
    finally:
        if own_client:
            client.close()

    if not isinstance(entries, list):
        raise ValueError(
            f"Unexpected response from {DATA_DOWNLOAD_API}: expected a list, "
            f"got {type(entries).__name__}"
        )

    if not all(isinstance(e, dict) for e in entries):
        raise ValueError(
            f"Unexpected response from {DATA_DOWNLOAD_API}: expected a list of "
            "objects, got non-object entries"
        )

    matches = [e for e in entries if e.get("name") == name]
    if len(matches) != 1:
        available = [e.get("name") for e in entries]
        problem = "No entry" if not matches else f"{len(matches)} entries"
        raise ValueError(
            f"{problem} named {name!r} in {DATA_DOWNLOAD_API}. "
            f"Available names: {available}"
        )

    url = matches[0].get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ValueError(
            f"Entry {name!r} in {DATA_DOWNLOAD_API} has no valid download URL: {url!r}"
        )

    logger.info(f"Resolved {name!r} to {url}")
    return url
