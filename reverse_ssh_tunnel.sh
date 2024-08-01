#!/bin/bash

# Opens a reverse SSH tunnel from Synology NAS to a VPS server that has a public IP address

## VPS configuration ##
#
### Enable binding to any interface ###
#
# sudo su
# vim /etc/ssh/sshd_config
#
# Add:
# GatewayPorts yes
#
# systemctl restart ssh
#
### Open port on firewall ###
#
# ufw status
# ufw allow $REMOTE_PORT
# ufw reload
#   
### Check incomming connection ###
#
# watch -n 1 -d netstat -tulnvp
#
### Test open port from a different host ###
#
# nmap -p $REMOTE_PORT $VPS_HOST

ROOT_FOLDER="$( cd "$( dirname "$0" )" && pwd )"
cd "${ROOT_FOLDER}" || exit

DELAY=60
VPS_HOST="$1"
VPS_USER="$2"
LOCAL_PORT=$3
REMOTE_PORT=$4

# Check if all arguments are provided
if [ -z "$VPS_HOST" ] || [ -z "$VPS_USER" ] || [ -z "$LOCAL_PORT" ] || [ -z "$REMOTE_PORT" ]; then
    echo "Usage: $0 <VPS_HOST> <VPS_USER> <LOCAL_PORT> <REMOTE_PORT>"
    exit 1
fi

# Make sure SSH key has correct permissions
# chmod 600 ~/.ssh/synology_ssh_tunnel

# Establish the SSH tunnel

# Add -o StrictHostKeyChecking=no on the first run
while true; do
    if [[ -f ./synology_ssh_tunnel_lock ]]; then
        echo "./synology_ssh_tunnel_lock exists, script tunnel will not open."
        exit 0
    fi

    echo "Starting a Reverse SSH tunnel 0.0.0.0@$VPS_HOST:$REMOTE_PORT -> localhost:$LOCAL_PORT"
    ssh -v -N -R 0.0.0.0:$REMOTE_PORT:localhost:$LOCAL_PORT -i ~/.ssh/synology_ssh_tunnel $VPS_USER@$VPS_HOST

    if [ $? -eq 1 ]; then
        echo "SSH tunnel closed by remote host. Will not restart."
        exit 1
    fi
    
    echo "SSH tunnel terminated. Restarting in $DELAY seconds."
    sleep $DELAY
done
