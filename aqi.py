#!/usr/bin/env python

import requests
from pydantic import BaseModel, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Budget(BaseModel):
    hours_per_day: int
    days_per_week: int = 5


class Settings(BaseSettings):
    PROMETHEUS_SERVER: AnyHttpUrl
    ROOM: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="AQI_")


def get_aqi(prometheus_server: str, room: str) -> str:
    query = f'sensors{{metric="aqi", sensor_name="total", sensor="{room}"}}'
    query_url = f"{prometheus_server}/api/v1/query?query={query}"

    try:
        response = requests.get(query_url, timeout=5)
    except requests.exceptions.ConnectTimeout:
        return ""
    except requests.exceptions.RequestException:
        return "Err"

    response.raise_for_status()

    json_response = response.json()

    if "data" in json_response and "result" in json_response["data"] and json_response["data"]["result"]:
        return f"{float(json_response['data']['result'][0]['value'][1]):.0f}"
    else:
        return "N/A"


def aqi_to_emoji(level: str) -> str:
    if level in ["N/A", "Err"]:
        return level

    if not level:
        return "🤍"

    level = int(level)

    if level >= 80:
        return "💚"
    if level >= 60:
        return "💛"
    if level >= 40:
        return "🧡"
    if level >= 20:
        return "❤️"
    return "💜"


if __name__ == "__main__":
    settings = Settings()
    aqi = get_aqi(settings.PROMETHEUS_SERVER, settings.ROOM)
    print(f" {aqi_to_emoji(aqi)} | ")
