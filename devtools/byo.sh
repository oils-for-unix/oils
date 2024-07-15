#!/usr/bin/env bash
#
# Run test executables that obey the BYO protocol.
#
# TODO: doc/byo.md
#
# Usage:
#   devtools/byo.sh test FLAGS* ARGS*
#
# TODO:
# - client creates a clean process state for each test
# - clean directory state for each test.

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

readonly TAB=$'\t'

detect() {
  if test $# -eq 0; then
    die "Expected argv to run"
  fi

  local out

  local status=0
  set +o errexit
  out=$(BYO_COMMAND=detect "$@" < /dev/null)
  status=$?
  set -o errexit

  if test $status -ne 66; then
    die "$(printf '%q ' "$@") doesn't implement BYO: expected status 66, got $status"
  fi

  # Verbose
  if false; then
    echo
    echo "BYO commands detected in $(printf '%q ' "$@"):"
    echo "$out"
  fi
}

print-help() {
  # Other flags:
  #
  # --host       host to upload to?
  # --auth       allow writing to host
  # --no-taskset disable taskset?

  cat <<EOF
Usage: byo run-tests FLAGS*
EOF
}

# Test params:
#
# SH=dash SH=bash SH=bin/osh          # test/spec.sh
# OSH=bin/osh OSH=_bin/cxx-asan/osh   # e.g. test/*{parse,runtime}-errors.sh
# YSH=bin/osh YSH=_bin/cxx-asan/osh   # e.g. test/*{parse,runtime}-errors.sh
#
# benchmarks/compute.sh has 3 dimensions:
#   ( workload name, param1, param2 )
#
# Pretty much all tests are parameterized by shell
#
# There's also python2 vs. python3 vs. awk etc.
# benchmarks/compute
#
# Should it be 
# BYO_PARAM_OSH
#
# Usage:
#
#   $ byo run-tests test/osh-usage
#   $ byo run-tests --param OSH=bin/osh test/osh-usage
#   $ byo run-tests --param OSH=bin/osh --param OSH=_bin/cxx-asan/osh test/osh-usage
#   $ byo run-tests --param OSH='bin/osh;_bin/cxx-asan/osh' test/osh-usage
#
# Run with each value of param in sequence, and then make a big table later?
# I think you just loop over the param flags

# If no params, we run once.  Otherwise we run once per param value
FLAG_params=()
FLAG_fresh_dir=''
FLAG_capture=''
FLAG_test_filter=''

parse-flags-for-test() {
  ### Sets global vars FLAG_*

  while test $# -ne 0; do
    case "$1" in
      -h|--help)
        print-help
        exit
        ;;

      # Capture stdout and stderr? Or let it go to the terminal
      --capture)
        FLAG_capture=T
        ;;

      # Is each test case run in its own dir?  Or set TEST_TEMP_DIR
      --fresh-dir)
        FLAG_fresh_dir=T
        ;;

      --test-filter)
        if test $# -eq 1; then
          die "--test-filter requires an argument"
        fi
        shift

        # Regex in ERE syntax
        FLAG_test_filter=$1
        ;;

      --param)
        if test $# -eq 1; then
          die "--param requires an argument"
        fi
        shift

        pat='[A-Z_]+=.*'
        if ! [[ $1 =~ $pat ]]; then
            die "Expected string like PARAM_NAME=value, got $1"
        fi
        FLAG_params+=( $1 )
        ;;

      -*)
        die "Invalid flag '$1'"
        break
        ;;

      --)
        shift
        break
        ;;

      *)
        # Move on to args
        break
        ;;

    esac
    shift
  done

  ARGV=( "$@" )
}

run-tests() {
  if test $# -eq 0; then
    die "Expected argv to run"
  fi

  # Set FLAG_* and ARGV
  parse-flags-for-test "$@"

  # ARGV is the command to run, like bash foo.sh
  #
  # It's an array rather than a single command, so you can run the same scripts
  # under multiple shells:
  #
  #   bash myscript.sh
  #   osh myscript.sh
  #
  # This matters so two-test.sh can SOURCE two.sh, and run under both bash and
  # OSH.
  # That could be or --use-interp bin/osh
  #
  # could you have --use-interp python3 too?  e.g. I want benchmarks/time_.py
  # to work under both?  See time-tsv3 in tsv-lib.sh
  #
  # No that's a test param PYTHON=python3 PYTHON=python2

  detect "${ARGV[@]}"

  log '---'
  log "byo run-tests: ${ARGV[@]}"
  log

  mkdir -p _tmp
  local tmp=_tmp/byo-list.txt

  # First list the tests
  BYO_COMMAND=list-tests "${ARGV[@]}" > $tmp

  local i=0
  local status

  while read -r test_name; do

    echo "${TAB}${test_name}"

    set +o errexit
    if test -n "$FLAG_capture"; then
      # TODO: Capture it to a string
      # - Write to nice HTML file?
      BYO_COMMAND=run-test BYO_ARG="$test_name" "${ARGV[@]}" >/dev/null 2>&1
    else
      BYO_COMMAND=run-test BYO_ARG="$test_name" "${ARGV[@]}"
    fi
    status=$?
    set -o errexit

    if test $status -eq 0; then
       echo "${TAB}OK"
    else
      echo "${TAB}FAIL with status $status"
      exit 1
    fi

    i=$(( i + 1 ))
  done < $tmp

  echo
  echo "$0: $i tests passed."
}

case $1 in
  test)  # don't clobber this name
    shift
    run-tests "$@"
    ;;
  *)
    task-five "$@"
    ;;
esac
