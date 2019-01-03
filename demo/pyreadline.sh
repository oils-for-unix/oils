#!/bin/bash
#
# Usage:
#   ./pyreadline.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

scrape-flags() {
  demo/scrape_flags.py "$@"
}

demo() {
  ls --help | scrape-flags > _tmp/ls_flags.txt

  grep --help | scrape-flags > _tmp/grep_flags.txt

  head _tmp/*_flags.txt
}

"$@"
