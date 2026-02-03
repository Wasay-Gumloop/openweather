"""Pydantic models for OpenWeather API responses."""

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Geographic coordinates."""

    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")


class WeatherCondition(BaseModel):
    """Weather condition details."""

    main: str = Field(description="Group of weather parameters (Rain, Snow, Clouds, etc.)")
    description: str = Field(description="Weather condition within the group")
    icon: str = Field(description="Weather icon ID")


class Temperature(BaseModel):
    """Temperature information."""

    current: float = Field(description="Current temperature in specified units")
    feels_like: float = Field(description="Human perception of temperature")
    min: float = Field(description="Minimum temperature at the moment")
    max: float = Field(description="Maximum temperature at the moment")


class Wind(BaseModel):
    """Wind information."""

    speed: float = Field(description="Wind speed in m/s (metric) or mph (imperial)")
    direction: int = Field(description="Wind direction in degrees (meteorological)")
    gust: float | None = Field(default=None, description="Wind gust speed if available")


class CurrentWeatherResult(BaseModel):
    """Current weather data for a location."""

    location: str = Field(description="City/location name")
    country: str = Field(description="Country code (ISO 3166)")
    coordinates: Coordinates = Field(description="Geographic coordinates")
    temperature: Temperature = Field(description="Temperature data")
    humidity: int = Field(description="Humidity percentage")
    pressure: int = Field(description="Atmospheric pressure in hPa")
    visibility: int = Field(description="Visibility in meters")
    wind: Wind = Field(description="Wind conditions")
    clouds: int = Field(description="Cloudiness percentage")
    weather: WeatherCondition = Field(description="Weather condition")
    timestamp: int = Field(description="Time of data calculation (Unix UTC)")
    timezone: int = Field(description="Shift in seconds from UTC")


class ForecastItem(BaseModel):
    """Single forecast time point."""

    timestamp: int = Field(description="Time of data forecasted (Unix UTC)")
    datetime_text: str = Field(description="Human-readable date/time string")
    temperature: Temperature = Field(description="Temperature data")
    humidity: int = Field(description="Humidity percentage")
    pressure: int = Field(description="Atmospheric pressure in hPa")
    wind: Wind = Field(description="Wind conditions")
    clouds: int = Field(description="Cloudiness percentage")
    weather: WeatherCondition = Field(description="Weather condition")
    precipitation_probability: float = Field(
        description="Probability of precipitation (0-1)"
    )
    rain_volume: float | None = Field(
        default=None, description="Rain volume for last 3 hours in mm"
    )
    snow_volume: float | None = Field(
        default=None, description="Snow volume for last 3 hours in mm"
    )


class WeatherForecastResult(BaseModel):
    """5-day weather forecast with 3-hour intervals."""

    location: str = Field(description="City/location name")
    country: str = Field(description="Country code (ISO 3166)")
    coordinates: Coordinates = Field(description="Geographic coordinates")
    timezone: int = Field(description="Shift in seconds from UTC")
    forecast_count: int = Field(description="Number of forecast items")
    forecasts: list[ForecastItem] = Field(description="List of forecast time points")


class GeocodingLocation(BaseModel):
    """Geocoded location result."""

    name: str = Field(description="Name of the found location")
    local_names: dict[str, str] | None = Field(
        default=None, description="Name of the found location in different languages"
    )
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    country: str = Field(description="Country code (ISO 3166)")
    state: str | None = Field(default=None, description="State/region name if available")


class GeocodingResult(BaseModel):
    """Result of geocoding a location query."""

    query: str = Field(description="Original search query")
    results_count: int = Field(description="Number of matching locations found")
    locations: list[GeocodingLocation] = Field(description="List of matching locations")


class ReverseGeocodingResult(BaseModel):
    """Result of reverse geocoding coordinates."""

    latitude: float = Field(description="Queried latitude")
    longitude: float = Field(description="Queried longitude")
    results_count: int = Field(description="Number of matching locations found")
    locations: list[GeocodingLocation] = Field(description="List of matching locations")
