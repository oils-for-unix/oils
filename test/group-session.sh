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

  local kind=$1

  case $kind in
    *fgpipe*)
      echo '[foreground pipeline]'
      ps -o pid,ppid,pgid,sid,tpgid,comm | cat | _tmp/cat2
      ;;

    *bgpipe*)
      # For interactive shells, the TPGID is different here.
      # Foreground: it matches the PGID of 'ps | cat | cat2'
      # Background: it matches the PGID of bash!

      echo '[background pipeline]'
      ps -o pid,ppid,pgid,sid,tpgid,comm | cat | _tmp/cat2 &
      wait
      ;;

    *fgproc*)
      echo '[single process]'
      ps -o pid,ppid,pgid,sid,comm
      ;;

    *csub*)
      # does NOT create a new process group.  So what happens when it's
      # interrupted?
      echo '[command sub]'
      local x
      x=$(ps -o pid,ppid,pgid,sid,comm)
      echo "$x"
      ;;

    *psub*)
      echo '[process sub]'
      # use 'eval' as workaround for syntax error in dash and mksh
      eval 'cat <(ps -o pid,ppid,pgid,sid,comm)'
      # RESULTS
      # zsh: ps and cat are in their own process groups distinct from the shell!
      # bash: cat is in its own process group, but ps is in one with bash.  Hm
      ;;

  esac
}

compare_shells() {
  ### Pass tasks, any of fgproc-fgpipe-bgpipe

  #for sh in dash bash mksh zsh bin/osh; do
  for sh in dash bash bin/osh; do

  # for psub
  #for sh in bash zsh bin/osh; do
    echo -----
    echo $sh
    echo -----

    echo 'NON-INTERACTIVE'
    $sh $0 show_group_session "$@"
    echo

    local more_flags=''
    case $sh in
      (bash|bin/osh)
        more_flags='--rcfile /dev/null'
        ;;
    esac

    echo INTERACTIVE
    $sh $more_flags -i -c '. $0; show_group_session "$@"' $0 "$@"
    echo
  done
}

# We might be sourced by INTERACTIVE, so avoid running anything in that case.
case $1 in
  setup|show_group_session|compare_shells)
    "$@"
    ;;
esac
