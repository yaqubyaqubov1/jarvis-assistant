import atexit
import re

from pathlib import Path
from urllib.parse import quote_plus

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)

from config import DATA_DIR
from tools.registry import register
from tools.web_tools import (
    validate_public_url
)


class JarvisBrowser:

    def __init__(self):
        self.playwright = None
        self.context = None

    def _start(self):
        if self.context is not None:
            return

        profile = (
            DATA_DIR
            / "browser_profile"
        )

        profile.mkdir(
            parents=True,
            exist_ok=True
        )

        self.playwright = (
            sync_playwright().start()
        )

        self.context = (
            self.playwright
            .chromium
            .launch_persistent_context(
                user_data_dir=str(
                    profile
                ),
                headless=False,
                accept_downloads=True
            )
        )

    def page(self):
        self._start()

        pages = self.context.pages

        if not pages:
            return self.context.new_page()

        return pages[-1]

    def new_page(self):
        self._start()

        return self.context.new_page()

    def close(self):
        if self.context is not None:
            try:
                self.context.close()
            except Exception:
                pass

            self.context = None

        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass

            self.playwright = None


BROWSER = JarvisBrowser()

atexit.register(
    BROWSER.close
)


def _find_clickable(
    page,
    text
):
    candidates = [
        page.get_by_role(
            "button",
            name=text,
            exact=False
        ),

        page.get_by_role(
            "link",
            name=text,
            exact=False
        ),

        page.get_by_text(
            text,
            exact=False
        )
    ]

    for locator in candidates:
        try:
            if locator.count() > 0:
                return locator.first
        except Exception:
            continue

    return None


def _safe_filename(name):
    name = Path(
        str(name)
    ).name

    name = re.sub(
        r"[^A-Za-z0-9._() -]",
        "_",
        name
    )

    return (
        name[:180]
        or "download.bin"
    )


def _unique_path(path):
    if not path.exists():
        return path

    for number in range(
        1,
        10000
    ):
        candidate = path.with_name(
            f"{path.stem}_{number}"
            f"{path.suffix}"
        )

        if not candidate.exists():
            return candidate

    raise RuntimeError(
        "Could not choose filename."
    )


@register(
    "browser_open",
    "Open a webpage in JARVIS's controlled "
    "browser. arguments={url}"
)
def browser_open(url):
    url = validate_public_url(url)

    page = BROWSER.page()

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000
    )

    return (
        f"Opened {page.title()} "
        f"at {page.url}"
    )


@register(
    "browser_search",
    "Search DuckDuckGo in the controlled "
    "browser. arguments={query}"
)
def browser_search(query):
    page = BROWSER.page()

    url = (
        "https://duckduckgo.com/"
        "?q="
        + quote_plus(
            str(query)
        )
    )

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000
    )

    return (
        f"Searched DuckDuckGo "
        f"for {query}."
    )


@register(
    "browser_read",
    "Read the visible text of the current "
    "browser page. arguments={max_chars?}"
)
def browser_read(
    max_chars=15000
):
    page = BROWSER.page()

    text = page.locator(
        "body"
    ).inner_text(
        timeout=10000
    )

    return text[
        :min(
            int(max_chars),
            30000
        )
    ]


@register(
    "browser_current_page",
    "Return current browser title and URL. "
    "arguments={}"
)
def browser_current_page():
    page = BROWSER.page()

    return (
        f"Title: {page.title()}\n"
        f"URL: {page.url}"
    )


@register(
    "browser_click_text",
    "Click a visible button, link or text "
    "on the current webpage. arguments={text}"
)
def browser_click_text(text):
    page = BROWSER.page()

    locator = _find_clickable(
        page,
        str(text)
    )

    if locator is None:
        raise ValueError(
            f"Could not find '{text}' "
            "on the page."
        )

    locator.click(
        timeout=7000
    )

    page.wait_for_timeout(
        300
    )

    return (
        f"Clicked '{text}'. "
        f"Current page: {page.url}"
    )


@register(
    "browser_fill",
    "Fill a webpage field. "
    "arguments={field,value}"
)
def browser_fill(
    field,
    value
):
    page = BROWSER.page()

    field = str(field)

    candidates = [
        page.get_by_label(
            field,
            exact=False
        ),

        page.get_by_placeholder(
            field,
            exact=False
        ),

        page.get_by_role(
            "textbox",
            name=field,
            exact=False
        )
    ]

    locator = None

    for candidate in candidates:
        try:
            if candidate.count() > 0:
                locator = candidate.first
                break
        except Exception:
            continue

    if locator is None:
        raise ValueError(
            f"Could not find field "
            f"'{field}'."
        )

    locator.fill(
        str(value),
        timeout=7000
    )

    return (
        f"Filled '{field}'."
    )


@register(
    "browser_press",
    "Press a keyboard key in the browser. "
    "For example Enter, Escape or Tab. "
    "arguments={key}"
)
def browser_press(key):
    page = BROWSER.page()

    page.keyboard.press(
        str(key)
    )

    return (
        f"Pressed {key}."
    )


@register(
    "browser_back",
    "Navigate browser backward. arguments={}"
)
def browser_back():
    page = BROWSER.page()

    page.go_back(
        wait_until="domcontentloaded"
    )

    return (
        f"Navigated back to {page.url}."
    )


@register(
    "browser_forward",
    "Navigate browser forward. arguments={}"
)
def browser_forward():
    page = BROWSER.page()

    page.go_forward(
        wait_until="domcontentloaded"
    )

    return (
        f"Navigated forward to {page.url}."
    )


@register(
    "browser_new_tab",
    "Open a new browser tab. arguments={url?}"
)
def browser_new_tab(
    url=None
):
    page = BROWSER.new_page()

    if url:
        url = validate_public_url(url)

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

    return (
        f"Opened new browser tab: "
        f"{page.url}"
    )


@register(
    "browser_close_tab",
    "Close the current browser tab. arguments={}"
)
def browser_close_tab():
    page = BROWSER.page()

    page.close()

    return (
        "Closed browser tab."
    )


@register(
    "browser_download_click",
    "Click a visible link/button expected to "
    "download a file. Confirmation required. "
    "arguments={text,filename?}"
)
def browser_download_click(
    text,
    filename=None
):
    page = BROWSER.page()

    locator = _find_clickable(
        page,
        str(text)
    )

    if locator is None:
        raise ValueError(
            f"Could not find "
            f"'{text}'."
        )

    with page.expect_download(
        timeout=20000
    ) as download_info:

        locator.click()

    download = (
        download_info.value
    )

    suggested = (
        filename
        or download.suggested_filename
        or "download.bin"
    )

    filename = _safe_filename(
        suggested
    )

    folder = (
        Path.home()
        / "Downloads"
        / "JARVIS"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    destination = _unique_path(
        folder / filename
    )

    download.save_as(
        str(destination)
    )

    return (
        f"Downloaded to {destination}"
    )