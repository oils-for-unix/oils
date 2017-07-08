#!/usr/bin/env bash
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
# BUG mksh stdout: [monday]=eggs
#  mksh note: it coerces "days" to 0?  Horrible.

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

### Var ref with ${!a}
a=b
b=c
echo ref ${!a}
# Woah mksh has a completely different behavior -- var name, not var ref.
# stdout: ref c
# BUG mksh stdout: ref a
# N-I dash/zsh stdout-json: ""

### Bad var ref with ${!a}
#set -o nounset
a='bad var name'
echo ref ${!a}
# Woah even dash implements this!
# stdout-json: "ref\n"
# BUG mksh stdout: ref a
# N-I dash/zsh stdout-json: ""
