#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}" || exit

LOG_FILE="/tmp/rsync_timeshift.log"

source .env
source shared.sh

mirror_timeshift() {
  stdbuf -i0 -o0 -e0 rsync \
      -e "ssh -l ${RSYNC_SSH_USER} -p ${RSYNC_PORT}" \
      --info=name0,del0,progress2 \
      --progress \
      --inplace \
      --links \
      --hard-links \
      --archive \
      --human-readable \
      --verbose \
      --no-inc-recursive \
      --delete \
      --delete-excluded \
      --prune-empty-dirs \
      /timeshift ${RSYNC_SERVER}::${RSYNC_TARGET_FOLDER} | \
          stdbuf -i0 -o0 -e0 tr '\r' '\n' | \
              stdbuf -i0 -o0 -e0 sed 's/  */ /g;s/ to consider//;s/^ //;s/ (.*//;s/\.\.\.//;s/\(.*\)/⏳️ \1/' >${LOG_FILE}
}

mirror_home() {
  stdbuf -i0 -o0 -e0 rsync \
      -e "ssh -l ${RSYNC_SSH_USER} -p ${RSYNC_PORT}" \
      --info=name0,del0,progress2 \
      --progress \
      --inplace \
      --links \
      --hard-links \
      --archive \
      --human-readable \
      --verbose \
      --no-inc-recursive \
      --delete \
      --delete-excluded \
      --prune-empty-dirs \
      --exclude SynologyDrive \
      --exclude .SynologyDrive \
      --exclude='*/.git' \
      --exclude='*/.venv' \
      --exclude='*/__pycache__' \
      --exclude='*/.mypy_cache' \
      --exclude='*/.pytest_cache' \
      --exclude='*/.ruff_cache' \
      --exclude .cache/pypoetry \
      --exclude .cache/pre-commit \
      --exclude .cache/google-chrome \
      --exclude .config/Signal \
      --exclude .config/Franz \
      --exclude .config/google-chrome \
      --exclude .local/share/JetBrains/Toolbox \
      --exclude .local/share/Trash \
      --exclude .local/share/virtualenv \
      --exclude .local/lib \
      --exclude .pyenv \
      --exclude .npm \
      --exclude .nvm \
      /home/rlat ${RSYNC_SERVER}::${RSYNC_TARGET_FOLDER} | \
          stdbuf -i0 -o0 -e0 tr '\r' '\n' | \
              stdbuf -i0 -o0 -e0 sed 's/  */ /g;s/ to consider//;s/^ //;s/ (.*//;s/\.\.\.//;s/\(.*\)/🏡 \1/' >${LOG_FILE}
}

metered_connection() {
    nmcli -f connection.metered connection show "$(nmcli -t -f GENERAL.CONNECTION --mode tabular device show $DEVICE | head -n1)" | grep -q "yes"
    return $?
}

server_available() {
    if ! which nping >/dev/null 2>&1; then
      notify_critical "Skipping backup" "nmap is not installed. Run 'sudo apt install nmap'."
      return 1
    fi

    nping --tcp-connect -c 1 -p ${RSYNC_PORT} -q "${RSYNC_SERVER}" | grep -q "Successful connections: 1"
    return $?
}

fast_upload() {
  local min_upload_speed_in_mb=5

  if ! which speedtest >/dev/null 2>&1; then
      notify_critical "Skipping backup" "speedtest is not installed. Run 'sudo apt install speedtest-cli'."
      return 1
    fi

    local upload_speed_in_bytes="$(speedtest --no-download --single --csv | cut -d ',' -f 8)"
    if [[ $? -ne 0 ]]; then
      notify_error "Skipping backup" "Speed test failed."
      return 1
    fi

    local upload_speed_in_mb=$(echo "${upload_speed_in_bytes} / 1024^2" | bc)
    if [[ ${upload_speed_in_mb} -lt ${min_upload_speed_in_mb} ]]; then
      upload_speed_in_mb=$(echo "scale=2; ${upload_speed_in_bytes} / 1024^2" | bc)
      notify_network_error "Skipping backup" "Upload speed is ${upload_speed_in_mb} Mb. Required minimum is ${min_upload_speed_in_mb} Mb."
      return 1
    fi

    return 0
}

# has the log file been modified today already?
if [[ -e $LOG_FILE && $(stat -c "%y" $LOG_FILE | cut -f 1 -d " ") == $(date +%Y-%m-%d) ]]; then
    echo "Backup has been executed today already. Skipping."
elif ! server_available; then
    notify_network_error "Skipping backup" "Backup server is not available"
elif metered_connection; then
    notify_network_error "Skipping backup" "On a metered connection"
elif ! fast_upload; then
    exit 1
else
    notify_info "Backup started" "/home/rlat"
    mirror_home
    notify_info "Backup started" "/timeshift"
    mirror_timeshift
    truncate -s 0 ${LOG_FILE}
fi