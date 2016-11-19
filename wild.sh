#!/bin/bash
#
# Run the osh parser on shell scripts found in the wild.
#
# Usage:
#   ./wild.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

#
# Helpers
# 

banner() {
  echo ---
  echo "$@"
  echo ---
}

parse-one() {
  bin/osh --print-ast --no-exec "$@"
}

# TODO: Could do this in parallel
parse-files() {
  for f in "$@"; do
    banner $f
    parse-one $f
  done

  # 2961 lines
  wc -l "$@" | sort -n
  echo "DONE: Parsed ${#@} files"
}

#
# Corpora
#

# TODO: Move to blog/run.sh eventually.
oil-sketch() {
  local repo=~/git/oil-sketch
  local files=( $repo/*.sh $repo/{awk,demo,make,misc,regex,tools}/*.sh )
  parse-files "${files[@]}"
}

this-repo() {
  parse-files *.sh
}

"$@"
