#!/usr/bin/env bash

HEADPHONES_MAC="04:5D:4B:97:5D:34"

# ED:10:02:9F:7F:92 = MX Master mouse
KEEP_BLUETOOTH_ON_FOR="ED:10:02:9F:7F:92"

connected() {
    bluetoothctl info ${HEADPHONES_MAC} | grep -q "Connected: yes"
    return $?
}

can_turn_bluetooth_off() {
  for mac in ${KEEP_BLUETOOTH_ON_FOR}; do
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
        bluetoothctl connect ${HEADPHONES_MAC}
        if connected; then
            echo " connected."
            notify "🎧 connected"
            exit 0
        fi
        echo -n "."
        if [[ i -eq 1 ]]; then
            notify "Connecting 🎧"
        fi
    done
    echo " not connected."
    notify "🎧 not connected"
fi
