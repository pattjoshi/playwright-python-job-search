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

ALIASES = {
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
