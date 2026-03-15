from __future__ import annotations

from urllib.parse import quote_plus


# City slug mapping for common Indian cities
_CITY_SLUGS: dict[str, str] = {
    "mumbai": "mumbai",
    "delhi": "delhi",
    "bangalore": "bangalore",
    "bengaluru": "bangalore",
    "hyderabad": "hyderabad",
    "chennai": "chennai",
    "kolkata": "kolkata",
    "pune": "pune",
    "ahmedabad": "ahmedabad",
    "jaipur": "jaipur",
    "surat": "surat",
    "lucknow": "lucknow",
    "kanpur": "kanpur",
    "nagpur": "nagpur",
    "indore": "indore",
    "thane": "thane",
    "bhopal": "bhopal",
    "visakhapatnam": "visakhapatnam",
    "vadodara": "vadodara",
    "noida": "noida",
    "gurgaon": "gurgaon",
    "gurugram": "gurgaon",
    "chandigarh": "chandigarh",
    "coimbatore": "coimbatore",
    "kochi": "kochi",
}


def build_deep_link(query: str, city: str) -> str:
    """Return a Zomato search deep link for the given query and city.

    Opens the Zomato app directly on supported devices; falls back to web.
    """
    city_lower = city.lower().strip()
    city_slug = _CITY_SLUGS.get(city_lower, city_lower.replace(" ", "-"))
    encoded_query = quote_plus(query)
    return f"https://www.zomato.com/{city_slug}/search?q={encoded_query}"


def build_restaurant_deep_link(restaurant_name: str, city: str) -> str:
    """Return a Zomato search link for a specific restaurant."""
    return build_deep_link(restaurant_name, city)
