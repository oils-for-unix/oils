#!/bin/bash
#
# Test the child process FD state of each shell.
#
# This used to be a spec test, but I found it wasn't consistent when running in
# parallel under test/spec-runner.sh.
#
# Also see demo/fd-main.sh.
#
# Usage:
#   ./fd-state.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

readonly SCRIPT=_tmp/list-fds.sh

#### File Descriptor State is clean when running script
count-fds() {
  local sh=$1

  # Run it and count output
  $sh $SCRIPT _tmp/fd.txt
  count=$(cat _tmp/fd.txt | wc -l)
  echo "count=$count"

  # bash and dash are very orderly: there are 3 pipes and then 10 or 255
  # has the script.sh.
  # mksh and zsh have /dev/tty saved as well.  Not sure why.

  # for debugging failures
  if test "$count" -ne 4; then
    cat _tmp/fd.txt >&2
  fi
  # stdout: count=4
  # OK mksh/zsh stdout: count=5
  # stdout-json: ""
}

main() {
  # tail -n + 2: get rid of first line
  cat >$SCRIPT <<'EOF'
out=$1
ls -l /proc/$$/fd | tail -n +2 > $out
EOF

  # TODO: Make assertions here for OSH.
  for sh in bash dash mksh zsh bin/osh _bin/osh; do

    echo
    echo "=== $sh ==="
    echo

    if ! which $sh; then
      continue
    fi
    count-fds $sh
  done
}

main "$@"
