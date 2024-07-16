import subprocess

COMMAND = "nmcli -t -m multiline -f GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,GENERAL.METERED dev show".split()
PING_CMD = "ping -I {interface} -q -c 1 -w 3 1.1.1.1"


def ping_interface(interface: str) -> bool:
    try:
        subprocess.run(PING_CMD.format(interface=interface).split(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def is_internet_connection_metered(interface_types: list[str] = ("wifi", "ethernet")) -> bool | None:
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
