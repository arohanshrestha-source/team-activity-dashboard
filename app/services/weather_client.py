"""
Weather data via Open-Meteo API (free, no API key required).
"""
import os
import re
import requests
from typing import Any, Dict, Optional

OPENMETEO_GEO = "https://geocoding-api.open-meteo.com/v1/search"
OPENMETEO_FORECAST = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes -> short description
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _geocode(city: str) -> Optional[Dict[str, Any]]:
    """Resolve city name to lat/lon using Open-Meteo geocoding."""
    try:
        resp = requests.get(
            OPENMETEO_GEO,
            params={"name": city, "count": 1},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return None
        r = results[0]
        return {"lat": r["latitude"], "lon": r["longitude"], "name": r.get("name", city)}
    except Exception:
        return None


def _extract_location_from_question(question: str) -> Optional[str]:
    """Try to extract a city/location from phrases like 'weather in Austin' or 'weather for Paris'."""
    q = question.lower()
    for pat in [
        r"weather\s+in\s+([a-zA-Z\s]+?)(?:\?|$|\.)",
        r"weather\s+for\s+([a-zA-Z\s]+?)(?:\?|$|\.)",
        r"forecast\s+for\s+([a-zA-Z\s]+?)(?:\?|$|\.)",
        r"temperature\s+in\s+([a-zA-Z\s]+?)(?:\?|$|\.)",
    ]:
        m = re.search(pat, q)
        if m:
            return m.group(1).strip()
    return None


def get_weather(location: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch current weather. Uses Open-Meteo (free, no key).
    Returns dict with temperature, conditions, humidity, wind, etc.
    """
    default_city = os.getenv("WEATHER_DEFAULT_CITY", "Austin")

    # Resolve location
    if location:
        geo = _geocode(location)
        if geo:
            lat, lon, name = geo["lat"], geo["lon"], geo["name"]
        else:
            try:
                lat = float(os.getenv("WEATHER_LAT", "30.2672"))
                lon = float(os.getenv("WEATHER_LON", "-97.7431"))
            except (TypeError, ValueError):
                lat, lon = 30.2672, -97.7431
            name = location
    else:
        try:
            lat = float(os.getenv("WEATHER_LAT", "30.2672"))
            lon = float(os.getenv("WEATHER_LON", "-97.7431"))
        except (TypeError, ValueError):
            lat, lon = 30.2672, -97.7431
        geo = _geocode(default_city)
        name = geo["name"] if geo else default_city

    url = OPENMETEO_FORECAST
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,precipitation",
        "timezone": "auto",
    }

    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Weather API failed ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    current = data.get("current") or {}
    code = int(current.get("weather_code", 0))
    desc = WMO_CODES.get(code, "Unknown")

    return {
        "location": name,
        "temperature_c": current.get("temperature_2m"),
        "temperature_f": round(current.get("temperature_2m", 0) * 9 / 5 + 32, 1) if current.get("temperature_2m") is not None else None,
        "humidity": current.get("relative_humidity_2m"),
        "weather_code": code,
        "conditions": desc,
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "precipitation": current.get("precipitation"),
    }


def get_weather_for_question(question: str) -> Dict[str, Any]:
    """Get weather, optionally extracting location from the question."""
    location = _extract_location_from_question(question)
    return get_weather(location=location)
