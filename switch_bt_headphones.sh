#!/usr/bin/env bash

HEADPHONES_MAC="04:5D:4B:97:5D:34"

# Run:
#   bluetoothctl devices
# DD:CA:2A:12:9C:92 MX Master 3
# 6C:93:08:61:89:FB Keychron K3 Pro
KEEP_BLUETOOTH_ON_FOR=("DD:CA:2A:12:9C:92" "6C:93:08:61:89:FB")

connected() {
    bluetoothctl info ${HEADPHONES_MAC} | grep -q "Connected: yes"
    return $?
}

can_turn_bluetooth_off() {
  for mac in ${KEEP_BLUETOOTH_ON_FOR[@]}; do
    if bluetoothctl info ${mac} | grep -q "Connected: yes"; then
      return 1
    fi
  done

  return 0
}

# $1: message
notify () {
    notify-send -t 5000 "$1"
}

if connected; then
    notify "Disconnecting 🎧"
    bluetoothctl disconnect ${HEADPHONES_MAC}
    if can_turn_bluetooth_off; then
        echo "Turning off bluetooth"
        notify "Bluetooth OFF"
        rfkill block bluetooth
    fi
else
    if rfkill list bluetooth | grep -q "Soft blocked: yes"; then
      echo "Turning on bluetooth"
      notify "Bluetooth ON"
      rfkill unblock bluetooth
    fi
    echo -n "Trying to connect "
    for i in $(seq 1 30); do
        bluetoothctl connect ${HEADPHONES_MAC} | grep -q "\[[^]]*NEW[^]]*\] Transport"
        if [[ $? -eq 0 && connected ]]; then
            echo " connected."
            notify "🎧 connected"
            exit 0
        fi
        echo -n "."
        sleep 1
        if [[ i -eq 1 ]]; then
            notify "Connecting 🎧"
        fi
    done
    echo " not connected."
    notify "🎧 not connected"
fi
