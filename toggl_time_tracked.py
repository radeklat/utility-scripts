#!/usr/bin/env python

from base64 import b64encode
from datetime import datetime, timedelta
from enum import StrEnum

import requests
from pydantic import BaseSettings
from pydantic.main import BaseModel


class Settings(BaseSettings):
    API_TOKEN: str
    PROJECT_ID: int
    DAILY_HOURS_BUDGET: int
    SEPARATOR: str = "  |  "

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "toggl_"


class TimeEntry(BaseModel):
    project_id: int | None
    duration: int
    duronly: bool
    start: datetime
    stop: datetime | None

    class Config:
        extra = "ignore"


class State(StrEnum):
    RUNNING_SELECTED_PROJECT = ""
    RUNNING_OTHER_PROJECT = "⚠️"
    NOT_RUNNING = "⚪️"


settings = Settings()

HEADERS: dict[str, str] = {
    "content-type": "application/json",
    "Authorization": "Basic %s"
    % b64encode(f"{settings.API_TOKEN}:api_token".encode()).decode("ascii"),
}
API_DATE_FMT: str = "%Y-%m-%d"


def get_this_week_time_entries() -> list[TimeEntry]:
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    data = requests.get(
        "https://api.track.toggl.com/api/v9/me/time_entries",
        params={"start_date": monday.strftime(API_DATE_FMT), "end_date": sunday.strftime(API_DATE_FMT)},
        headers=HEADERS,
    )

    assert data.status_code == 200, f"Unexpected status code {data.status_code}"

    return [TimeEntry(**time_entry) for time_entry in data.json()]


def calculate_duration(time_entries: list[TimeEntry]) -> tuple[int, State]:
    duration_sec = 0
    state: State = State.NOT_RUNNING

    for time_entry in time_entries:
        if time_entry.project_id is None or time_entry.project_id != settings.PROJECT_ID:
            if time_entry.duration < 0:
                state = State.RUNNING_OTHER_PROJECT
        elif time_entry.duration > 0:
            duration_sec += time_entry.duration
        else:
            duration_sec += (datetime.now().astimezone() - time_entry.start).total_seconds()
            state = State.RUNNING_SELECTED_PROJECT

    return duration_sec, state


def main():
    print(settings.SEPARATOR, end="")
    duration, state = calculate_duration(get_this_week_time_entries())

    if state == State.RUNNING_SELECTED_PROJECT:
        weekday = datetime.today().isoweekday()
        remaining = settings.DAILY_HOURS_BUDGET * 60 * 60 * weekday - duration
        if remaining > 0:
            multiplier = 1
        else:
            multiplier = -1
            print("-", end="")

        print(datetime.utcfromtimestamp(remaining * multiplier).strftime("%H:%M").removeprefix("0"))
    else:
        print(state)


if __name__ == "__main__":
    main()
