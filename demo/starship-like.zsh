#!/usr/bin/env bash
#
# Usage:
#   source demo/starship-like.zsh

starship_preexec() {
  local s
  s=$(which cat)
  echo "$s"
}

trap 'starship_preexec' DEBUG

set -x
