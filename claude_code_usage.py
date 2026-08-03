#!/usr/bin/env python

"""Show Claude Code quota usage as a GNOME Shell Executor status bar segment.

Renders the percentage used of each rate limit window plus the time remaining
until it resets, for example:

    🕐 11% 2.8h | 📅 2% 6d |

Data comes from the same endpoint the interactive ``/usage`` command calls:
``GET https://api.anthropic.com/api/oauth/usage``, authenticated with the OAuth
access token Claude Code stores in ``~/.claude/.credentials.json``.

That endpoint is UNDOCUMENTED and may change or disappear without notice, so
every failure path here degrades to printing nothing rather than raising.

This script never refreshes the OAuth token. Refreshing rotates the refresh
token and would race Claude Code's own refresh, which can log you out. When the
access token has expired, no request is made and the segment goes blank until
Claude Code refreshes it during normal use.

Installation: append an entry with a fresh uuid to the Executor extension's
dconf array ``/org/gnome/shell/extensions/executor/right-commands-json``, with
an interval of 60 and the command:

    bash -c -l "cd /<REPO_ROOT>; poetry run ./claude_code_usage.py"
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final

import requests
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.constants import SEP

USAGE_URL: Final[str] = "https://api.anthropic.com/api/oauth/usage"


def format_fractional_hours(remaining: timedelta) -> str:
    """Hours to one decimal place, e.g. ``3.5h``."""
    return f"{remaining.total_seconds() / 3600:.1f}h"


def format_days_or_hours(remaining: timedelta) -> str:
    """Whole days once past 24h, whole hours below that, e.g. ``5d`` or ``7h``."""
    hours = round(remaining.total_seconds() / 3600)

    return f"{hours // 24}d" if hours >= 24 else f"{hours}h"


@dataclass(frozen=True)
class WindowSpec:
    key: str
    icon: str
    format_remaining: Callable[[timedelta], str]


# Rate limit windows to display, in order. Windows missing from the response or
# without a utilisation are skipped, so listing one that is unused on the current
# plan costs nothing.
WINDOWS: Final[tuple[WindowSpec, ...]] = (
    WindowSpec("five_hour", "🕐", format_fractional_hours),
    WindowSpec("seven_day", "📅", format_days_or_hours),
)


class Settings(BaseSettings):
    CREDENTIALS_FILE: Path = Field(default=Path.home() / ".claude" / ".credentials.json")
    CACHE_FILE: Path = Field(default=Path("/tmp/claude_code_usage.json"))
    MAX_CACHE_AGE_MINUTES: int = 10
    TIMEOUT: int = 5

    model_config = SettingsConfigDict(
        env_prefix="CLAUDE_USAGE_",
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CREDENTIALS_FILE", "CACHE_FILE")
    @classmethod
    def expand_user(cls, value: Path) -> Path:
        return value.expanduser()


class Window(BaseModel):
    """One rate limit window. ``utilization`` is already a percentage, 0-100."""

    utilization: float | None = None
    resets_at: datetime | None = None


class Usage(BaseModel):
    """Windows keyed by response key, plus when they were fetched."""

    fetched_at: datetime
    windows: dict[str, Window] = Field(default_factory=dict)


def read_access_token(credentials_file: Path) -> str | None:
    """Return the OAuth access token, or None if missing or already expired."""
    try:
        oauth = json.loads(credentials_file.read_text())["claudeAiOauth"]
        token = oauth["accessToken"]
        expires_at = datetime.fromtimestamp(oauth["expiresAt"] / 1000, timezone.utc)
    except (OSError, ValueError, KeyError, TypeError):
        return None

    if not token or expires_at <= datetime.now(timezone.utc):
        return None

    return token


def fetch_usage(token: str, timeout: int) -> Usage | None:
    try:
        response = requests.get(
            USAGE_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.exceptions.RequestException, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    usage = Usage(fetched_at=datetime.now(timezone.utc))

    for spec in WINDOWS:
        if isinstance(window := payload.get(spec.key), dict):
            try:
                usage.windows[spec.key] = Window.model_validate(window)
            except ValueError:
                continue

    return usage


def read_cache(cache_file: Path, max_age: timedelta) -> Usage | None:
    try:
        usage = Usage.model_validate_json(cache_file.read_text())
    except (OSError, ValueError):
        return None

    return usage if usage.fetched_at > datetime.now(timezone.utc) - max_age else None


def write_cache(cache_file: Path, usage: Usage) -> None:
    """Persist derived percentages and timestamps only, never the token."""
    try:
        cache_file.write_text(usage.model_dump_json())
    except OSError:
        pass


def format_usage(usage: Usage) -> str:
    segments = []

    now = datetime.now(timezone.utc)

    for spec in WINDOWS:
        window = usage.windows.get(spec.key)

        if window is None or window.utilization is None:
            continue

        # A cached window past its reset holds a pre-reset percentage that is now
        # far too high. Better to show nothing than to imply a limit is near.
        if window.resets_at is not None and window.resets_at <= now:
            continue

        remaining = spec.format_remaining(window.resets_at - now) if window.resets_at else ""
        # Floored, not rounded, to match how /usage renders the same numbers.
        segments.append(f"{spec.icon} {int(window.utilization)}%{f' {remaining}' if remaining else ''}")

    return " | ".join(segments)


def main() -> None:
    settings = Settings()

    usage = None
    if (token := read_access_token(settings.CREDENTIALS_FILE)) is not None:
        usage = fetch_usage(token, settings.TIMEOUT)

    if usage is not None:
        write_cache(settings.CACHE_FILE, usage)
    else:
        usage = read_cache(settings.CACHE_FILE, timedelta(minutes=settings.MAX_CACHE_AGE_MINUTES))

    if usage is not None and (formatted := format_usage(usage)):
        print(f"{formatted}{SEP}", end="")


if __name__ == "__main__":
    main()
