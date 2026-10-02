"""Locations offered in the UI, and turning free-text locations into those names."""

REMOTE = "Remote"

# Major Indian tech hubs, roughly by size of the tech job market.
INDIA_TECH_CITIES = [
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Mumbai",
    "Delhi",
    "Gurugram",
    "Noida",
    "Kolkata",
    "Ahmedabad",
    "Kochi",
    "Thiruvananthapuram",
    "Coimbatore",
    "Chandigarh",
    "Jaipur",
    "Indore",
    "Nagpur",
    "Mysuru",
    "Bhubaneswar",
    "Visakhapatnam",
    "Mangaluru",
    "Vadodara",
    "Lucknow",
    "Navi Mumbai",
    "Thane",
]

LOCATION_CHOICES = [REMOTE, *INDIA_TECH_CITIES]

_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "gurgaon": "Gurugram",
    "bombay": "Mumbai",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "madras": "Chennai",
    "calcutta": "Kolkata",
    "cochin": "Kochi",
    "trivandrum": "Thiruvananthapuram",
    "mysore": "Mysuru",
    "vizag": "Visakhapatnam",
    "mangalore": "Mangaluru",
    "baroda": "Vadodara",
    "work from home": REMOTE,
    "wfh": REMOTE,
    "remote": REMOTE,
}


def is_remote(location: str) -> bool:
    return location.strip().lower() in ("remote", "work from home", "wfh")


def normalize_location(text: str) -> str:
    """'Bangalore, Karnataka, India' -> 'Bengaluru'. Unknown places are returned trimmed."""
    lowered = text.lower()
    for alias, city in _ALIASES.items():
        if alias in lowered:
            return city
    for city in LOCATION_CHOICES:
        if city.lower() in lowered:
            return city
    return text.strip()
