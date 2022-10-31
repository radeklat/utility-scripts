#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}"

LOG_FILE="/tmp/rsync_timeshift.log"

source .env

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
            stdbuf -i0 -o0 -e0 sed 's/  */ /g;s/ to consider//;s/^ //;s/ (.*//;s/\.\.\.//;s/\(.*\)/🔁 \1/' >${LOG_FILE}
            
rm -f ${LOG_FILE}

