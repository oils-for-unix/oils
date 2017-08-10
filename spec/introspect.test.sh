#!/usr/bin/env bash
#
# TODO:
# BASH_SOURCE, BASH_LINENO, caller builtin

### ${FUNCNAME[@]} array
f() {
  echo "begin: ${FUNCNAME[@]}"
  g
  echo "end: ${FUNCNAME[@]}"
}
g() {
  echo "func: ${FUNCNAME[@]}"
}
f
# stdout-json: "begin: f\nfunc: g f\nend: f\n"
# N-I mksh stdout-json: "begin: \nfunc: \nend: \n"
# N-I dash stdout-json: ""
# N-I dash status: 2
