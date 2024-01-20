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

# has the log file been modified today already?
if [[ -e $LOG_FILE && $(stat -c "%y" $LOG_FILE | cut -f 1 -d " ") == $(date +%Y-%m-%d) ]]; then
    echo "Backup has been executed today already. Skipping."
elif ! server_available; then
    notify_network_error "Skipping backup" "Backup server is not available"
elif metered_connection; then
    notify_network_error "Skipping backup" "On a metered connection"
else
    notify_info "Backup started" "/home/rlat"
    mirror_home
    notify_info "Backup started" "/timeshift"
    mirror_timeshift
    truncate -s 0 ${LOG_FILE}
fi
