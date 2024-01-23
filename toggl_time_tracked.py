#!/usr/bin/env python

from base64 import b64encode
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from sys import argv

import requests
from pydantic import ConfigDict, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Budget(BaseModel):
    hours_per_day: int
    days_per_week: int = 5


class Settings(BaseSettings):
    API_TOKEN: str
    BUDGETS: dict[int, Budget] = Field(default_factory=list)
    SEPARATOR: str = "  |  "
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="toggl_")


class TimeEntry(BaseModel):
    project_id: int | None = None
    duration: int
    duronly: bool
    start: datetime
    stop: datetime | None = None
    model_config = ConfigDict(extra="ignore")


class State(StrEnum):
    RUNNING_WITH_PROJECT = ""
    RUNNING_NO_PROJECT = "⚠️"
    NOT_RUNNING = "⚪️"


settings = Settings()

HEADERS: dict[str, str] = {
    "content-type": "application/json",
    "Authorization": "Basic %s" % b64encode(f"{settings.API_TOKEN}:api_token".encode()).decode("ascii"),
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
    time_entries: list[TimeEntry],
) -> tuple[int, defaultdict[str, int], State, int | None]:
    duration_sec = 0
    state: State = State.NOT_RUNNING
    per_day_duration_sec: defaultdict[str, int] = defaultdict(int)
    project_id = None

    for time_entry in time_entries:
        if time_entry.duration < 0:
            if time_entry.project_id is not None:
                state = State.RUNNING_WITH_PROJECT
                project_id = time_entry.project_id
            else:
                state = State.RUNNING_NO_PROJECT

            break

    if state != State.RUNNING_WITH_PROJECT:
        return duration_sec, per_day_duration_sec, state, project_id

    for time_entry in time_entries:
        if time_entry.duration == 0:
            continue

        if time_entry.project_id != project_id:
            continue

        if time_entry.duration > 0:
            duration = time_entry.duration
        else:
            duration = (datetime.now().astimezone() - time_entry.start).total_seconds()

        duration_sec += duration
        per_day_duration_sec[time_entry.start.strftime(API_DATE_FMT)] += duration

    return duration_sec, per_day_duration_sec, state, project_id


def secs_to_hours_minutes(secs: int) -> str:
    return datetime.fromtimestamp(secs, tz=timezone.utc).strftime("%H:%M").removeprefix("0")


def main():
    print(settings.SEPARATOR, end="")
    time_entries = get_this_week_time_entries()
    (
        duration_sec,
        per_day_duration_sec,
        state,
        project_id,
    ) = calculate_duration_in_seconds(time_entries)

    if state == State.RUNNING_WITH_PROJECT:
        if project_id in settings.BUDGETS:
            budget = settings.BUDGETS[project_id]
            weekday = datetime.today().isoweekday()
            elapsed_days = min(weekday, budget.days_per_week)
            remaining_sec = budget.hours_per_day * 60 * 60 * elapsed_days - duration_sec
            if remaining_sec > 0:
                multiplier = 1
            else:
                multiplier = -1
                print("-", end="")

            print(secs_to_hours_minutes(remaining_sec * multiplier))
        else:
            print(secs_to_hours_minutes(duration_sec))
    else:
        print(state)

    if len(argv) >= 2:
        if argv[1].startswith("-v"):
            print(
                "\n".join(
                    f"{day}: {secs_to_hours_minutes(duration_sec)}"
                    for day, duration_sec in per_day_duration_sec.items()
                )
            )

        if argv[1].startswith("-vv"):
            print("\n".join(str(time_entry) for time_entry in sorted(time_entries, key=lambda x: x.start)))


if __name__ == "__main__":
    main()
