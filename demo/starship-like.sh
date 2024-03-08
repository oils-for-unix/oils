#!/usr/bin/env bash
#
# Usage:
#   source demo/starship-like.sh

starship_preexec() {
  local s
  s=$(which cat)
  echo "$s"
}

trap 'starship_preexec' DEBUG

shopt --set xtrace_rich
set -x
