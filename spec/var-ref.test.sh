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

#### var ref: positional params
set -- x y
ref=1; printf "|%s" "${!ref}" $'\n'
ref=@; printf "|%s" "${!ref}" $'\n'
ref=*; printf "|%s" "${!ref}" $'\n'
## STDOUT:
|x|
|x|y|
|x y|
## END

#### var ref with special vars
myfunc() {
  local ref=$1
  echo ${!ref}
}
myfunc FUNCNAME
myfunc '?'  # osh doesn't do this dynamically
## stdout-json: "myfunc\n0\n"
## N-I mksh stdout-json: "ref\nref\n"

#### indirection, *then* fancy expansion features
check_eq() {
    [ "$1" = "$2" ] || { echo "$1 vs $2"; }
}
check_expand() {
    val=$(eval "echo \"$1\"")
    [ "$val" = "$2" ] || { echo "$1 -> $val vs $2"; }
}
check_err() {
    e="$1"
    msg=$(eval "$e" 2>&1) && echo "bad success: $e"
    [ -z "$2" ] || [[ "$msg" == $2 ]] || echo "bad err msg: $e -> $msg"
}
# Nearly everything in manual section 3.5.3 "Shell Parameter Expansion"
# is allowed after a !-indirection.
#
# Not allowed: any further prefix syntax.
x=xx; xx=aaabcc
xd=x
check_err '${!!xd}'
check_err '${!!x*}'
a=(1 2)
check_err '${!!a[*]}'
check_err '${!#x}'
check_err '${!#a[@]}'
#
# Allowed: apparently everything else.
y=yy; yy=
check_expand '${!y:-foo}' foo
check_expand '${!x:-foo}' aaabcc
z=zz; zz=
check_eq "${!z:=foo}" foo ; check_expand '$zz' foo
check_eq "${!z:=bar}" foo ; check_expand '$zz' foo
w=ww; ww=
check_err '${!w:?oops}' '*: oops'
check_expand '${!x:?oops}' aaabcc
check_expand '${!y:+foo}' ''
check_expand '${!x:+foo}' foo
check_expand '${!x:2}' abcc
check_expand '${!x:2:2}' ab
check_expand '${!x#*a}' aabcc
check_expand '${!x%%c*}' aaab
check_expand '${!x/a*b/d}' dcc
check_expand '${!x^a}' Aaabcc
p=pp; pp='\$ '
check_expand '${!p@P}' '$ '
echo ok
## stdout: ok

#### indirection *to* an array reference
f() {
  printf ".%s" "${!1}"
  echo
}
f a[0]
b=(x y)
f b[0]
f b[@]
f "b[*]"
# Also associative arrays.
## STDOUT:
.
.x
.x.y
.x y
## END
## N-I dash status: 2
## N-I dash stdout-json: ""

#### indirection *to* fancy expansion features bash disallows
check_indir() {
    result="${!1}"
    desugared_result=$(eval 'echo "${'"$1"'}"')
    [ "$2" = "$desugared_result" ] || { echo "$1 $desugared_result";  }
}
x=y
y=a
a=(x y)
declare -A aa
aa=([k]=r [l]=s)
# malformed array indexing
check_indir "a[0"
check_indir "aa[k"
# double indirection
check_indir "!x"      a
check_indir "!a[0]"   y
# apparently everything else in the manual under "Shell Parameter Expansion"
check_indir "x:-foo"  y
check_indir "x:=foo"  y
check_indir "x:?oops" y
check_indir "x:+yy"   yy
check_indir "x:0"     y
check_indir "x:0:1"   y
check_indir "!a@"    "a aa"
# (!a[@] is elsewhere)
check_indir "#x"      1
check_indir "x#y"
check_indir "x/y/foo" foo
check_indir "x@Q"    "'y'"
echo done
## status: 1
## stdout-json: ""
## OK bash status: 0
## OK bash stdout: done

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
## STDOUT:
status=1
## END
## BUG mksh STDOUT:
ref a
status=0
## END

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
