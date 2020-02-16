#!/usr/bin/env bash
#
# Var refs are done with ${!a}
#
# local/declare -n is tested in spec/named-ref.test.sh.
#
# http://stackoverflow.com/questions/16461656/bash-how-to-pass-array-as-an-argument-to-a-function

#### var ref ${!a}
a=b
b=c
echo ref ${!a} ${a}
## stdout: ref c b

#### ref to $@ with @
set -- one two
ref='@'
echo ref=${!ref}
## STDOUT:
ref=one two
## END

#### ref to $1 and $2 with 1 and 2
set -- one two
ref1='1'
echo ref1=${!ref1}
ref2='2'
echo ref2=${!ref2}

## STDOUT:
ref1=one
ref2=two
## END

#### var ref with 1 and @ and *
set -- x y
ref=1; printf "|%s" "${!ref}" $'\n'
ref=@; printf "|%s" "${!ref}" $'\n'
ref=*; printf "|%s" "${!ref}" $'\n'
## STDOUT:
|x|
|x|y|
|x y|
## END

#### var ref to special var BASH_SOURCE
ref='LINENO'
echo lineno=${!ref}
## STDOUT:
lineno=2
## END

#### var ref to $? with '?' (not in Oil)
myfunc() {
  local ref=$1
  echo ${!ref}
}
myfunc FUNCNAME
myfunc '?'  # osh doesn't do this dynamically
## STDOUT: 
myfunc
0
## END
## N-I osh STDOUT: 
myfunc
## END
## N-I osh status: 1

#### indirection, *then* fancy expansion features
check_eq() {
    [ "$1" = "$2" ] || { echo "$1 vs $2"; }
}
check_expand() {
    val=$(eval "echo \"$1\"")
    [ "$val" = "$2" ] || { echo "$1 -> expected $2, got $val"; }
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
a=(asdf x)
check_err '${!!a[*]}'
check_err '${!#x}'
check_err '${!#a[@]}'
# And an array reference binds tighter in the syntax, so goes first;
# there's no way to spell "indirection, then array reference".
check_expand '${!a[1]}' xx
b=(aoeu a)
check_expand '${!b[1]}' asdf  # i.e. like !(b[1]), not (!b)[1]
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

#### indirection to nasty complex array references
i=0
f() {
    ((i++))
    val=$(echo "${!1}")
    [ "$val" = y ] && echo -n "$i "
}
# Warmup: nice plain array reference
a=(x y)
f 'a[1]'
#
# Not allowed:
# no brace expansion
f 'a[{1,0}]'  # operand expected
# no process substitution (but see command substitution below!)
f 'a[<(echo x)]'  # operand expected
# TODO word splitting seems interesting
aa="1 0"
f 'a[$aa]'  # 1 0: syntax error in expression (error token is "0")
# no filename globbing
f 'a[b*]'  # operand expected
f 'a[1"]'  # bad substitution
#
# Allowed: most everything else in section 3.5 "Shell Expansions".
# tilde expansion
( PWD=1; f 'a[~+]' ); ((i++))
# shell parameter expansion
b=1
f 'a[$b]'
f 'a[${c:-1}]'
# (... and presumably most of the other features there)
# command substitution, yikes!
f 'a[$(echo 1)]'
# arithmetic expansion
f 'a[$(( 3 - 2 ))]'
echo end
# All of these are undocumented and probably shouldn't exist,
# though it's always possible some will turn up in the wild and
# we'll end up implementing them.
## stdout: 1 end
## OK bash stdout: 1 7 8 9 10 11 end

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

#### Bad var ref with ${!a}
a='bad var name'
echo ref ${!a}
echo status=$?
## STDOUT:
status=1
## END

# this error is fatal in osh
## OK osh stdout-json: ""
## OK osh status: 1

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

#### ${!ref-default}

ref=x

echo x=${!ref-default}

x=''
echo x=${!ref-default}

x=foo
echo x=${!ref-default}

## STDOUT:
x=default
x=
x=foo
## END

