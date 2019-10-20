#!/usr/bin/env bash

g() {
  argv 'G funcs' "${FUNCNAME[@]}" 
  argv 'G files' "${BASH_SOURCE[@]}"
  argv 'G lines' "${BASH_LINENO[@]}" 
}
