#!/bin/bash

docker-compose exec dovecot-mailcow doveadm quota recalc -A
