#!/usr/bin/env bash
#
# TODO:
# BASH_SOURCE, BASH_LINENO, caller builtin

### ${FUNCNAME[@]} array
f() {
  argv.py "${FUNCNAME[@]}"
  g
  argv.py "${FUNCNAME[@]}"
}
g() {
  argv.py "${FUNCNAME[@]}"
}
f
# stdout-json: "['f']\n['g', 'f']\n['f']\n"
