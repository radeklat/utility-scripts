import subprocess
from collections import Counter

COMMAND = "nmcli -t -m multiline -f GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,GENERAL.METERED dev show".split()
PING_TARGETS = Counter(["1.1.1.1", "8.8.8.8"])
PING_CMD = "ping -I {interface} -q -c 1 -w 3 {target}"


def ping_interface(interface: str) -> bool:
    for target, _count in PING_TARGETS.most_common():
        try:
            command = PING_CMD.format(interface=interface, target=target).split()
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            PING_TARGETS[target] += 1
            return True
        except subprocess.CalledProcessError:
            pass

    return False


def is_internet_connection_metered(interface_types: list[str] = ("wifi", "ethernet", "wireguard", "tun")) -> bool | None:
    stdout = subprocess.run(COMMAND, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout

    devices = []
    for device in stdout.strip().split("\n\n"):
        device_info = {}
        for line in device.split("\n"):
            key, value = line.split(":", 1)
            device_info[key] = value.strip()
        devices.append(device_info)

    metered = None
    for device in devices:
        if device["GENERAL.TYPE"] in interface_types:
            if "connected" in device["GENERAL.STATE"] and ping_interface(device["GENERAL.DEVICE"]):
                metered = False

                if device["GENERAL.METERED"] == "yes":
                    return True

    return metered
