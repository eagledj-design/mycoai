"""Resumen meteorológico de los días completos anteriores a la consulta."""

from datetime import date, timedelta

import requests

URL = "https://api.open-meteo.com/v1/forecast"
SOURCE = "https://open-meteo.com/en/docs"


def recent_weather(latitude: float, longitude: float, today: date) -> dict | None:
    response = requests.get(URL, params={
        "latitude": round(latitude, 2),
        "longitude": round(longitude, 2),
        "daily": "precipitation_sum,temperature_2m_mean",
        "past_days": 14,
        "forecast_days": 1,
        "timezone": "auto",
    }, timeout=5)
    response.raise_for_status()
    daily = response.json()["daily"]
    start = today - timedelta(days=14)
    samples = {
        date.fromisoformat(day): (rain, temperature)
        for day, rain, temperature in zip(
            daily["time"], daily["precipitation_sum"], daily["temperature_2m_mean"], strict=True
        )
        if rain is not None and temperature is not None
    }
    expected = [start + timedelta(days=offset) for offset in range(14)]
    if not all(day in samples for day in expected):
        return None
    values = [samples[day] for day in expected]
    return {
        "from": start.isoformat(),
        "to": (today - timedelta(days=1)).isoformat(),
        "precipitation_7d_mm": round(sum(rain for rain, _ in values[-7:]), 1),
        "precipitation_14d_mm": round(sum(rain for rain, _ in values), 1),
        "mean_temperature_7d_c": round(sum(temp for _, temp in values[-7:]) / 7, 1),
        "source": SOURCE,
    }
