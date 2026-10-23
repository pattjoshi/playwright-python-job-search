"""Find the company's own application page behind a board's "Apply on company site" link."""

import re
from urllib.parse import parse_qs, urljoin, urlparse

_QUOTED_URL = re.compile(r"""["'](https?://[^"']+)["']""")
_REDIRECT_PARAMS = ("url", "dest", "redirect", "target")


def external_apply_url(raw: str, base: str = "", board_hosts: tuple[str, ...] = ()) -> str:
    """The company page a board's apply link points to, or "" when there is none.

    `raw` is an href, or text holding a quoted URL (LinkedIn hides it in an HTML comment). Board redirect links
    that carry the target in a query parameter (`...externalApply/1?url=https%3A...`) are unwrapped; other
    board links (e.g. Indeed's `/rc/clk?...`) are kept, since the browser follows them to the company page.
    A link that only leads back to the board's own apply flow returns "".
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    quoted = _QUOTED_URL.search(raw)
    url = urljoin(base, quoted.group(1) if quoted else raw).replace("&amp;", "&")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return ""
    if _on(parsed.hostname or "", board_hosts):
        query = parse_qs(parsed.query)
        for name in _REDIRECT_PARAMS:
            target = (query.get(name) or [""])[0]
            if target.startswith(("http://", "https://")) and not _on(urlparse(target).hostname or "", board_hosts):
                return target
        if "externalApply" in parsed.path:
            return ""
    return url


def _on(host: str, hosts: tuple[str, ...]) -> bool:
    return any(host == h or host.endswith(f".{h}") for h in hosts)
