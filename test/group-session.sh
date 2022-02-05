#!/usr/bin/env bash
#
# Test kernel state: the process group and session leader.
#
# Usage:
#   test/group-session.sh <function name>

setup() {
  mkdir -p _tmp
  ln -s -f -v $(which cat) _tmp/cat2
}

show_group_session() {
  # by default, it shows processes that use the same terminal
  #ps -o pid,ppid,pgid,sid,tname,comm | cat | _tmp/cat2

  # - bash is the parent of ps, cat, ca2
  # - the PGID is the same as bash?  Oh this is for a NON-INTERACTIVE SHELL.
  # - TPGID: controlling terminal's notion of foreground pgid?
  #   - it's always the same number, so it's misleading to associate with a process
  #   - see APUE section on setpgid(), tcsetgprp()

  if true; then
    echo '[foreground pipeline]'
    ps -o pid,ppid,pgid,sid,tpgid,comm | cat | _tmp/cat2
  fi

  # Test background pipeline
  if false; then
    # For interactive shells, the TPGID is different here.
    # Foreground: it matches the PGID of 'ps | cat | cat2'
    # Background: it matches the PGID of bash!

    echo '[background pipeline]'
    ps -o pid,ppid,pgid,sid,tpgid,comm | cat | _tmp/cat2 &
    wait
  fi

  # Test plain process
  if false; then
    echo '[single process]'
    ps -o pid,ppid,pgid,sid,comm
  fi
}

compare_shells() {
  for sh in dash bash mksh zsh bin/osh; do
  #for sh in dash bash; do
    echo -----
    echo $sh
    echo -----

    echo 'NON-INTERACTIVE'
    $sh $0 show_group_session
    echo

    echo INTERACTIVE
    $sh -i -c '. $0; show_group_session' $0
    echo
  done
}

if test $(basename $0) = 'group-session.sh'; then
  "$@"
fi
