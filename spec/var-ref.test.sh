#!/usr/bin/env bash
#
# Var refs are done with ${!a} and local/declare -n.
#
# http://stackoverflow.com/questions/16461656/bash-how-to-pass-array-as-an-argument-to-a-function

#### var ref ${!a}
a=b
b=c
echo ref ${!a} ${a}
# Woah mksh has a completely different behavior -- var name, not var ref.
## stdout: ref c b
## BUG mksh stdout: ref a b
## N-I dash/zsh stdout-json: ""

#### var ref with special vars
myfunc() {
  local ref=$1
  echo ${!ref}
}
myfunc FUNCNAME
myfunc '?'  # osh doesn't do this dynamically
## stdout-json: "myfunc\n0\n"
## N-I mksh stdout-json: "ref\nref\n"

#### declare -n and ${!a}
declare -n a
a=b
b=c
echo ${!a} ${a}
## stdout: b c
## N-I mksh stdout: a b

#### Bad var ref with ${!a}
#set -o nounset
a='bad var name'
echo ref ${!a}
echo status=$?
## stdout-json: "ref\nstatus=0\n"
## BUG mksh stdout-json: "ref a\nstatus=0\n"
#### pass array by reference
show_value() {
  local -n array=$1
  local idx=$2
  echo "${array[$idx]}"
}
shadock=(ga bu zo meu)
show_value shadock 2
## stdout: zo

#### pass assoc array by reference
show_value() {
  local -n array=$1
  local idx=$2
  echo "${array[$idx]}"
}
days=([monday]=eggs [tuesday]=bread [sunday]=jam)
show_value days sunday
## stdout: jam
## BUG mksh stdout: [monday]=eggs
#  mksh note: it coerces "days" to 0?  Horrible.

#### pass local array by reference, relying on DYNAMIC SCOPING
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
## stdout: zo
# mksh appears not to hav elocal arrays!
## BUG mksh stdout-json: ""
## BUG mksh status: 1

#### ${!OPTIND} (used by bash completion
set -- a b c
echo ${!OPTIND}
f() {
  local OPTIND=1
  echo ${!OPTIND}
  local OPTIND=2
  echo ${!OPTIND}
}
f x y z
## STDOUT:
a
x
y
## END
## N-I mksh STDOUT:
OPTIND
OPTIND
OPTIND
## END
