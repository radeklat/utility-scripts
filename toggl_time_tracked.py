#!/usr/bin/env python

from base64 import b64encode
from collections import defaultdict
from datetime import datetime, timedelta
from enum import StrEnum
from sys import argv

import requests
from pydantic import BaseSettings
from pydantic.main import BaseModel


class Settings(BaseSettings):
    API_TOKEN: str
    PROJECT_ID: int
    BUDGET_HOURS_PER_DAY: int
    BUDGET_DAYS_PER_WEEK: int
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
        params={
            "start_date": monday.strftime(API_DATE_FMT),
            "end_date": sunday.strftime(API_DATE_FMT),
        },
        headers=HEADERS,
    )

    assert data.status_code == 200, f"Unexpected status code {data.status_code}"

    return [TimeEntry(**time_entry) for time_entry in data.json()]


def calculate_duration_in_seconds(
    time_entries: list[TimeEntry], project_id: int
) -> tuple[int, defaultdict[str, int], State]:
    duration_sec = 0
    state: State = State.NOT_RUNNING
    per_day_duration_sec: defaultdict[str, int] = defaultdict(int)

    for time_entry in time_entries:
        if time_entry.duration == 0:
            continue

        if time_entry.project_id is None or time_entry.project_id != project_id:
            if time_entry.duration < 0:
                state = State.RUNNING_OTHER_PROJECT
            continue

        if time_entry.duration > 0:
            duration = time_entry.duration
        else:
            duration = (datetime.now().astimezone() - time_entry.start).total_seconds()
            state = State.RUNNING_SELECTED_PROJECT

        duration_sec += duration
        per_day_duration_sec[time_entry.start.strftime(API_DATE_FMT)] += duration

    return duration_sec, per_day_duration_sec, state


def main():
    print(settings.SEPARATOR, end="")
    time_entries = get_this_week_time_entries()
    duration_sec, per_day_duration_sec, state = calculate_duration_in_seconds(
        time_entries, settings.PROJECT_ID
    )

    if state == State.RUNNING_SELECTED_PROJECT:
        weekday = datetime.today().isoweekday()
        elapsed_days = min(weekday, settings.BUDGET_DAYS_PER_WEEK)
        remaining_sec = (
            settings.BUDGET_HOURS_PER_DAY * 60 * 60 * elapsed_days - duration_sec
        )
        if remaining_sec > 0:
            multiplier = 1
        else:
            multiplier = -1
            print("-", end="")

        print(
            datetime.utcfromtimestamp(remaining_sec * multiplier)
            .strftime("%H:%M")
            .removeprefix("0")
        )
    else:
        print(state)

    if len(argv) >= 2:
        if argv[1].startswith("-v"):
            print(
                "\n".join(
                    f"{day}: {datetime.utcfromtimestamp(duration_sec).strftime('%H:%M')}"
                    for day, duration_sec in per_day_duration_sec.items()
                )
            )

        if argv[1].startswith("-vv"):
            print("\n".join(str(time_entry) for time_entry in sorted(time_entries, key=lambda x: x.start)))


if __name__ == "__main__":
    main()
