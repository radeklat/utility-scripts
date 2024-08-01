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

for script in "k9s-update"; do
  if [[ ! -f /home/rlat/bin/${script} ]]; then
    ln -s ${ROOT_FOLDER}/${script}.py /home/rlat/bin/${script}
  else
    echo "'${script}' is already installed."
  fi
done

# VPN AUTOCONNECT

sudo cp etc/systemd/system/vpn_autoconnect.service  /etc/systemd/system/vpn_autoconnect.service
sudo systemctl daemon-reload  # if it already exists
sudo systemctl enable vpn_autoconnect.service
sudo systemctl stop vpn_autoconnect.service
sudo systemctl start vpn_autoconnect.service

sudo cp etc/polkit-1/rules.d/50-org.freedesktop.NetworkManager.rules /etc/polkit-1/rules.d/
sudo systemctl restart polkit