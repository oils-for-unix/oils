#!/bin/bash
#
# Usage:
#   ./show-fd-table.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/spec-runner.sh

show-fd-table() {
  echo "   function in pid $$"
  # Make it truly parallel
  sleep 0.5
  /usr/bin/time --output /tmp/$$.txt -- spec/bin/show_fd_table.py "$@"
}

# Trying to recreate spec-runner problem with file descriptors.
main() {
  spec/bin/show_fd_table.py
  echo

  spec/bin/show_fd_table.py 2>/dev/null
  echo

  # File descriptor 3 is open!
  /usr/bin/time --output /tmp/task.txt -- spec/bin/show_fd_table.py 
  echo

  # Cannot reproduce problem.  What's the deal with descriptors 8 and 9?  Oh
  # maybe they have to be truly parallel.
  echo 'XARGS'
  seq 10 | xargs -n 1 -P 10 --verbose -- $0 show-fd-table
  echo
}

"$@"
