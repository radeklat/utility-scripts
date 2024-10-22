from subprocess import run, PIPE
import re
import datetime


ICON = "🔁 "
DIVIDER = " | "


def units_to_number(unit: str) -> int:
    if unit.startswith("kB"):
        return 1024
    elif unit.startswith("MB"):
        return 1024**2
    elif unit.startswith("GB"):
        return 1024**3
    else:
        return 1


def timedelta_to_highest_unit(time_delta: datetime.timedelta) -> str:
    years, days = divmod(time_delta.days, 365)
    hours, remainder = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    for value, unit in [
        (years, "y"),
        (days, "d"),
        (hours, "h"),
        (minutes, "m"),
        (seconds, "s"),
        (time_delta.microseconds, "us"),
    ]:
        if value > 0:
            return f"{value}{unit}"
    return "0s"


def main():
    try:
        stdout_log = run(["abb-cli", "-s"], stdout=PIPE).stdout.decode()
    except FileNotFoundError:
        print(f"{ICON}Not installed{DIVIDER}")
        return
    except PermissionError:
        print(f"{ICON}abb-cli permission error{DIVIDER}")
        return

    match = re.search("Backing up.* - ([0-9.]+) ([kMG]B) / ([0-9.]+) ([kMG]B) \(([^ ]+) ([^)]+)\)", stdout_log)

    if match:
        done = float(match.group(1)) * units_to_number(match.group(2))
        total = float(match.group(3)) * units_to_number(match.group(4))
        progress = done / total * 100

        speed = float(match.group(5))
        speed_unit = match.group(6)
        speed_bytes_per_sec = speed * units_to_number(speed_unit)

        remaining = timedelta_to_highest_unit(
            datetime.timedelta(seconds=int((total - done) / speed_bytes_per_sec))
        )

        print(f"{ICON}{progress:.0f}%, {remaining}, {speed:.0f} {speed_unit}{DIVIDER}", end="")


if __name__ == "__main__":
    main()
