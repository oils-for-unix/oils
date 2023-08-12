#!/usr/bin/env bash
#
# Usage:
#   build/dev-shell-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source build/dev-shell.sh

log() {
  echo "$@" >& 2
}

banner() {
  echo '  |' 
  echo "  | $@"
  echo '  |'
  echo
}

show-path() {
  local var_name=$1
  echo "$var_name ="
  eval "echo \$$var_name" | sed 's/:/\n/g'
  echo
}

test-cli() {
  banner "Testing command line"
  show-path PATH

  echo

  log "Testing re2c"
  re2c --help | head -n 2
  echo

  log "Testing cmark"
  echo '*bold*' | doctools/cmark.py
  echo

  log "Testing python3"
  which python3
  python3 -V
  echo
}

test-python2() {
  banner "Testing python2"

  # Can't do this because of vendor/typing.py issue.
  # log "Testing oils_for_unix.py"
  # bin/oils_for_unix.py --help | head -n 2

  bin/osh --help | head -n 2
  bin/ysh --help | head -n 2

  echo
}

test-python3() {
  banner "Testing python3"
  show-path PYTHONPATH

  log "Checking mycpp"
  mycpp/mycpp_main.py --help | head -n 2
  echo

  log "Checking pexpect"
  spec/stateful/interactive.py --help | head -n 2
  echo
}

test-R() {
  banner "Testing R"
  show-path R_LIBS_USER

  which R 
  R --version
  echo

  devtools/R-test.sh test-r-packages
  echo
}

soil-run() {
  test-cli
  test-python2
  test-python3
  test-R
}

"$@"
