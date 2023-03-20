#!/usr/bin/env bash
#
# test/process-table-portable.sh: helper for process-table.sh.
#
# This is a portable shell script, since it has to run under dash, mksh, etc.
#
# Usage:
#   test/process-table-portable.sh <function name>

setup() {
  mkdir -p _tmp
  ln -s -f -v $(which cat) _tmp/cat2
}

readonly PS_COLS='pid,ppid,pgid,sid,tpgid,comm'

show_process_table() {
  # by default, it shows processes that use the same terminal
  #ps -o pid,ppid,pgid,sid,tname,comm | cat | _tmp/cat2

  # - bash is the parent of ps, cat, ca2
  # - the PGID is the same as bash?  Oh this is for a NON-INTERACTIVE SHELL.
  # - TPGID: controlling terminal's notion of foreground pgid?
  #   - it's always the same number, so it's misleading to associate with a process
  #   - see APUE section on setpgid(), tcsetgprp()

  local sh=$1
  local snippet=$2

  case $snippet in 
    fgproc)
      echo '[foreground process]'
      ps -o $PS_COLS
      ;;
    bgproc)
      echo '[background process]'
      ps -o $PS_COLS &
      wait
      ;;

    # - Gets its own PGID
    # - Hm UNLIKE bgpipe it also gets its own TPGID?  Seems consistent in all
    #   shells.  Why is that?
    fgpipe)
      echo '[foreground pipeline, last is external]'
      ps -o $PS_COLS | cat | _tmp/cat2
      ;;

    fgpipe-lastpipe)
      echo '[foreground pipeline, last is builtin]'
      ps -o $PS_COLS | _tmp/cat2 | while read -r line; do echo "$line"; done
      ;;

    bgpipe)
      # For interactive shells, the TPGID is different here.
      # Foreground: it matches the PGID of 'ps | cat | cat2'
      # Background: it matches the PGID of bash!

      echo '[background pipeline]'
      ps -o $PS_COLS | cat | _tmp/cat2 &
      wait
      ;;

    bgpipe-lastpipe)
      echo '[background pipeline, last is builtin]'
      ps -o $PS_COLS | _tmp/cat2 | while read -r line; do echo "$line"; done &
      wait
      ;;

    subshell)
      # does NOT create a new process group.  So what happens when it's
      # interrupted?

      echo '[subshell]'
      ( ps -o $PS_COLS; echo ALIVE )
      # subshell gets its own PGID in every shell!
      ;;

    csub)
      # does NOT create a new process group.  So what happens when it's
      # interrupted?
      echo '[command sub]'
      local x
      x=$(ps -o $PS_COLS)
      echo "$x"
      ;;

    psub)
      case $sh in (dash|mksh)
        return
      esac

      echo '[process sub]'
      # use 'eval' as workaround for syntax error in dash and mksh
      eval "cat <(ps -o $PS_COLS)"
      # RESULTS
      # zsh: ps and cat are in their own process groups distinct from the shell!
      # bash: cat is in its own process group, but ps is in one with bash.  Hm
      ;;

    nested_eval)
      echo '[nested eval]'
      ps -o $PS_COLS | tac | eval 'cat | _tmp/cat2'
      ;;

    nested_pipeline)
      echo '[nested pipeline]'
      ps -o $PS_COLS | { cat | _tmp/cat2; } | tac
      ;;

    nested_pipeline_last)
      echo '[nested pipeline]'
      ps -o $PS_COLS | tac | { cat | _tmp/cat2; }
      ;;

    *)
      echo "Invalid snippet $snippet"
      exit 1
      ;;

  esac
}

run_snippet() {
  local sh=$1
  local snippet=$2
  local interactive=$3

  echo "run_snippet $sh $snippet $interactive"

  local tmp=_tmp/process-table.txt

  if test $interactive = 'yes'; then
    # Run shell with -i, but source the code first.

    local more_flags=''
    case $sh in
      (bash|bin/osh)
        more_flags='--rcfile /dev/null'
        ;;
    esac

    $sh $more_flags -i -c '. $0; show_process_table "$@"' $0 $sh $snippet > $tmp
  else
    # Run shell without -i.

    $sh $0 show_process_table $sh $snippet > $tmp
  fi

  test/process_table.py $$ $sh $snippet $interactive < $tmp
  local status=$?

  cat $tmp
  echo

  return $status
}

# We might be sourced by run_with_shell_interactive, so avoid running anything
# in that case.
case $1 in
  setup|show_process_table|run_snippet|run_with_shell|run_with_shell_interactive)
    "$@"
esac
