#!/usr/bin/env python

import subprocess


def is_metered(interface):
    try:
        status = subprocess.run(
            ["nmcli", "-t", "-m", "tabular", "-f", "GENERAL.METERED", "dev", "show", interface],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip().split(" ")[0]
    except subprocess.CalledProcessError as exc:
        if f"Device '{interface}' not found" in exc.stderr:
            return None
        raise

    if status == "no":
        return False
    if status == "yes":
        return True

    return None


statuses = {is_metered(_) for _ in ["enx32531cd5255a", "wlp0s20f3"]}

if statuses == {None}:
    print("📵")
elif False in statuses:
    print("")
else:
    print("📱")
