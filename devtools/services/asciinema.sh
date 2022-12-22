#!/usr/bin/env bash
#
# Usage:
#   devtools/services/asciinema.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

install() {
  sudo apt-get install asciinema
}


#
# Instructions:
#
# 'asciinema rec' to record interactively
# 'asciinema auth' to be able to delete/rename uploaded recordings
#
# https://asciinema.org/~andyc
#

"$@"
