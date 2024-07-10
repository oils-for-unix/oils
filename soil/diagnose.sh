#!/usr/bin/env bash
#
# Usage:
#   soil/diagnose.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/task-five.sh
source soil/common.sh  # dump-env

dump-timezone() {

  # On Travis:
  #  /usr/share/zoneinfo/UTC
  # On my machine
  #  /usr/share/zoneinfo/America/Los_Angeles

  if command -v file; then
    file '/etc/localtime'
  fi
  echo
  read md5 _ <<< $(md5sum /etc/localtime)
  log "md5 = $md5"
  find /usr/share/zoneinfo -type f | xargs md5sum | grep $md5
  echo
}

dump-versions() {
  set +o errexit

  source build/dev-shell.sh  # python3 may be here

  set -x
  which python2
  python2 -V

  which python3
  python3 -V
  set +x
}

dump-locale() {
  set -x
  # show our locale
  locale

  # show all locales
  locale -a
  set +x
}

dump-hardware() {
  egrep '^(processor|model name)' /proc/cpuinfo
  echo

  egrep '^Mem' /proc/meminfo
  echo

  df -h
  echo
}

dump-distro() {
  local path=/etc/os-release
  if test -f $path; then
    cat $path
  else
    echo "$path doesn't exist"
  fi
  echo

  if command -v apt-cache > /dev/null; then
    apt-cache policy r-base-core
  fi
}

dump-user-host() {
  echo -n 'whoami = '
  whoami
  echo

  echo "PWD = $PWD"
  echo

  if command -v hostname > /dev/null; then
    echo -n 'hostname = '
    hostname
  else
    # Fedora
    echo 'hostname command missing'
  fi
  echo

  uname -a
  echo

  who
  echo
}

dump-tty() {
  echo TTY
  tty || true
}

os-info() {
  dump-user-host
  echo

  dump-tty
  echo

  dump-distro
  echo

  dump-versions
  echo

  dump-locale
  echo

  dump-timezone
  echo

  dump-hardware
  echo

  # Process limits
  echo 'Soft limits:'
  ulimit -S -a
  echo
  echo 'Hard limits:'
  ulimit -H -a
  echo
}

task-five "$@"

