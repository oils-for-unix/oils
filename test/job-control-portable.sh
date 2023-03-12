#!/usr/bin/env bash
#
# test/job-control-portable.sh: helper for job-control.sh.
#
# This is a portable shell script, since it has to run under dash, mksh, etc.
#
# Usage:
#   test/job-control-portable.sh <function name>

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

  local sh=$1
  local kind=$2

  # We have many case statements here to allow choosing many tests as a "mask",
  # e.g. show_group_session fgproc+bgproc

  case $kind in (*fgproc*)
    echo '[foreground process]'
    ps -o pid,ppid,pgid,sid,tpgid,comm
    ;;
  esac

  case $kind in (*bgproc*)
    echo '[background process]'
    ps -o pid,ppid,pgid,sid,tpgid,comm &
    wait

    # - Gets its own PGID
    # - Hm UNLIKE bgpipe it also gets its own TPGID?  Seems consistent in all
    #   shells.  Why is that?
    ;;
  esac

  case $kind in (*fgpipe*)
    echo '[foreground pipeline]'
    ps -o pid,ppid,pgid,sid,tpgid,comm | cat | _tmp/cat2
    ;;
  esac

  case $kind in (*bgpipe*)
    # For interactive shells, the TPGID is different here.
    # Foreground: it matches the PGID of 'ps | cat | cat2'
    # Background: it matches the PGID of bash!

    echo '[background pipeline]'
    ps -o pid,ppid,pgid,sid,tpgid,comm | cat | _tmp/cat2 &
    wait
    ;;
  esac

  case $kind in (*subshell*)
    # does NOT create a new process group.  So what happens when it's
    # interrupted?

    echo '[subshell]'
    ( ps -o pid,ppid,pgid,sid,tpgid,comm; echo ALIVE )
    # subshell gets its own PGID in every shell!
    ;;
  esac

  case $kind in (*csub*)
    # does NOT create a new process group.  So what happens when it's
    # interrupted?
    echo '[command sub]'
    local x
    x=$(ps -o pid,ppid,pgid,sid,tpgid,comm)
    echo "$x"
    ;;
  esac

  case $kind in (*psub*)
    case $sh in (dash|mksh)
      return
    esac

    echo '[process sub]'
    # use 'eval' as workaround for syntax error in dash and mksh
    eval 'cat <(ps -o pid,ppid,pgid,sid,tpgid,comm)'
    # RESULTS
    # zsh: ps and cat are in their own process groups distinct from the shell!
    # bash: cat is in its own process group, but ps is in one with bash.  Hm
    ;;
  esac
}

run_with_shell() {
  local sh=$1
  shift

  echo "sh = $sh"

  $sh $0 show_group_session $sh "$@" > _tmp/group-session-output

  test/assert_process_table.py $$ $sh $1 < _tmp/group-session-output
  local status=$?

  cat _tmp/group-session-output
  echo

  return $status
}

run_with_shell_interactive() {
  local sh=$1
  shift

  echo "sh = $sh"

  local more_flags=''
  case $sh in
    (bash|bin/osh)
      more_flags='--rcfile /dev/null'
      ;;
  esac

  $sh $more_flags -i -c '. $0; show_group_session "$@"' $0 $sh "$@" > _tmp/group-session-output

  test/assert_process_table.py -i $$ $sh $1 < _tmp/group-session-output
  local status=$?

  cat _tmp/group-session-output
  echo

  return $status
}

# We might be sourced by run_with_shell_interactive, so avoid running anything
# in that case.
case $1 in
  setup|show_group_session|run_with_shell|run_with_shell_interactive)
    "$@"
esac
