#!/usr/bin/env bash

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}"

SOURCE_FOLDER="/timeshift"
LOG_FILE="/tmp/rsync_timeshift.log"

source .env

rsync \
    -e "ssh -l ${SSH_USER} -p ${RSYNC_PORT}" \
    --info=name0,del0,progress2 --progress -ahv --no-i-r --delete --prune-empty-dirs \
    ${SOURCE_FOLDER} ${RSYNC_SERVER}::${TARGET_FOLDER} | \
        stdbuf -i0 -o0 -e0 tr '\r' '\n' | \
            sed 's/  */ /g;s/^ //;s/ (.*//;s/\.\.\.//;s/\(.*\)/🔁 \1/' >${LOG_FILE}
            
rm -f ${LOG_FILE}

