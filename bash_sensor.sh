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

turbo_boost_status() {
    [[ $(cat /sys/devices/system/cpu/intel_pstate/no_turbo) -eq 0 ]] && echo -n "🔥"
}

if [[ -f /tmp/rsync_timeshift.log && $(stat -c "%b" /tmp/rsync_timeshift.log) -gt 0 ]]; then
  line="$(tail -n 1 /tmp/rsync_timeshift.log)"
  if [[ "$line" =~ .*\ files ]]; then
    line="$(echo ${line} | cut -d ' ' -f 2)"
    divider=1
    scale=""
    if [[ $line -ge 1000000 ]]; then
      divider=1000000
      scale="M"
    elif [[ $line -ge 1000 ]]; then
      divider=1000
      scale="k"
    fi
    line=$(echo "scale=1; ${line} / ${divider}" | bc -l)${scale}
  else
    line="$(echo ${line} | cut -d " " -f 1-3)"
  fi
  echo -n "🔁 ${line}${SEP}"
fi

#python parse_backup_progress.py 2>&1
#echo -n "$(temperature)°C"
# turbo_boost_status
python toggl_time_tracked.py
consumption_value=$(consumption)

if [[ "$(battery_status)" == "Charging" ]]; then
    time_to_full="$(time_to_full_charge)"
    [[ -n ${time_to_full} ]] && echo "⚡${time_to_full} / $(charging_wattage)W${SEP}"
elif [[ "${consumption_value}" != "0" ]]; then
    printf "%02dW${SEP}" "${consumption_value}"
fi
