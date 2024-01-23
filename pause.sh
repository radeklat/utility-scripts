#!/bin/bash

DELAY_SEC=$((55*60))
SHORT_BREAK_SEC=$((5*60))
LONG_BREAK_SEC=$((15*60))
SHORT_BREAK_CNT=3

yad --version >/dev/null 2>&1

if [[ $? -ne 252 ]]; then
    echo -e "yad is not installed. Run:\n\nsudo apt install -y yad"
    exit 1
fi

# run if user hits control-c
control_c() {
  echo "SIGINT received, interrupting current task."
  exit 1
}

# trap keyboard interrupt (control-c)
trap control_c SIGINT

# Fix: yad: cannot create shared memory for key -1: File exists
ipcrm -M -1

if [[ $# -gt 0 ]]; then
    pauseat=$(($(date +%s) + 1$))
else
    pauseat=$(($(date +%s) + DELAY_SEC))
fi

clear
break_cnt=0
next_break="short"

while true
do
    remtime=$((pauseat - $(date +%s))) # remaining time
    
    if [[ $remtime -gt 0 ]]; then
        # still some time left
        [[ $remtime -ge 3600 ]] && dtfmt="%H:%M:%S" || dtfmt="%M:%S"
        echo -ne "\r$(date +"$dtfmt" -u --date="@$remtime") until the next $next_break break."
        sleep 1
    elif [[ $((remtime * -1)) -gt $((DELAY_SEC * 2)) ]]; then
        # computer woke up from sleep/hibernation, start over
        echo "Sleep/hibernation detected. Starting over..."
        pauseat=$(($(date +%s) + DELAY_SEC))
    else
      # time to take a brake
      break_cnt=$((break_cnt + 1))
      next_break="short"

      if [[ $break_cnt -ge $SHORT_BREAK_CNT ]]; then
        break_len=$LONG_BREAK_SEC
        break_cnt=0
        name="long"
      else
        [[ $break_cnt -eq $((SHORT_BREAK_CNT - 1)) ]] && next_break="long"
        break_len=$SHORT_BREAK_SEC
        name="short"
      fi

      pauseend=$((break_len + $(date +%s)))
      title="Take a $name $(($break_len / 60)) minutes break"

      while [[ $pauseend -gt $(date +%s) ]]; do
        rempause=$((pauseend - $(date +%s)))
        yad \
          --notebook \
          --text-align=center \
          --text="\n\n\n<span font='50'>$title</span>\n\n\n<span font='30'>Change your table height and stretch.</span>" \
          --sticky \
          --center \
          --on-top \
          --skip-taskbar \
          --fulscreen \
          --timeout=$rempause \
          --timeout-indicator=top \
          --no-buttons \
          --borders=50 \
          --mouse \
          --maximized \
          --undecorated \
          --no-escape
      done

      yad \
        --notebook \
        --text-align=center \
        --title "$title" \
        --text="<span font='20'>Did you change your table height and stretched?</span>" \
        --sticky \
        --center \
        --on-top \
        --button="          YES          ":1 \
        --buttons-layout=center \
        --borders=50 \
        --mouse

      pauseat=$(($(date +%s) + DELAY_SEC))
      clear
    fi
done
