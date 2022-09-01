#!/usr/bin/env bash

containers=$(docker container ps -a -f 'name=pytest' --format '{{.ID}}')
networks=$(docker network ls -f 'name=pytest' --format '{{.ID}}')

[[ -n "$containers" ]] && docker rm --force --volumes $containers
[[ -n "$networks" ]] && docker network rm $networks 
