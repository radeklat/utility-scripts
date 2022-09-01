#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}"

for script in "docker-pytest-cleanup" "switch_bt_headphones" "pause" "toggle_turbo_boost"; do
  if [[ ! -f /home/rlat/bin/${script} ]]; then
    ln -s ${ROOT_FOLDER}/${script}.sh /home/rlat/bin/${script}
  else
    echo "'${script}' is already installed."
  fi
done

