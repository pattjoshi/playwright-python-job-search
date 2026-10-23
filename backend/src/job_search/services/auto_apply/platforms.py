"""Which application system a company career page runs on, and the few things that differ between them."""

from urllib.parse import parse_qs, urlparse

PLATFORMS: dict[str, tuple[str, ...]] = {
    "greenhouse": ("greenhouse.io",),
    "lever": ("lever.co",),
    "ashby": ("ashbyhq.com",),
    "smartrecruiters": ("smartrecruiters.com",),
    "workday": ("myworkdayjobs.com", "myworkday.com"),
}
NAMES = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby", "smartrecruiters": "SmartRecruiters",
         "workday": "Workday", "other": "Company site"}
# Need an account on every company before you can apply: skipped for now.
NEEDS_ACCOUNT = {"workday"}
# Where the form usually is, tried before "the form with the most fields".
FORM_HINTS = {
    "greenhouse": "#application-form, #application_form, form[action*='greenhouse']",
    "lever": "form#application-form, .application-form form, form[action*='lever']",
    "ashby": "[class*='ashby-application-form'], form",
    "smartrecruiters": "oc-oneclick-form, form",
}


def detect(url: str) -> str:
    """"greenhouse", "lever", "ashby", "smartrecruiters", "workday" or "other"."""
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    for platform, hosts in PLATFORMS.items():
        if any(host == h or host.endswith(f".{h}") for h in hosts):
            return platform
    if "gh_jid" in parse_qs(parsed.query):  # a company page embedding a Greenhouse form
        return "greenhouse"
    return "other"


def form_url(url: str, platform: str) -> str:
    """Go straight to the application form where the system keeps it on its own page."""
    path = urlparse(url).path.rstrip("/")
    if platform == "lever" and not path.endswith("/apply"):
        return url.split("?")[0].rstrip("/") + "/apply"
    if platform == "ashby" and not path.endswith("/application"):
        return url.split("?")[0].rstrip("/") + "/application"
    return url
