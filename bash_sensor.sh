#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}"

BATTERY="BAT0"
BAT_PATH="/sys/class/power_supply/${BATTERY}"
SEP="  |  "

temperature() {
    sensors | grep -oP 'Package.*?\+\K[0-9]+'
}

time_to_full_charge() {
    upower -i /org/freedesktop/UPower/devices/battery_${BATTERY} | \
    grep "time to full" | \
    sed 's/time to full://;s/ *//g;s/hours/h/;s/minutes/m/;s/.[0-9]m/m/'
}

charging_wattage() {
  upower -i /org/freedesktop/UPower/devices/battery_${BATTERY} | \
  grep 'energy-rate' | \
  sed 's/.*: *\([0-9]*\)\.[0-9]* W/\1/'
}

consumption() {
    local current="$(cat ${BAT_PATH}/current_now 2>/dev/null || echo '0')"
    local voltage="$(cat ${BAT_PATH}/voltage_now)"
    echo "scale=0; ${current} * ${voltage} / 10^12" | bc
}

battery_status() {
    cat ${BAT_PATH}/status
}

#python parse_backup_progress.py 2>&1
#echo -n "$(temperature)°C"
python toggl_time_tracked.py
consumption_value=$(consumption)

if [[ "$(battery_status)" == "Charging" ]]; then
    time_to_full="$(time_to_full_charge)"
    [[ -n ${time_to_full} ]] && echo "⚡${time_to_full} / $(charging_wattage)W${SEP}"
elif [[ "${consumption_value}" != "0" ]]; then
    printf "%02dW${SEP}" "${consumption_value}"
fi
