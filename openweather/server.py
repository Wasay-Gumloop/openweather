"""OpenWeather MCP Server - Provides weather data tools via OpenWeather API."""

import logging
import os

import httpx
from dotenv import load_dotenv
from mcp.gumstack import GumstackHost
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from openweather.models import (
    Coordinates,
    CurrentWeatherResult,
    ForecastItem,
    GeocodingLocation,
    GeocodingResult,
    ReverseGeocodingResult,
    Temperature,
    WeatherCondition,
    WeatherForecastResult,
    Wind,
)
from openweather.utils.auth import get_credentials


class DiagnosticResult(BaseModel):
    """Result of API diagnostic check."""

    api_key_length: int = Field(description="Length of the API key")
    api_key_preview: str = Field(description="First 8 characters of API key")
    api_key_hex_preview: str = Field(description="Hex representation of first 16 chars")
    test_url: str = Field(description="URL used for testing")
    response_status: int = Field(description="HTTP status code from OpenWeather")
    response_body: str = Field(description="Response body from OpenWeather")
    success: bool = Field(description="Whether the API call succeeded")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get port from environment variable (default 8000 for local, 8080 for Knative)
PORT = int(os.environ.get("PORT", 8000))

# OpenWeather API base URLs
WEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
GEO_API_BASE = "https://api.openweathermap.org/geo/1.0"

mcp = FastMCP("OpenWeather", host="0.0.0.0", port=PORT)


# Health check endpoint for Knative readiness/liveness probes
@mcp.custom_route("/health_check", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for container orchestration."""
    return JSONResponse({"status": "ok"})


def _parse_weather_condition(weather_list: list) -> WeatherCondition:
    """Parse weather condition from API response."""
    weather = weather_list[0] if weather_list else {}
    return WeatherCondition(
        main=weather.get("main", "Unknown"),
        description=weather.get("description", ""),
        icon=weather.get("icon", ""),
    )


def _parse_temperature(main: dict) -> Temperature:
    """Parse temperature data from API response."""
    return Temperature(
        current=main.get("temp", 0),
        feels_like=main.get("feels_like", 0),
        min=main.get("temp_min", 0),
        max=main.get("temp_max", 0),
    )


def _parse_wind(wind: dict) -> Wind:
    """Parse wind data from API response."""
    return Wind(
        speed=wind.get("speed", 0),
        direction=wind.get("deg", 0),
        gust=wind.get("gust"),
    )


@mcp.tool()
async def get_current_weather(
    location: str = Field(
        description="City name, optionally with country code (e.g., 'London' or 'London,UK')"
    ),
    units: str = Field(
        default="metric",
        description="Temperature units: 'metric' (Celsius), 'imperial' (Fahrenheit), or 'standard' (Kelvin)",
    ),
) -> CurrentWeatherResult:
    """
    Get current weather conditions for a specific location.

    Returns real-time weather data including temperature, humidity, wind,
    atmospheric pressure, visibility, and weather conditions.
    """
    creds = await get_credentials()
    logger.info("Credentials received: %s", {k: f"{v[:8]}..." if v else "empty" for k, v in creds.items()})

    # Try multiple possible key names
    api_key = creds.get("api_key") or creds.get("API_KEY") or creds.get("apiKey") or ""
    api_key = api_key.strip()  # Remove any whitespace

    if not api_key:
        raise ValueError(
            f"OpenWeather API key not configured. Received credential keys: {list(creds.keys())}"
        )

    logger.info("Using API key: %s...", api_key[:8] if len(api_key) >= 8 else api_key)

    # Ensure units is a string (handle potential Field object issue)
    if not isinstance(units, str):
        units = "metric"

    request_url = f"{WEATHER_API_BASE}/weather"
    request_params = {
        "q": location,
        "appid": api_key,
        "units": units,
    }
    logger.info("Making request to %s with params: q=%s, units=%s", request_url, location, units)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(request_url, params=request_params)

        logger.info("Response status: %d", response.status_code)

        if response.status_code == 401:
            error_body = response.text
            logger.error("OpenWeather 401 response: %s", error_body)
            raise ValueError(
                f"Invalid OpenWeather API key. Key starts with: {api_key[:8]}... "
                f"API response: {error_body}"
            )
        if response.status_code == 404:
            raise ValueError(f"Location not found: {location}")

        response.raise_for_status()
        data = response.json()

    logger.info("Retrieved weather for %s", data.get("name", location))

    return CurrentWeatherResult(
        location=data.get("name", location),
        country=data.get("sys", {}).get("country", ""),
        coordinates=Coordinates(
            latitude=data.get("coord", {}).get("lat", 0),
            longitude=data.get("coord", {}).get("lon", 0),
        ),
        temperature=_parse_temperature(data.get("main", {})),
        humidity=data.get("main", {}).get("humidity", 0),
        pressure=data.get("main", {}).get("pressure", 0),
        visibility=data.get("visibility", 0),
        wind=_parse_wind(data.get("wind", {})),
        clouds=data.get("clouds", {}).get("all", 0),
        weather=_parse_weather_condition(data.get("weather", [])),
        timestamp=data.get("dt", 0),
        timezone=data.get("timezone", 0),
    )


@mcp.tool()
async def get_weather_forecast(
    location: str = Field(
        description="City name, optionally with country code (e.g., 'Paris' or 'Paris,FR')"
    ),
    units: str = Field(
        default="metric",
        description="Temperature units: 'metric' (Celsius), 'imperial' (Fahrenheit), or 'standard' (Kelvin)",
    ),
) -> WeatherForecastResult:
    """
    Get 5-day weather forecast with 3-hour intervals for a location.

    Returns up to 40 forecast data points covering the next 5 days,
    including temperature, precipitation probability, wind, and conditions.
    """
    creds = await get_credentials()
    api_key = (creds.get("api_key") or creds.get("API_KEY") or creds.get("apiKey") or "").strip()

    if not api_key:
        raise ValueError(f"OpenWeather API key not configured. Keys: {list(creds.keys())}")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{WEATHER_API_BASE}/forecast",
            params={
                "q": location,
                "appid": api_key,
                "units": units,
            },
        )

        if response.status_code == 401:
            raise ValueError(f"Invalid OpenWeather API key. Response: {response.text}")
        if response.status_code == 404:
            raise ValueError(f"Location not found: {location}")

        response.raise_for_status()
        data = response.json()

    city = data.get("city", {})
    forecasts = []

    for item in data.get("list", []):
        forecast = ForecastItem(
            timestamp=item.get("dt", 0),
            datetime_text=item.get("dt_txt", ""),
            temperature=_parse_temperature(item.get("main", {})),
            humidity=item.get("main", {}).get("humidity", 0),
            pressure=item.get("main", {}).get("pressure", 0),
            wind=_parse_wind(item.get("wind", {})),
            clouds=item.get("clouds", {}).get("all", 0),
            weather=_parse_weather_condition(item.get("weather", [])),
            precipitation_probability=item.get("pop", 0),
            rain_volume=item.get("rain", {}).get("3h") if item.get("rain") else None,
            snow_volume=item.get("snow", {}).get("3h") if item.get("snow") else None,
        )
        forecasts.append(forecast)

    logger.info(
        "Retrieved %d forecast items for %s", len(forecasts), city.get("name", location)
    )

    return WeatherForecastResult(
        location=city.get("name", location),
        country=city.get("country", ""),
        coordinates=Coordinates(
            latitude=city.get("coord", {}).get("lat", 0),
            longitude=city.get("coord", {}).get("lon", 0),
        ),
        timezone=city.get("timezone", 0),
        forecast_count=len(forecasts),
        forecasts=forecasts,
    )


@mcp.tool()
async def geocode_location(
    query: str = Field(
        description="Location search query (city name, state, country) e.g., 'New York, US' or 'Tokyo'"
    ),
    limit: int = Field(
        default=5,
        description="Maximum number of results to return (1-5)",
    ),
) -> GeocodingResult:
    """
    Convert a location name to geographic coordinates.

    Useful for getting precise latitude/longitude for a city or place name.
    Returns multiple matches if the query is ambiguous.
    """
    creds = await get_credentials()
    api_key = (creds.get("api_key") or creds.get("API_KEY") or creds.get("apiKey") or "").strip()

    if not api_key:
        raise ValueError(f"OpenWeather API key not configured. Keys: {list(creds.keys())}")

    # Clamp limit to valid range
    limit = max(1, min(5, limit))

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GEO_API_BASE}/direct",
            params={
                "q": query,
                "limit": limit,
                "appid": api_key,
            },
        )

        if response.status_code == 401:
            raise ValueError(f"Invalid OpenWeather API key. Response: {response.text}")

        response.raise_for_status()
        data = response.json()

    locations = []
    for item in data:
        loc = GeocodingLocation(
            name=item.get("name", ""),
            local_names=item.get("local_names"),
            latitude=item.get("lat", 0),
            longitude=item.get("lon", 0),
            country=item.get("country", ""),
            state=item.get("state"),
        )
        locations.append(loc)

    logger.info("Geocoding '%s' found %d results", query, len(locations))

    return GeocodingResult(
        query=query,
        results_count=len(locations),
        locations=locations,
    )


@mcp.tool()
async def reverse_geocode(
    latitude: float = Field(description="Latitude coordinate (-90 to 90)"),
    longitude: float = Field(description="Longitude coordinate (-180 to 180)"),
    limit: int = Field(
        default=5,
        description="Maximum number of results to return (1-5)",
    ),
) -> ReverseGeocodingResult:
    """
    Convert geographic coordinates to location names.

    Given latitude and longitude, returns the location names (city, state, country)
    at or near those coordinates.
    """
    creds = await get_credentials()
    api_key = (creds.get("api_key") or creds.get("API_KEY") or creds.get("apiKey") or "").strip()

    if not api_key:
        raise ValueError(f"OpenWeather API key not configured. Keys: {list(creds.keys())}")

    # Validate coordinates
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180")

    # Clamp limit to valid range
    limit = max(1, min(5, limit))

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GEO_API_BASE}/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "limit": limit,
                "appid": api_key,
            },
        )

        if response.status_code == 401:
            raise ValueError(f"Invalid OpenWeather API key. Response: {response.text}")

        response.raise_for_status()
        data = response.json()

    locations = []
    for item in data:
        loc = GeocodingLocation(
            name=item.get("name", ""),
            local_names=item.get("local_names"),
            latitude=item.get("lat", 0),
            longitude=item.get("lon", 0),
            country=item.get("country", ""),
            state=item.get("state"),
        )
        locations.append(loc)

    logger.info(
        "Reverse geocoding (%.4f, %.4f) found %d results",
        latitude,
        longitude,
        len(locations),
    )

    return ReverseGeocodingResult(
        latitude=latitude,
        longitude=longitude,
        results_count=len(locations),
        locations=locations,
    )


@mcp.tool()
async def diagnose_api_key() -> DiagnosticResult:
    """
    Diagnose API key configuration and connectivity.

    Tests the OpenWeather API connection and returns detailed diagnostic
    information to help troubleshoot authentication issues.
    """
    creds = await get_credentials()
    api_key = (creds.get("api_key") or creds.get("API_KEY") or creds.get("apiKey") or "").strip()

    # Get hex representation to check for invisible characters
    hex_preview = api_key[:16].encode().hex() if api_key else "empty"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{WEATHER_API_BASE}/weather",
            params={"q": "London", "appid": api_key, "units": "metric"},
        )

    return DiagnosticResult(
        api_key_length=len(api_key),
        api_key_preview=api_key[:8] + "..." if len(api_key) >= 8 else api_key,
        api_key_hex_preview=hex_preview,
        test_url=f"{WEATHER_API_BASE}/weather?q=London&units=metric&appid=***",
        response_status=response.status_code,
        response_body=response.text[:500],
        success=response.status_code == 200,
    )


def main():
    """Start the OpenWeather MCP server."""
    load_dotenv()
    if os.environ.get("ENVIRONMENT") != "local":
        host = GumstackHost(mcp)
        host.run(host="0.0.0.0", port=PORT)
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
