#!/usr/bin/env python3
"""Unit tests for OpenWeather MCP server tools."""

import os
from unittest.mock import AsyncMock, patch

import pytest

# Set environment to local before importing
os.environ["ENVIRONMENT"] = "local"
os.environ["LOCAL_API_KEY"] = "test_api_key_12345"

from openweather.models import (
    CurrentWeatherResult,
    GeocodingResult,
    ReverseGeocodingResult,
    WeatherForecastResult,
)
from openweather.server import (
    geocode_location,
    get_current_weather,
    get_weather_forecast,
    reverse_geocode,
)


# Sample API responses
CURRENT_WEATHER_RESPONSE = {
    "coord": {"lon": -0.1257, "lat": 51.5085},
    "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
    "main": {
        "temp": 15.5,
        "feels_like": 14.2,
        "temp_min": 13.0,
        "temp_max": 17.0,
        "pressure": 1015,
        "humidity": 65,
    },
    "visibility": 10000,
    "wind": {"speed": 3.5, "deg": 220, "gust": 5.0},
    "clouds": {"all": 10},
    "dt": 1700000000,
    "sys": {"country": "GB"},
    "timezone": 0,
    "name": "London",
}

FORECAST_RESPONSE = {
    "city": {
        "name": "Paris",
        "country": "FR",
        "coord": {"lat": 48.8566, "lon": 2.3522},
        "timezone": 3600,
    },
    "list": [
        {
            "dt": 1700000000,
            "dt_txt": "2024-11-15 12:00:00",
            "main": {
                "temp": 12.0,
                "feels_like": 10.5,
                "temp_min": 11.0,
                "temp_max": 13.0,
                "pressure": 1020,
                "humidity": 70,
            },
            "weather": [
                {"id": 801, "main": "Clouds", "description": "few clouds", "icon": "02d"}
            ],
            "clouds": {"all": 20},
            "wind": {"speed": 2.5, "deg": 180},
            "pop": 0.1,
        },
        {
            "dt": 1700010800,
            "dt_txt": "2024-11-15 15:00:00",
            "main": {
                "temp": 14.0,
                "feels_like": 12.5,
                "temp_min": 13.0,
                "temp_max": 15.0,
                "pressure": 1018,
                "humidity": 60,
            },
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "clouds": {"all": 5},
            "wind": {"speed": 3.0, "deg": 200},
            "pop": 0.0,
        },
    ],
}

GEOCODING_RESPONSE = [
    {
        "name": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
        "country": "US",
        "state": "New York",
        "local_names": {"en": "New York", "es": "Nueva York"},
    },
    {
        "name": "New York",
        "lat": 42.9399,
        "lon": -75.6201,
        "country": "US",
        "state": "New York",
    },
]

REVERSE_GEOCODING_RESPONSE = [
    {
        "name": "Manhattan",
        "lat": 40.7831,
        "lon": -73.9712,
        "country": "US",
        "state": "New York",
    }
]


class MockResponse:
    """Mock httpx response."""

    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.text = str(json_data) if json_data else ""

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.mark.asyncio
async def test_get_current_weather():
    """Test get_current_weather returns correct data structure."""
    mock_response = MockResponse(CURRENT_WEATHER_RESPONSE)

    with patch("openweather.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await get_current_weather(location="London,UK", units="metric")

        assert isinstance(result, CurrentWeatherResult)
        assert result.location == "London"
        assert result.country == "GB"
        assert result.temperature.current == 15.5
        assert result.humidity == 65
        assert result.wind.speed == 3.5
        assert result.weather.main == "Clear"


@pytest.mark.asyncio
async def test_get_weather_forecast():
    """Test get_weather_forecast returns correct data structure."""
    mock_response = MockResponse(FORECAST_RESPONSE)

    with patch("openweather.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await get_weather_forecast(location="Paris,FR", units="metric")

        assert isinstance(result, WeatherForecastResult)
        assert result.location == "Paris"
        assert result.country == "FR"
        assert result.forecast_count == 2
        assert len(result.forecasts) == 2
        assert result.forecasts[0].temperature.current == 12.0
        assert result.forecasts[0].precipitation_probability == 0.1


@pytest.mark.asyncio
async def test_geocode_location():
    """Test geocode_location returns correct data structure."""
    mock_response = MockResponse(GEOCODING_RESPONSE)

    with patch("openweather.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await geocode_location(query="New York, US", limit=5)

        assert isinstance(result, GeocodingResult)
        assert result.query == "New York, US"
        assert result.results_count == 2
        assert len(result.locations) == 2
        assert result.locations[0].name == "New York"
        assert result.locations[0].latitude == 40.7128
        assert result.locations[0].country == "US"


@pytest.mark.asyncio
async def test_reverse_geocode():
    """Test reverse_geocode returns correct data structure."""
    mock_response = MockResponse(REVERSE_GEOCODING_RESPONSE)

    with patch("openweather.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result = await reverse_geocode(latitude=40.7128, longitude=-74.0060, limit=1)

        assert isinstance(result, ReverseGeocodingResult)
        assert result.latitude == 40.7128
        assert result.longitude == -74.0060
        assert result.results_count == 1
        assert result.locations[0].name == "Manhattan"


@pytest.mark.asyncio
async def test_reverse_geocode_invalid_latitude():
    """Test reverse_geocode raises error for invalid latitude."""
    with pytest.raises(ValueError, match="Latitude must be between"):
        await reverse_geocode(latitude=100.0, longitude=0.0)


@pytest.mark.asyncio
async def test_reverse_geocode_invalid_longitude():
    """Test reverse_geocode raises error for invalid longitude."""
    with pytest.raises(ValueError, match="Longitude must be between"):
        await reverse_geocode(latitude=0.0, longitude=200.0)


@pytest.mark.asyncio
async def test_get_current_weather_not_found():
    """Test get_current_weather handles 404 errors."""
    mock_response = MockResponse({}, status_code=404)

    with patch("openweather.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        with pytest.raises(ValueError, match="Location not found"):
            await get_current_weather(location="NonexistentCity123")


@pytest.mark.asyncio
async def test_get_current_weather_invalid_api_key():
    """Test get_current_weather handles 401 errors."""
    mock_response = MockResponse({}, status_code=401)

    with patch("openweather.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        with pytest.raises(ValueError, match="Invalid OpenWeather API key"):
            await get_current_weather(location="London")
