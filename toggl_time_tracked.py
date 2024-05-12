#!/usr/bin/env python
"""Shows remaining time to track in defined budgets.

Toggl API documentation: https://engineering.toggl.com/docs/
"""
import dataclasses
from base64 import b64encode
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from functools import cache
from sys import argv
from typing import Any

import requests
from pydantic import ConfigDict, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Budget(BaseModel):
    hours_per_day: int
    days_per_week: int = 5


class Settings(BaseSettings):
    API_TOKEN: str
    WORKSPACE_ID: int
    BUDGETS: dict[int, Budget] = Field(default_factory=list)
    SEPARATOR: str = "  |  "
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="toggl_")


class TogglTimeEntry(BaseModel):
    project_id: int | None = None
    duration: int
    duronly: bool
    start: datetime
    stop: datetime | None = None
    model_config = ConfigDict(extra="ignore")


class TogglProject(BaseModel):
    id: int
    name: str
    client_id: int | None
    model_config = ConfigDict(extra="ignore")


class State(StrEnum):
    RUNNING_WITH_PROJECT = ""
    RUNNING_NO_PROJECT = "⚠️"
    NOT_RUNNING = "⚪️"


settings = Settings()

API_DATE_FMT: str = "%Y-%m-%d"


@dataclasses.dataclass(frozen=True)
class TogglAPI:
    workspace_id: int
    api_token: str
    base_url: str = "https://api.track.toggl.com/api/v9"

    @property
    def _headers(self):
        return {
            "content-type": "application/json",
            "Authorization": "Basic %s" % b64encode(f"{self.api_token}:api_token".encode()).decode("ascii"),
        }

    def _request(self, path: str, params: dict = None) -> Any:
        data = requests.get(f"{self.base_url}/{path}", params=params, headers=self._headers)
        data.raise_for_status()
        return data.json()

    @cache
    def get_projects(self) -> list[TogglProject]:
        """See https://engineering.toggl.com/docs/api/projects#get-workspaceprojects for more information."""
        data = self._request(
            f"workspaces/{self.workspace_id}/projects",
            {"active": True},
        )

        return [TogglProject(**project) for project in data]

    def get_clients_to_projects(self) -> dict[int, set[int]]:
        clients_to_projects = defaultdict(set)

        for project in self.get_projects():
            clients_to_projects[project.client_id].add(project.id)

        return clients_to_projects

    def get_projects_to_client(self) -> dict[int | None, int]:
        return {project.id: project.client_id for project in self.get_projects()}

    def get_this_week_time_entries(self) -> list[TogglTimeEntry]:
        today = datetime.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=7)

        data = self._request(
            f"me/time_entries",
            {"start_date": monday.strftime(API_DATE_FMT), "end_date": sunday.strftime(API_DATE_FMT)},
        )

        return [TogglTimeEntry(**time_entry) for time_entry in data]


def calculate_duration_in_seconds(
    time_entries: list[TogglTimeEntry],
    clients_to_projects: dict[int, set[int]],
    projects_to_client: dict[int, int],
) -> tuple[int, defaultdict[str, int], State, int | None]:
    duration_sec = 0
    state: State = State.NOT_RUNNING
    per_day_duration_sec: defaultdict[str, int] = defaultdict(int)
    client_id = None
    project_ids = set()

    for time_entry in time_entries:
        if time_entry.duration < 0:
            if time_entry.project_id is not None:
                state = State.RUNNING_WITH_PROJECT
                client_id = projects_to_client[time_entry.project_id]
                project_ids = clients_to_projects[client_id]
            else:
                state = State.RUNNING_NO_PROJECT

            break

    if state != State.RUNNING_WITH_PROJECT:
        return duration_sec, per_day_duration_sec, state, client_id

    for time_entry in time_entries:
        if time_entry.duration == 0:
            continue

        if time_entry.project_id not in project_ids:
            continue

        if time_entry.duration > 0:
            duration = time_entry.duration
        else:
            duration = (datetime.now().astimezone() - time_entry.start).total_seconds()

        duration_sec += duration
        per_day_duration_sec[time_entry.start.strftime(API_DATE_FMT)] += duration

    return duration_sec, per_day_duration_sec, state, client_id


def secs_to_hours_minutes(secs: int) -> str:
    return datetime.fromtimestamp(secs, tz=timezone.utc).strftime("%H:%M").removeprefix("0")


def main():
    api = TogglAPI(workspace_id=settings.WORKSPACE_ID, api_token=settings.API_TOKEN)

    print(settings.SEPARATOR, end="")
    time_entries = api.get_this_week_time_entries()
    clients_to_projects = api.get_clients_to_projects()
    projects_to_client = api.get_projects_to_client()

    (
        duration_sec,
        per_day_duration_sec,
        state,
        client_id,
    ) = calculate_duration_in_seconds(time_entries, clients_to_projects, projects_to_client)

    if state == State.RUNNING_WITH_PROJECT:
        if client_id in settings.BUDGETS:
            budget = settings.BUDGETS[client_id]
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
