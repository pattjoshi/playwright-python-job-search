"""Turning free-text locations into the UI's canonical city names."""

from job_search.config.locations import ALIASES, LOCATION_CHOICES


def is_remote(location: str) -> bool:
    return location.strip().lower() in ("remote", "work from home", "wfh")


def normalize_location(text: str) -> str:
    """'Bangalore, Karnataka, India' -> 'Bengaluru'. Unknown places are returned trimmed."""
    lowered = text.lower()
    for alias, city in ALIASES.items():
        if alias in lowered:
            return city
    for city in LOCATION_CHOICES:
        if city.lower() in lowered:
            return city
    return text.strip()
