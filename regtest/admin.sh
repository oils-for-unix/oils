#!/usr/bin/env bash
#
# Server admin
#
# Usage:
#   regtest/admin.sh <function name>

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

_make-user() {
  local name=${1:-gabe}

  # will prompt
  if ! adduser $name; then
    # User already exists
    return
  fi

  usermod -aG sudo $name

  local dir=/home/$name/.ssh
  mkdir -v $dir
  chmod -v 700 $dir

  # ask for public key
  echo 'TODO' > $dir/authorized_keys
  chmod -v 600 $dir/authorized_keys
}

make-users() {
  for name in gabe aidan daveads andriy; do
    sudo $0 _make-user $name
  done
}

check() {
  grep sudo /etc/group 

  ls -l /home/
}

# users can check with:
#
# ssh NAME@he.oils.pub
# sudo ls /

task-five "$@"
