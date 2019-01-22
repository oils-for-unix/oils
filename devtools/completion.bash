# Bash completion for run.sh scripts and running PyUnit unit tests.
#
# 2 methods are supported:
#
# 1) ./run.sh 'unit' file class.method
#
# 2) pu file class.method
#
# pu is a dummy script to enable completion to have a "word".  Not sure how else
# I could do it.
#
# TODO:
#
# There is a bunch of duplicated code between *run.sh) and *_test.py) and
# _pu_completion.  Could factor it out.
#
# Query the binary for more advanced completions?  (e.g. flag completions)
#
# Maybe it could a --completions flag.
#
# Most binaries will response with a exit code 1 in that case.  But if it
# prints a spec, then you could use that to find flags.
#
# NOTES: Bash completion is bizarre.
#
# - Use -X '!*_test.py' to remove everything EXCEPT *_test.py.  -G for glob
# does NOT do what you want.  This confusing and bizarrely undocumented.
#
# Test:
# bash --norc --noprofile
# . /etc/bash_completion
# apt-get <TAB>  -> You see actions.

log() {
  echo "$@" >&2
}

_debug() {
  log "$COMP_CWORD - ${COMP_WORDS[@]}"
}

readonly THIS_DIR=$(dirname ${BASH_SOURCE[0]})

_completion_py() {
  "$THIS_DIR/completion.py" "$@"
}

# default completion
# if $0 ends with .sh, then try scanning with completion.py
# otherwise, do the default filename/dir completion
_my_default_completion() {
  # This seems be what the default completion is, for the -1, 0, and positive
  # cases

  case "$COMP_CWORD" in

    # Fall back if there's nothing there
    -1) ;;
    # Fall back to complete a partial command ($0)
    # NOTE: not getting this to happen?
    0) ;;

    *)
      local cur="${COMP_WORDS[COMP_CWORD]}"
      local script="${COMP_WORDS[0]}"

      case $script in
        # Special completion for run.sh/test.sh scripts.  Auto is also supported.
        # unit action, and then unit tests
        # test.sh: new convention for test runner setting PYTHONPATH, etc.
        *run.sh|*test.sh|*unit.sh|*Auto)
          case "$COMP_CWORD" in
            # Complete the action first
            1)
              local script="${COMP_WORDS[0]}"
              local actions=$(_completion_py bash "$script")
              COMPREPLY=( $(compgen -W "$actions" -- "$cur") )
              return
              ;;
            # Complete *_test.py files
            2)
              local word1="${COMP_WORDS[1]}"
              if test "$word1" = 'unit' || test "$word1" = 'py-unit'; then
                # BUG: dirs don't have slashes here?
                COMPREPLY=( $(compgen -A file -o plusdirs -X '!*_test.py' -- "$cur") )
                return
              fi
              ;;
            # Complete Class.testMethod within the foo_test.py file
            3)
              local word1="${COMP_WORDS[1]}"
              if test "$word1" = 'unit' || test "$word1" = 'py-unit'; then
                local test_file="${COMP_WORDS[2]}"
                local tests=$(_completion_py pyunit "$test_file")
                if test -z "$tests"; then
                  COMPREPLY=( NOTESTS )
                else
                  COMPREPLY=( $(compgen -W "$tests" -- "$cur") )
                fi
                return
              fi
              ;;
          esac
          ;;

        *.sh)
          # For the first word, try to complete actions in shell scripts
          case "$COMP_CWORD" in
            1)
              local actions=$(_completion_py bash "$script")
              COMPREPLY=( $(compgen -W "$actions" -- "$cur") )
              return
              ;;
          esac
          ;;

        *_test.py)
          case "$COMP_CWORD" in
            # Complete Class.testMethod within the foo_test.py file
            1)
              local test_file="${COMP_WORDS[0]}"
              local tests=$(_completion_py pyunit "$test_file")
              # Show a dummy error result, so we aren't confused by the
              # directory name completion
              if test -z "$tests"; then
                COMPREPLY=( NOTESTS )
              else
                COMPREPLY=( $(compgen -W "$tests" -- "$cur") )
              fi
              return
              ;;
          esac
          ;;
      esac  # script
      ;;
  esac  # $COMP_CWORD

  # Need this for for ./run.sh action <filename>  There is an "if" in that clause.
  test -n "$_comp_fallback" && "$_comp_fallback" "$@"
}

# This could be removed; the only benefit of the "pu" prefix is that it only
# complete test files.
_pu_completion() {
  local cur="${COMP_WORDS[COMP_CWORD]}"

  case "$COMP_CWORD" in
    # Complete *_test.py files
    1)
      # Add "cur" to the glob
      # Use -o plusdirs to also list directories
      # NOTE: The compgen command is easy to test at the command line!
      COMPREPLY=( $(compgen -A file -o plusdirs -X '!*_test.py' -- "$cur") )
      ;;
    # Complete Class.testMethod within the foo_test.py file
    2)
      local test_file="${COMP_WORDS[1]}"
      local tests=$(_completion_py pyunit "$test_file")
      # Show a dummy error result, so we aren't confused by the directory name
      # completion
      if test -z "$tests"; then
        COMPREPLY=( NOTESTS )
      else
        COMPREPLY=( $(compgen -W "$tests" -- "$cur") )
      fi
      ;;
  esac
}

# global that is mutated
_comp_fallback=''

# _comp_fallback is invoked by my _my_default_completion, with the same 3 args
# as a completion function, i.e. -- "$@".
_maybe_set_comp_fallback() {
  local _distro_script
  if test -n "$BASH_VERSION"; then 
    _distro_script='/etc/bash_completion'
  else
    _distro_script=~/git/oilshell/bash-completion/osh_completion
  fi
  local _distro_function=_completion_loader

  # NOTE: _compbacllback
  if test -f $_distro_script; then
    source $_distro_script
    if test $(type -t $_distro_function) = 'function'; then
      _comp_fallback=$_distro_function
    fi
  else
    _comp_fallback=''
  fi
}

_install_completion() {
  # Fallback on distro completion so we don't clobber it.
  _maybe_set_comp_fallback

  # Fix: add "-o bashdefault" to fix completion of variable names (e.g. $HO ->
  # HOME).  When there is no completion produced by  my function, bash will fall
  # back on its defaults.
  # -o filenames: it makes it so that directories get a trailing slash.
  #
  # Formula for completing a subset of filenames: 
  # 1) complete -o filenames ...
  # 2) compgen -A file -o plusdirs -X '!*.sh' 

  complete -F _my_default_completion -o bashdefault -o filenames -D

  # pu gives filenames.  NOTE: I'm not really using pu, but I guess I should.
  # Need to put it in bashrc.bash.  It's shorter than putting ./test.sh unit in
  # every single repo!
  complete -F _pu_completion -o filenames pu
}

_install_completion

