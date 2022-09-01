#!/usr/bin/env bash

TURBO_BOOST_PATH="/sys/devices/system/cpu/intel_pstate/no_turbo"

turbo_boost_on() {
    [ $(cat ${TURBO_BOOST_PATH}) -eq 0 ]
    return $?
}

# $1: message
notify () {
    notify-send -t 5000 "$1"
}

if turbo_boost_on; then
    pkexec bash -c "echo '1' > ${TURBO_BOOST_PATH}"
    notify "Turbo Boost Off 🍃"
else
    pkexec bash -c "echo '0' > ${TURBO_BOOST_PATH}"
    notify "Turbo Boost On 🔥"
fi
