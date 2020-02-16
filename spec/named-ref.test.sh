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


#### flag -n and +n
x=foo

ref=x

echo ref=$ref

typeset -n ref
echo ref=$ref

typeset +n ref
echo ref=$ref

## STDOUT:
ref=x
ref=foo
ref=x
## END


#### flag -n compared with ${!ref} -- INVERTS IT!
x=foo

ref=x

echo ref=$ref
echo "!ref=${!ref}"

echo 'NOW A NAMEREF'

typeset -n ref
echo ref=$ref
echo "!ref=${!ref}"

## STDOUT:
ref=x
!ref=foo
NOW A NAMEREF
ref=foo
!ref=x
## END
## BUG mksh STDOUT:
ref=x
!ref=ref
NOW A NAMEREF
ref=foo
!ref=x
## END

#### named ref with $# doesn't work
set -- one two three

ref='#'
echo ref=$ref
typeset -n ref
echo ref=$ref

## STDOUT:
ref=#
ref=#
## END

# mksh does respect it!!  Gah.
## BUG mksh STDOUT:
ref=#
ref=3
## END


#### named ref with $# and shopt -s strict_nameref
shopt -s strict_nameref

ref='#'
echo ref=$ref
typeset -n ref
echo ref=$ref
## STDOUT:
ref=#
## END
## status: 1
## N-I bash status: 0
## N-I bash STDOUT:
ref=#
ref=#
## END
## N-I mksh status: 0
## N-I mksh STDOUT:
ref=#
ref=0
## END

#### named ref with 1 $1 etc.

ref='1'
echo ref=$ref
typeset -n ref
echo ref=$ref

ref='$1'
echo ref=$ref
typeset -n ref
echo ref=$ref

x=foo

ref='x'
echo ref=$ref
typeset -n ref
echo ref=$ref

## STDOUT:
ref=1
ref=1
ref=$1
ref=$1
ref=x
ref=foo
## END

## BUG mksh status: 2
## BUG mksh STDOUT:
ref=1
ref=
## END

#### name ref on Undef cell
typeset  -n ref

# This is technically incorrect: an undefined name shouldn't evaluate to empty
# string.  mksh doesn't allow it.
echo ref=$ref

echo nounset
set -o nounset
echo ref=$ref
## status: 1
## STDOUT:
ref=
nounset
## END
## OK mksh stdout-json: ""

#### -n attribute before it has a value
typeset -n ref

echo ref=$ref

# Now that it's a string, it still has the -n attribute
x=XX
ref=x
echo ref=$ref

## STDOUT:
ref=
ref=XX
## END
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### -n attribute on array is hard error, not a warning
typeset -n ref

echo ref=$ref

x=XX

# bash prints warning: REMOVES the nameref attribute here!
ref=(x y)
echo ref=$ref

## status: 1
## stdout-json: ""
## BUG bash status: 0
## BUG bash STDOUT:
ref=
ref=x
## END
