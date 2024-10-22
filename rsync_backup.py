"""To install:

sudo crontab -e

Add:
# m h  dom mon dow   command
00 *  *   *   *     /<REPO_ROOT>/.venv/bin/python /<REPO_ROOT>/rsync_backup.py
"""

import datetime
import shutil
import subprocess
import sys
from functools import cache
from ipaddress import IPv4Address
from pathlib import Path
from typing import Iterable

from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.constants import SEP
from shared.metered_connection_status import is_internet_connection_metered
from shared.notify import Notifier


class Settings(BaseSettings):
    rsync_ssh_user: str
    rsync_port: int
    rsync_servers: list[str]
    rsync_target_folder: str
    rsync_log_file: Path = Path("/tmp/rsync_timeshift.log")
    rsync_min_upload_speed_in_mb: float = 5

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
notifier = Notifier()


def run_command(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)
    return result.stdout


def _format_number(number):
    for unit, divider, precision in [("G", 10**9, 1), ("M", 10**6, 1), ("k", 10**3, 1), ("", 1, 0)]:
        if number > divider:
            return f"{number / divider:.{precision}f}{unit}"


def _run_mirror_command(icon: str, source: str, exclude: Iterable[str] = ()) -> None:
    command = [
        "rsync",
        "-e",
        f"ssh -l {settings.rsync_ssh_user} -p {settings.rsync_port}",
        "--info=name0,del0,progress2",
        "--progress",
        "--inplace",
        "--links",
        "--hard-links",
        "--archive",
        "--human-readable",
        "--verbose",
        "--no-inc-recursive",
        "--delete",
        "--delete-excluded",
        "--prune-empty-dirs",
        *(f"--exclude='{_}'" for _ in exclude),
        source,
        f"{first_available_server()}::{settings.rsync_target_folder}",
    ]
    notifier.info(f"Backup started: {source}")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # While there is a process output, read the output line by line and write it to the log file
    with open(settings.rsync_log_file, "a") as log:
        while process.poll() is None:
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                output = None

                if line.endswith("files..."):
                    # Example: '1234 files...'
                    count = line.split(" ", 1)[0]
                    output = _format_number(int(count))
                elif "% " in line:
                    # Examples:
                    #   '34.25M   0%    5.19MB/s    0:00:06 (xfr#1186, to-chk=1168445/1170633)'
                    #   '34.25M   0%    5.19MB/s    0:00:06'
                    parts = line.split(maxsplit=4)
                    output = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]}"

                if output is not None:
                    log.seek(0)
                    log.truncate()
                    log.write(f"🔁{icon} {output}")
                    log.flush()

    if process.returncode != 0:
        notifier.error(f"Backup failed: {source}", process.stderr.read())
        return

    return


def mirror_timeshift() -> None:
    _run_mirror_command("⏳️", "/timeshift")


def mirror_home() -> None:
    excludes = [
        "SynologyDrive",
        ".SynologyDrive",
        "*/.git",
        "*/.venv",
        "*/__pycache__",
        "*/.mypy_cache",
        "*/.pytest_cache",
        "*/.ruff_cache",
        ".cache/pypoetry",
        ".cache/pre-commit",
        ".cache/google-chrome",
        ".config/Signal",
        ".config/Franz",
        ".config/google-chrome",
        ".local/share/JetBrains/Toolbox",
        ".local/share/Trash",
        ".local/share/virtualenv",
        ".local/lib",
        ".pyenv",
        ".npm",
        ".nvm",
    ]
    _run_mirror_command("🏡", "/home/rlat", excludes)

@cache
def first_available_server() -> str | None:
    if not shutil.which("nping"):
        notifier.critical("Skipping backup: nmap is not installed.", "Run 'sudo apt install nmap'.")
        return None

    for server in settings.rsync_servers:
        if "Successful connections: 1" in run_command(
            ["nping", "--tcp-connect", "-c", "1", "-p", str(settings.rsync_port), "-q", server]
        ):
            return server

    return None

def fast_upload(min_upload_speed_in_mb: float) -> bool:
    if not shutil.which("speedtest"):
        notifier.critical("Skipping backup: speedtest is not installed.", "Run 'sudo apt install speedtest-cli'.")
        return False

    try:
        upload_speed_in_bytes = float(
            run_command(["speedtest", "--no-download", "--secure", "--single", "--csv"]).split(",")[7]
        )
    except subprocess.CalledProcessError:
        notifier.error("Skipping backup: Speed test failed.")
        return False

    if (upload_speed_in_mb := upload_speed_in_bytes / 1024**2) < min_upload_speed_in_mb:
        notifier.network_error(
            f"Skipping backup: Upload speed is {upload_speed_in_mb:.2f} Mb. Required minimum is {min_upload_speed_in_mb} Mb."
        )
        return False

    return True


def main() -> None:
    log_file = settings.rsync_log_file
    if log_file.exists() and log_file.stat().st_mtime >= datetime.datetime.now().timestamp() - 86400:
        print("Backup has been executed today already. Skipping.")
        return

    if (server := first_available_server()) is None:
        notifier.network_error("Skipping backup: No backup server available")
        return

    try:
        server_on_private_network = IPv4Address(server).is_private
    except ValueError:
        server_on_private_network = False

    if not server_on_private_network:
        if is_internet_connection_metered():
            notifier.network_error("Skipping backup: On a metered connection")
            return

        if not fast_upload(settings.rsync_min_upload_speed_in_mb):
            return

    mirror_home()
    mirror_timeshift()
    log_file.write_text("")


def status() -> None:
    if settings.rsync_log_file.exists():
        if (log := settings.rsync_log_file.read_text()) != "":
            print(f"{log}{SEP}", end="")


if __name__ == "__main__":
    if sys.argv[-1] == "--status":
        status()
    else:
        main()
