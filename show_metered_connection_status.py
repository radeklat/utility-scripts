#!/usr/bin/env python

import subprocess


def is_not_metered(interface):
    return subprocess.run(
        ["nmcli", "-t", "-m", "tabular", "-f", "GENERAL.METERED", "dev", "show", interface],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip() == "no"


print("🌍️" if any(is_not_metered(_) for _ in ["enx32531cd5255a", "wlp0s20f3"]) else "📱")
