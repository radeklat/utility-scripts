import os
import subprocess
from pwd import getpwnam
from typing import Final


class Notifier:
    _DISPLAY: Final[str] = f"DISPLAY={os.environ.get('DISPLAY', ':0')}"
    _TIMEOUT: Final[int] = 5000

    def __init__(self):
        if not (user := self._find_logged_in_user()):
            raise RuntimeError("No logged-in user found to send the notification.")
        self._user = user
        self._bus_address: Final[str] = f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{getpwnam(user).pw_uid}/bus"

    @staticmethod
    def _find_logged_in_user() -> str | None:
        try:
            result = subprocess.run(["who"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "(:1)" in line:
                    return line.split()[0]
        except Exception as exc:
            raise RuntimeError(f"Error finding logged-in user: {exc}") from exc

        return None

    def send_notification(self, icon: str, urgency: str, message: str, body: str | None = None):
        args = ["sudo", "-u", self._user, self._DISPLAY, self._bus_address]
        args += ["notify-send", "-i", icon, "-u", urgency, "-t", str(self._TIMEOUT), message]
        if body is not None:
            args.append(body.replace("\n", " "))

        try:
            subprocess.run(args)
        except Exception as exc:
            raise RuntimeError(f"Error sending notification: {exc}") from exc

    def debug(self, message: str, body: str | None = None):
        self.send_notification("dialog-information", "low", message, body)

    def info(self, message: str, body: str | None = None):
        self.send_notification("dialog-information", "normal", message, body)

    def warning(self, message: str, body: str | None = None):
        self.send_notification("dialog-warning", "normal", message, body)

    def error(self, message: str, body: str | None = None):
        self.send_notification("dialog-error", "normal", message, body)

    def critical(self, message: str, body: str | None = None):
        self.send_notification("dialog-error", "critical", message, body)

    def network_error(self, message: str, body: str | None = None):
        self.send_notification("network-error", "normal", message, body)


if __name__ == "__main__":
    notifier = Notifier()
    notifier.info("Hello", "This is a test message.")
    notifier.debug("Debug", "This is a debug message.")
    notifier.warning("Warning", "This is a warning message.")
    notifier.error("Error", "This is an error message.")
    notifier.critical("Critical", "This is a critical message.")
    notifier.network_error("Network Error", "This is a network error message.")
