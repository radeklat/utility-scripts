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

consumption() {
    local current="$(cat ${BAT_PATH}/current_now 2>/dev/null || echo '0')"
    local voltage="$(cat ${BAT_PATH}/voltage_now)"
    echo "scale=0; ${current} * ${voltage} / 10^12" | bc
}

battery_status() {
    cat ${BAT_PATH}/status
}

turbo_boost_status() {
    [[ $(cat /sys/devices/system/cpu/intel_pstate/no_turbo) -eq 0 ]] && echo "🔥"
}

if [[ -f /tmp/rsync_timeshift.log ]]; then
  line="$(tail -n 1 /tmp/rsync_timeshift.log)"
  if [[ "$line" =~ ".* files" ]]; then
    line="$(echo ${line} | sed 's/ files//')"
  else
    line="$(echo ${line} | cut -d " " -f 1-4)"
  fi
  echo -n "${line}${SEP}"
fi

python parse_backup_progress.py 2>&1
echo -n "$(temperature)°C"
turbo_boost_status
consumption_value=$(consumption)

if [[ "$(battery_status)" == "Charging" ]]; then
    time_to_full="$(time_to_full_charge)"
    [[ -n ${time_to_full} ]] && echo "${SEP}⚡${time_to_full}"
elif [[ "${consumption_value}" != "0" ]]; then
    printf "${SEP}%dW" "${consumption_value}"
fi

echo "${SEP}"
