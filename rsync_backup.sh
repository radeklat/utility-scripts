#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}" || exit

LOG_FILE="/tmp/rsync_timeshift.log"

source .env

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
      --exclude /home/rlat/SynologyDrive/*** \
      --exclude /home/rlat/.pyenv/*** \
      --exclude /home/rlat/.SynologyDrive/*** \
      --exclude /home/rlat/***/.git \
      --exclude /home/rlat/.cache/pypoetry \
      --exclude /home/rlat/.cache/pre-commit \
      --exclude /home/rlat/.cache/google-chrome \
      --exclude /home/rlat/.config/Signal \
      --exclude /home/rlat/.config/Franz \
      --exclude /home/rlat/.config/google-chrome \
      --exclude /home/rlat/.local/share/JetBrains/Toolbox \
      --exclude /home/rlat/.local/share/Trash \
      --exclude /home/rlat/.local/share/virtualenv \
      --exclude /home/rlat/.local/lib \
      --exclude /home/rlat/.pyenv \
      --exclude /home/rlat/.npm \
      --exclude /home/rlat/.nvm \
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
elif metered_connection; then
  echo "On a metered connection. Skipping."
else
  echo "Backing up /timeshift"
  mirror_timeshift
  truncate -s 0 ${LOG_FILE}
  echo "Backing up /home/rlat"
  mirror_home
  truncate -s 0 ${LOG_FILE}
fi
