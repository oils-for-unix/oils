#!/bin/bash
#
# Var refs are done with ${!a} and local/declare -n.
#
# http://stackoverflow.com/questions/16461656/bash-how-to-pass-array-as-an-argument-to-a-function

### pass array by reference
show_value() {
  local -n array=$1
  local idx=$2
  echo "${array[$idx]}"
}
shadock=(ga bu zo meu)
show_value shadock 2
# stdout: zo


### pass assoc array by reference
show_value() {
  local -n array=$1
  local idx=$2
  echo "${array[$idx]}"
}
days=([monday]=eggs [tuesday]=bread [sunday]=jam)
show_value days sunday
# stdout: jam

### pass local array by reference, relying on DYNAMIC SCOPING
show_value() {
  local -n array=$1
  local idx=$2
  echo "${array[$idx]}"
}
caller() {
  local shadock=(ga bu zo meu)
  show_value shadock 2
}
caller
# stdout: zo
# mksh appears not to hav elocal arrays!
# BUG mksh stdout-json: ""
# BUG mksh status: 1
