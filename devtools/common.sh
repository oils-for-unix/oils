#!/usr/bin/env bash
# 
# Common shell functions for the devtools directory.
#
# Usage:
#   source devtools/common.sh

# Copied from test/unit.sh
banner() {
  echo -----
  echo "$@"
  echo -----
}

# TODO: delete this function?
mypy_() {
  local system=mypy
  local pip_global=/usr/local/bin/mypy
  local pip_user=~/.local/bin/mypy

  if test -x $pip_user; then
    $pip_user "$@"
  elif test -x $pip_global; then
    $pip_global "$@"
  else
    $system "$@"
  fi
}
