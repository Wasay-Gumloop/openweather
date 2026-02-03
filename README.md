# OpenWeather MCP Server

A GumStack MCP server that provides weather data tools via the OpenWeather API.

## Features

- **Current Weather**: Get real-time weather conditions for any location
- **5-Day Forecast**: Weather predictions with 3-hour intervals
- **Geocoding**: Convert location names to coordinates and vice versa

## Setup

```bash
# Install dependencies
uv sync

# Copy environment file
cp env.example .env

# Edit .env with your OpenWeather API key
```

## Local Development

```bash
# Run the server
./run.sh

# Or directly
uv run openweather
```

## Authentication

This server uses user-provided credentials. In local development, set `ENVIRONMENT=local` and `LOCAL_API_KEY` in your `.env` file.

When deployed to GumStack, users will enter their OpenWeather API key in the GumStack UI.

Get your free API key at: https://openweathermap.org/api

## Tools

### `get_current_weather`

Get current weather conditions for a specific location.

**Parameters:**
- `location` (required): City name, optionally with country code (e.g., "London" or "London,UK")
- `units` (optional): Temperature units - "metric" (Celsius), "imperial" (Fahrenheit), or "standard" (Kelvin). Default: "metric"

**Returns:** Current temperature, humidity, wind speed/direction, pressure, visibility, cloudiness, and weather conditions.

### `get_weather_forecast`

Get 5-day weather forecast with 3-hour intervals.

**Parameters:**
- `location` (required): City name, optionally with country code (e.g., "Paris" or "Paris,FR")
- `units` (optional): Temperature units - "metric", "imperial", or "standard". Default: "metric"

**Returns:** Up to 40 forecast data points with temperature, precipitation probability, wind, and conditions.

### `geocode_location`

Convert a location name to geographic coordinates.

**Parameters:**
- `query` (required): Location search query (e.g., "New York, US" or "Tokyo")
- `limit` (optional): Maximum results to return (1-5). Default: 5

**Returns:** List of matching locations with latitude, longitude, country, and state.

### `reverse_geocode`

Convert geographic coordinates to location names.

**Parameters:**
- `latitude` (required): Latitude coordinate (-90 to 90)
- `longitude` (required): Longitude coordinate (-180 to 180)
- `limit` (optional): Maximum results to return (1-5). Default: 5

**Returns:** List of location names at or near the specified coordinates.

## Testing

```bash
# Run all tests
uv run pytest

# Run HTTP transport test
uv run pytest tests/test_http.py -v
```

## Deployment

This server is designed for deployment to GumStack. The server:
- Listens on `0.0.0.0:8000/mcp` (or PORT env var)
- Provides a `/health_check` endpoint for container orchestration
- Uses stateless HTTP transport for scalability

## API Reference

This server uses the [OpenWeather API](https://openweathermap.org/api):
- Current Weather: `/data/2.5/weather`
- 5-Day Forecast: `/data/2.5/forecast`
- Geocoding: `/geo/1.0/direct`
- Reverse Geocoding: `/geo/1.0/reverse`
