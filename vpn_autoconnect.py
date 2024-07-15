import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Never

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ON_SSIDS: set[str]
    PROFILE_NAME: str
    RECHECK_INTERVAL_SEC: int = 60
    LOG_LEVEL: str = "INFO"

    class Config:
        env_prefix = "VPN_AUTOCONNECT_"
        env_file = Path(__file__).parent / ".env"
        env_file_encoding = "utf-8"

    @property
    def logging_log_level(self) -> int:
        return logging.getLevelNamesMapping()[self.LOG_LEVEL.upper()]


LOG = logging.getLogger(__name__)


def get_active_autoconnect_wifi_ssid(ssids: set[str]) -> str | None:
    @dataclass
    class Connection:
        active: str
        ssid: str

    try:
        # Get the list of active connections
        result = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Check if any of the specified SSIDs are active
        for line in result.stdout.strip().split("\n"):
            connection = Connection(*line.split(":", maxsplit=2))

            if connection.active == "yes" and connection.ssid in ssids:
                return connection.ssid
    except Exception as e:
        LOG.error(f"Error checking WiFi connections: {e}")

    return None


def is_vpn_profile_active(vpn_name):
    @dataclass
    class Connection:
        type: str
        state: str
        name: str

    try:
        # Get the list of active VPN connections
        result = subprocess.run(
            ["nmcli", "-t", "-f", "TYPE,STATE,NAME", "connection", "show", "--active"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Check if the specified VPN is active
        for line in result.stdout.strip().split("\n"):
            connection = Connection(*line.split(":", maxsplit=3))

            if connection.name == vpn_name and connection.type == "vpn" and connection.state == "activated":
                return True

    except Exception as e:
        LOG.error(f"Error checking VPN connection: {e}")

    return False


def activate_vpn_connection(vpn_name):
    try:
        subprocess.run(
            ["nmcli", "connection", "up", vpn_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        LOG.info(f"VPN connection '{vpn_name}' activated successfully.")
    except Exception as e:
        LOG.error(f"Error activating VPN connection: {e}")


def main(settings: Settings) -> None:
    if is_vpn_profile_active(settings.PROFILE_NAME):
        LOG.debug(f"'{settings.PROFILE_NAME}' VPN connection is already active.")
        return

    if (ssid := get_active_autoconnect_wifi_ssid(settings.ON_SSIDS)) is None:
        LOG.info("None of the specified WiFi connections to be used for VPN auto-connect are active.")
        return

    if not ((now := datetime.now()).weekday() < 5 and 8 <= now.hour < 19):
        LOG.info("Outside of work hours. Skipping VPN activation.")
        return

    LOG.info(
        f"WiFi connection '{ssid}' is active and set to be used for VPN auto-connect and "
        f"'{settings.PROFILE_NAME}' VPN connection is not active. Activating VPN..."
    )
    activate_vpn_connection(settings.PROFILE_NAME)


def main_loop() -> Never:
    settings = Settings()

    logging.basicConfig(
        level=settings.logging_log_level,
        format="[%(levelname)s] %(message)s",
    )

    while True:
        main(settings)

        if sys.argv[-1] != "--loop":
            break

        sleep(settings.RECHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main_loop()
