"""The browser auto-apply uses, with a saved profile so job-board logins are remembered between runs."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright


@contextmanager
def open_browser(headless: bool, executable_path: str | None = None, profile_dir: Path | None = None) -> Iterator[BrowserContext]:
    """A browser context; with profile_dir, cookies (your board logins) are kept there on this computer."""
    with sync_playwright() as playwright:
        options = {"headless": headless, "executable_path": executable_path, "locale": "en-US",
                   "viewport": {"width": 1280, "height": 900}}
        if profile_dir:
            Path(profile_dir).mkdir(parents=True, exist_ok=True)
            context = playwright.chromium.launch_persistent_context(str(profile_dir), **options)
            try:
                yield context
            finally:
                context.close()
            return
        browser = playwright.chromium.launch(headless=headless, executable_path=executable_path)
        try:
            yield browser.new_context(locale="en-US", viewport=options["viewport"])
        finally:
            browser.close()


def write_docx(path: Path, text: str) -> Path:
    import docx

    document = docx.Document()
    for paragraph in text.split("\n\n"):
        document.add_paragraph(paragraph.strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(path))
    return path
