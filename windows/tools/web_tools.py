import ipaddress
import re
import socket
import webbrowser

from pathlib import Path
from urllib.parse import (
    unquote,
    urljoin,
    urlparse,
)

import requests

from bs4 import BeautifulSoup
from ddgs import DDGS

from tools.registry import (
    register,
)


USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "Chrome/140 Safari/537.36 "
    "JARVIS/1.0"
)


MAX_PAGE_BYTES = (
    2
    * 1024
    * 1024
)


MAX_DOWNLOAD_BYTES = (
    100
    * 1024
    * 1024
)


# =========================================================
# URL SAFETY
# =========================================================

def normalize_url(
    url,
):

    url = str(
        url
    ).strip()

    if not url:

        raise ValueError(
            "URL is empty."
        )

    parsed = urlparse(
        url
    )

    if not parsed.scheme:

        url = (
            "https://"
            + url
        )

        parsed = urlparse(
            url
        )

    if parsed.scheme not in {
        "http",
        "https",
    }:

        raise ValueError(
            "Only HTTP and HTTPS "
            "URLs are allowed."
        )

    if not parsed.hostname:

        raise ValueError(
            "Invalid URL."
        )

    return url


def validate_public_url(
    url,
):

    url = normalize_url(
        url
    )

    parsed = urlparse(
        url
    )

    hostname = (
        parsed.hostname
    )

    if not hostname:

        raise ValueError(
            "URL has no hostname."
        )

    if hostname.lower() in {
        "localhost",
        "localhost.localdomain",
    }:

        raise ValueError(
            "Internet tools cannot access localhost."
        )

    try:

        addresses = socket.getaddrinfo(
            hostname,
            None,
        )

    except socket.gaierror as exc:

        raise ValueError(
            f"Could not resolve {hostname}."
        ) from exc

    for entry in addresses:

        ip_text = (
            entry[4][0]
        )

        try:

            ip = ipaddress.ip_address(
                ip_text
            )

        except ValueError:
            continue

        if not ip.is_global:

            raise ValueError(
                "Access to private/internal "
                "network addresses is blocked."
            )

    return url


# =========================================================
# HTTP
# =========================================================

def _request(
    url,
    stream=False,
):

    current = (
        validate_public_url(
            url
        )
    )

    for _ in range(
        6
    ):

        response = requests.get(
            current,

            headers={
                "User-Agent":
                    USER_AGENT
            },

            timeout=15,

            allow_redirects=False,

            stream=stream,
        )

        if response.status_code in {
            301,
            302,
            303,
            307,
            308,
        }:

            location = (
                response.headers.get(
                    "Location"
                )
            )

            if not location:

                return response

            current = (
                validate_public_url(
                    urljoin(
                        current,
                        location,
                    )
                )
            )

            continue

        return response

    raise RuntimeError(
        "Too many HTTP redirects."
    )


# =========================================================
# SEARCH
# =========================================================

def _duckduckgo_text(
    query,
    max_results=5,
    timelimit=None,
):

    count = max(
        1,

        min(
            int(max_results),
            10,
        ),
    )

    rows = (
        DDGS(
            timeout=10
        )
        .text(
            str(query),

            region="wt-wt",

            safesearch="moderate",

            timelimit=timelimit,

            max_results=count,

            backend="duckduckgo",
        )
    )

    return list(
        rows or []
    )


@register(
    "web_search",
    "Search DuckDuckGo and return web results. "
    "arguments={query,max_results?,timelimit?}",
)
def web_search(
    query,
    max_results=5,
    timelimit=None,
):

    rows = (
        _duckduckgo_text(
            query,
            max_results=max_results,
            timelimit=timelimit,
        )
    )

    if not rows:

        return (
            "No search results found."
        )

    output = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        output.append(
            (
                f"{index}. "
                f"{row.get('title', '')}\n"
                f"{row.get('href', '')}\n"
                f"{row.get('body', '')}"
            )
        )

    return "\n\n".join(
        output
    )


# =========================================================
# NEWS SEARCH
# =========================================================

@register(
    "web_news_search",
    "Search recent DuckDuckGo news results. "
    "arguments={query,max_results?,timelimit?}",
)
def web_news_search(
    query,
    max_results=5,
    timelimit="w",
):

    count = max(
        1,

        min(
            int(max_results),
            10,
        ),
    )

    rows = (
        DDGS(
            timeout=10
        )
        .news(
            str(query),

            region="wt-wt",

            safesearch="moderate",

            timelimit=timelimit,

            max_results=count,

            backend="duckduckgo",
        )
    )

    rows = list(
        rows or []
    )

    if not rows:

        return (
            "No news results found."
        )

    output = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        url = (
            row.get("url")
            or
            row.get("href")
            or
            ""
        )

        output.append(
            (
                f"{index}. "
                f"{row.get('title', '')}\n"
                f"{url}\n"
                f"{row.get('body', '')}\n"
                f"{row.get('date', '')}"
            )
        )

    return "\n\n".join(
        output
    )


# =========================================================
# OPEN EXPLICIT URL
# =========================================================

@register(
    "open_url",
    "Open a public HTTP or HTTPS URL in the "
    "default browser. arguments={url}",
)
def open_url(
    url,
):

    url = (
        validate_public_url(
            url
        )
    )

    webbrowser.open(
        url
    )

    return (
        f"Opened {url}."
    )


# =========================================================
# OPEN WEBSITE BY NAME
# =========================================================

@register(
    "open_website",
    "Search DuckDuckGo for a website by name and "
    "open the first valid public result. "
    "Use this when the user explicitly asks for "
    "a site's website/page rather than an app. "
    "arguments={query}",
)
def open_website(
    query,
):

    query = str(
        query
    ).strip()

    if not query:

        raise ValueError(
            "Website query is empty."
        )

    search_query = (
        f"{query} official website"
    )

    rows = (
        _duckduckgo_text(
            search_query,
            max_results=8,
        )
    )

    if not rows:

        return (
            f"I couldn't find a website "
            f"for '{query}'."
        )

    for row in rows:

        url = (
            row.get(
                "href"
            )
            or
            row.get(
                "url"
            )
            or
            ""
        )

        if not url:

            continue

        try:

            url = (
                validate_public_url(
                    url
                )
            )

        except Exception:
            continue

        webbrowser.open(
            url
        )

        title = (
            row.get(
                "title"
            )
            or query
        )

        return (
            f"Opened {title}."
        )

    return (
        f"I found search results for "
        f"'{query}', but none had a "
        f"valid public website address."
    )


# =========================================================
# READ WEBSITE
# =========================================================

@register(
    "read_webpage",
    "Download and extract readable text from a "
    "public webpage. arguments={url}",
)
def read_webpage(
    url,
):

    response = _request(
        url,
        stream=True,
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get(
            "Content-Type",
            "",
        )
        .lower()
    )

    allowed = (
        "text/html",
        "application/xhtml+xml",
        "text/plain",
        "application/json",
    )

    if not any(
        kind in content_type
        for kind in allowed
    ):

        raise ValueError(
            "That URL is not a readable "
            "text webpage."
        )

    data = bytearray()

    for chunk in response.iter_content(
        chunk_size=65536
    ):

        if not chunk:
            continue

        data.extend(
            chunk
        )

        if (
            len(data)
            > MAX_PAGE_BYTES
        ):

            raise ValueError(
                "Webpage is too large."
            )

    encoding = (
        response.encoding
        or
        "utf-8"
    )

    text = data.decode(
        encoding,
        errors="replace",
    )

    if (
        "text/html"
        in content_type
        or
        "xhtml"
        in content_type
    ):

        soup = BeautifulSoup(
            text,
            "html.parser",
        )

        for tag in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
            ]
        ):

            tag.decompose()

        text = soup.get_text(
            "\n",
            strip=True,
        )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text[:30000]


# =========================================================
# DOWNLOAD
# =========================================================

def _safe_filename(
    name,
):

    name = Path(
        str(name)
    ).name

    name = re.sub(
        r"[^A-Za-z0-9._() -]",
        "_",
        name,
    )

    return (
        name[:180]
        or
        "download.bin"
    )


def _unique_path(
    path,
):

    if not path.exists():
        return path

    for number in range(
        1,
        10000,
    ):

        candidate = (
            path.with_name(
                f"{path.stem}_"
                f"{number}"
                f"{path.suffix}"
            )
        )

        if not candidate.exists():
            return candidate

    raise RuntimeError(
        "Could not generate "
        "a download filename."
    )


@register(
    "download_file",
    "Download a public internet file into "
    "Downloads/JARVIS. Confirmation required. "
    "arguments={url,filename?}",
)
def download_file(
    url,
    filename=None,
):

    response = _request(
        url,
        stream=True,
    )

    response.raise_for_status()

    content_length = (
        response.headers.get(
            "Content-Length"
        )
    )

    if content_length:

        try:

            length = int(
                content_length
            )

        except (
            TypeError,
            ValueError,
        ):

            length = None

        if (
            length is not None
            and
            length
            > MAX_DOWNLOAD_BYTES
        ):

            raise ValueError(
                "Download exceeds the "
                "100 MB safety limit."
            )

    if not filename:

        parsed = urlparse(
            response.url
        )

        filename = unquote(
            Path(
                parsed.path
            ).name
        )

    filename = (
        _safe_filename(
            filename
            or
            "download.bin"
        )
    )

    folder = (
        Path.home()
        / "Downloads"
        / "JARVIS"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        _unique_path(
            folder
            / filename
        )
    )

    downloaded = 0

    try:

        with destination.open(
            "wb"
        ) as file:

            for chunk in response.iter_content(
                chunk_size=65536
            ):

                if not chunk:
                    continue

                downloaded += len(
                    chunk
                )

                if (
                    downloaded
                    > MAX_DOWNLOAD_BYTES
                ):

                    raise ValueError(
                        "Download exceeded "
                        "the 100 MB safety limit."
                    )

                file.write(
                    chunk
                )

    except Exception:

        try:

            if destination.exists():

                destination.unlink()

        except OSError:
            pass

        raise

    return (
        f"Downloaded to {destination}"
    )