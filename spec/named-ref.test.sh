#!/bin/bash
#
# Usage:
#   ./named-ref.test.sh <function name>

#### pass array by reference
show_value() {
  local -n array_name=$1
  local idx=$2
  echo "${array_name[$idx]}"
}
shadock=(ga bu zo meu)
show_value shadock 2
## stdout: zo

#### pass assoc array by reference
show_value() {
  local -n array_name=$1
  local idx=$2
  echo "${array_name[$idx]}"
}
days=([monday]=eggs [tuesday]=bread [sunday]=jam)
show_value days sunday
## stdout: jam
## BUG mksh stdout: [monday]=eggs
#  mksh note: it coerces "days" to 0?  Horrible.

#### pass local array by reference, relying on DYNAMIC SCOPING
show_value() {
  local -n array_name=$1
  local idx=$2
  echo "${array_name[$idx]}"
}
caller() {
  local shadock=(ga bu zo meu)
  show_value shadock 2
}
caller
## stdout: zo
# mksh appears not to have local arrays!
## BUG mksh stdout-json: ""
## BUG mksh status: 1

