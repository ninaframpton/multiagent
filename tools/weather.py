"""Weather tool — fetch a forecast from the OpenWeatherMap free API.

Setup
-----
1. Sign up (free) at https://openweathermap.org/api
2. Copy your API key into .env:

       OPENWEATHER_API_KEY=your_key_here

3. Call get_forecast() from any handler.

Free-tier notes
---------------
- The "5 day / 3 hour" forecast endpoint covers the next 5 days in 3-hour
  intervals. Dates further away than that are not available on the free plan.
- Results are cached in-process for 10 minutes to avoid hammering the API
  during a demo.
"""

import logging
import os
import time
from datetime import date

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
_CACHE: dict[str, tuple[float, "WeatherForecast"]] = {}
_CACHE_TTL_SECONDS = 600  # 10 minutes


class WeatherForecast(BaseModel):
    """A simple weather summary for a location and date."""

    location: str
    date: str  # ISO format: YYYY-MM-DD
    description: str  # e.g. "light rain"
    temp_celsius: float
    humidity_percent: int
    outdoor_friendly: bool  # True when dry and < 30 °C


async def get_forecast(location: str, target_date: date) -> WeatherForecast:
    """Return a weather forecast for the given location and date.

    Only dates within the next 5 days are supported on the free plan.
    Falls back to a clear-sky default if the API key is missing or the
    date is out of range, so the rest of the pipeline always works.

    Args:
        location: City name, e.g. ``"London"`` or ``"London,GB"``.
        target_date: The festival date to forecast.

    Returns:
        A WeatherForecast summarising conditions on that day.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        logger.warning(
            "OPENWEATHER_API_KEY not set — returning default clear-sky forecast."
        )
        return _default_forecast(location, target_date)

    cache_key = f"{location}:{target_date.isoformat()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        result = await _fetch_forecast(api_key, location, target_date)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Weather API call failed (%s) — using default.", exc)
        result = _default_forecast(location, target_date)

    _cache_set(cache_key, result)
    return result


async def _fetch_forecast(
    api_key: str, location: str, target_date: date
) -> WeatherForecast:
    """Hit the OpenWeatherMap 5-day forecast endpoint."""
    params = {
        "q": location,
        "appid": api_key,
        "units": "metric",
        "cnt": 40,  # max entries (~5 days)
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    target_str = target_date.isoformat()
    # Find the midday entry closest to the target date
    entries = [
        e for e in data["list"] if e["dt_txt"].startswith(target_str)
    ]
    if not entries:
        logger.warning(
            "No forecast entry for %s — date may be out of 5-day range.",
            target_str,
        )
        return _default_forecast(location, target_date)

    # Prefer the 12:00 slot, otherwise take the first available
    midday = next(
        (e for e in entries if "12:00" in e["dt_txt"]), entries[0]
    )

    description = midday["weather"][0]["description"]
    temp = midday["main"]["temp"]
    humidity = midday["main"]["humidity"]
    outdoor_friendly = (
        "rain" not in description
        and "snow" not in description
        and "storm" not in description
        and temp < 30  # noqa: PLR2004
    )

    return WeatherForecast(
        location=data["city"]["name"],
        date=target_str,
        description=description,
        temp_celsius=round(temp, 1),
        humidity_percent=humidity,
        outdoor_friendly=outdoor_friendly,
    )


def _default_forecast(location: str, target_date: date) -> WeatherForecast:
    return WeatherForecast(
        location=location,
        date=target_date.isoformat(),
        description="clear sky",
        temp_celsius=22.0,
        humidity_percent=55,
        outdoor_friendly=True,
    )


def _cache_get(key: str) -> "WeatherForecast | None":
    entry = _CACHE.get(key)
    if entry and time.monotonic() - entry[0] < _CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _cache_set(key: str, value: "WeatherForecast") -> None:
    _CACHE[key] = (time.monotonic(), value)
