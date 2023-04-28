#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}"

LOG_FILE="/tmp/rsync_timeshift.log"

source .env

mirror_files() {
  stdbuf -i0 -o0 -e0 rsync \
      -e "ssh -l ${SSH_USER} -p ${RSYNC_PORT}" \
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
      /timeshift ${RSYNC_SERVER}::${TARGET_FOLDER} | \
          stdbuf -i0 -o0 -e0 tr '\r' '\n' | \
              stdbuf -i0 -o0 -e0 sed 's/  */ /g;s/ to consider//;s/^ //;s/ (.*//;s/\.\.\.//' >${LOG_FILE}
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
  mirror_files
  truncate -s 0 ${LOG_FILE}
fi
