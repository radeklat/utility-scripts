#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}" || exit

source shared.sh

TURBO_BOOST_PATH="/sys/devices/system/cpu/intel_pstate/no_turbo"

turbo_boost_on() {
    [ $(cat ${TURBO_BOOST_PATH}) -eq 0 ]
    return $?
}

if turbo_boost_on; then
    pkexec bash -c "echo '1' > ${TURBO_BOOST_PATH}"
    notify_info "Turbo Boost Off 🍃"
else
    pkexec bash -c "echo '0' > ${TURBO_BOOST_PATH}"
    notify_info "Turbo Boost On 🔥"
fi
