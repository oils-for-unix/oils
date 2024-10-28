## compare_shells: bash dash mksh
## oils_failures_allowed: 2
## tags: interactive

# Test options to set, shopt, $SH.

#### $- with -c
# dash's behavior seems most sensible here?
$SH -o nounset -c 'echo $-'
## stdout: u
## OK bash stdout: huBc
## OK mksh stdout: uhc
## status: 0

#### $- with pipefail
set -o pipefail -o nounset
echo $-
## stdout: u
## status: 0
## OK bash stdout: huBs
## OK mksh stdout: ush
## N-I dash stdout-json: ""
## N-I dash status: 2

#### $- and more options
set -efuC
o=$-
[[ $o == *e* ]]; echo yes
[[ $o == *f* ]]; echo yes
[[ $o == *u* ]]; echo yes
[[ $o == *C* ]]; echo yes
## STDOUT:
yes
yes
yes
yes
## END
## N-I dash stdout-json: ""
## N-I dash status: 127

#### $- with interactive shell
$SH -c 'echo $-' | grep i || echo FALSE
$SH -i -c 'echo $-' | grep -q i && echo TRUE
## STDOUT:
FALSE
TRUE
## END
#### pass short options like sh -e
$SH -e -c 'false; echo status=$?'
## stdout-json: ""
## status: 1

#### pass long options like sh -o errexit
$SH -o errexit -c 'false; echo status=$?'
## stdout-json: ""
## status: 1

#### pass shopt options like sh -O nullglob
$SH +O nullglob -c 'echo foo *.nonexistent bar'
$SH -O nullglob -c 'echo foo *.nonexistent bar'
## STDOUT:
foo *.nonexistent bar
foo bar
## END
## N-I dash/mksh stdout-json: ""
## N-I dash status: 2
## N-I mksh status: 1

#### can continue after unknown option
# dash and mksh make this a fatal error no matter what.
set -o errexit
set -o STRICT || true # unknown option
echo hello
## stdout: hello
## status: 0
## BUG dash/mksh stdout-json: ""
## BUG dash status: 2
## BUG mksh status: 1

#### set with both options and argv
set -o errexit a b c
echo "$@"
false
echo done
## stdout: a b c
## status: 1

#### set -o vi/emacs
set -o vi
echo $?
set -o emacs
echo $?
## STDOUT:
0
0
## END

#### vi and emacs are mutually exclusive
show() {
  shopt -o -p | egrep 'emacs$|vi$'
  echo ___
};
show

set -o emacs
show

set -o vi
show

## STDOUT:
set +o emacs
set +o vi
___
set -o emacs
set +o vi
___
set +o emacs
set -o vi
___
## END
## N-I dash/mksh STDOUT:
___
___
___
## END

#### interactive shell starts with emacs mode on
case $SH in (dash) exit ;; esac
case $SH in (bash|*osh) flag='--rcfile /dev/null' ;; esac

code='test -o emacs; echo $?; test -o vi; echo $?'

echo non-interactive
$SH $flag -c "$code"

echo interactive
$SH $flag -i -c "$code"

## STDOUT:
non-interactive
1
1
interactive
0
1
## END
## OK mksh STDOUT:
non-interactive
0
1
interactive
0
1
## END
## N-I dash stdout-json: ""

#### nounset
echo "[$unset]"
set -o nounset
echo "[$unset]"
echo end  # never reached
## stdout: []
## status: 1
## OK dash status: 2

#### -u is nounset
echo "[$unset]"
set -u
echo "[$unset]"
echo end  # never reached
## stdout: []
## status: 1
## OK dash status: 2

#### nounset with "$@"
set a b c
set -u  # shouldn't touch argv
echo "$@"
## stdout: a b c

#### set -u -- clears argv
set a b c
set -u -- # shouldn't touch argv
echo "$@"
## stdout: 

#### set -u -- x y z
set a b c
set -u -- x y z
echo "$@"
## stdout: x y z

#### reset option with long flag
set -o errexit
set +o errexit
echo "[$unset]"
## stdout: []
## status: 0

#### reset option with short flag
set -u 
set +u
echo "[$unset]"
## stdout: []
## status: 0

#### set -eu (flag parsing)
set -eu 
echo "[$unset]"
echo status=$?
## stdout-json: ""
## status: 1
## OK dash status: 2

#### -n for no execution (useful with --ast-output)
# NOTE: set +n doesn't work because nothing is executed!
echo 1
set -n
echo 2
set +n
echo 3
# osh doesn't work because it only checks -n in bin/oil.py?
## STDOUT:
1
## END
## status: 0

#### pipefail
# NOTE: the sleeps are because osh can fail non-deterministically because of a
# bug.  Same problem as PIPESTATUS.
{ sleep 0.01; exit 9; } | { sleep 0.02; exit 2; } | { sleep 0.03; }
echo $?
set -o pipefail
{ sleep 0.01; exit 9; } | { sleep 0.02; exit 2; } | { sleep 0.03; }
echo $?
## STDOUT:
0
2
## END
## status: 0
## N-I dash STDOUT:
0
## END
## N-I dash status: 2

#### shopt -p -o prints 'set' options
case $SH in dash|mksh) exit ;; esac

shopt -po nounset
set -o nounset
shopt -po nounset

echo --

shopt -po | egrep -o 'errexit|noglob|nounset'

## STDOUT: 
set +o nounset
set -o nounset
--
errexit
noglob
nounset
## END
## N-I dash/mksh STDOUT:
## END

#### shopt -o prints 'set' options
case $SH in dash|mksh) exit ;; esac

shopt -o | egrep -o 'errexit|noglob|nounset'
echo --
## STDOUT: 
errexit
noglob
nounset
--
## END
## N-I dash/mksh STDOUT:
## END

#### shopt -p prints 'shopt' options
shopt -p nullglob
shopt -s nullglob
shopt -p nullglob
## STDOUT:
shopt -u nullglob
shopt -s nullglob
## END
## N-I dash/mksh stdout-json: ""
## N-I dash/mksh status: 127

#### shopt with no flags prints options
cd $TMP

# print specific options.  OSH does it in a different format.
shopt nullglob failglob > one.txt
wc -l one.txt
grep -o nullglob one.txt
grep -o failglob one.txt

# print all options
shopt | grep nullglob | wc -l
## STDOUT:
2 one.txt
nullglob
failglob
1
## END
## N-I dash/mksh STDOUT:
0 one.txt
0
## END

#### noclobber off
set -o errexit

echo foo > can-clobber
echo status=$?
set +C

echo foo > can-clobber
echo status=$?
set +o noclobber

echo foo > can-clobber
echo status=$?
cat can-clobber

## STDOUT:
status=0
status=0
status=0
foo
## END

#### noclobber on

rm -f no-clobber
set -C

echo foo > no-clobber
echo create=$?

echo overwrite > no-clobber
echo overwrite=$?

echo force >| no-clobber
echo force=$?

cat no-clobber

## STDOUT:
create=0
overwrite=1
force=0
force
## END
## OK dash STDOUT:
create=0
overwrite=2
force=0
force
## END

#### noclobber on <>
set -C
echo foo >| $TMP/no-clobber
exec 3<> $TMP/no-clobber
read -n 1 <&3
echo -n . >&3
exec 3>&-
cat $TMP/no-clobber
## stdout-json: "f.o\n"
## N-I dash stdout-json: ".oo\n"

#### SHELLOPTS is updated when options are changed
echo $SHELLOPTS | grep -q xtrace
echo $?
set -x
echo $SHELLOPTS | grep -q xtrace
echo $?
set +x
echo $SHELLOPTS | grep -q xtrace
echo $?
## STDOUT:
1
0
1
## END
## N-I dash/mksh STDOUT:
1
1
1
## END

#### SHELLOPTS is readonly
SHELLOPTS=x
echo status=$?
## stdout: status=1
## N-I dash/mksh stdout: status=0

# Setting a readonly variable in osh is a hard failure.
## OK osh status: 1
## OK osh stdout-json: ""

#### SHELLOPTS and BASHOPTS are set

# 2024-06 - tickled by Samuel testing Gentoo

# bash: bracexpand:hashall etc.

echo shellopts ${SHELLOPTS:?} > /dev/null
echo bashopts ${BASHOPTS:?} > /dev/null

## STDOUT:
## END

## N-I dash status: 2
## N-I mksh status: 1


#### set - -
set a b
echo "$@"
set - a b
echo "$@"
set -- a b
echo "$@"
set - -
echo "$@"
set - +
echo "$@"
set + -
echo "$@"
set -- --
echo "$@"

# note: zsh is different, and yash is totally different
## STDOUT:
a b
a b
a b
-
+
+
--
## END
## OK osh/yash STDOUT:
a b
- a b
a b
- -
- +
+ -
--
## END
## BUG mksh STDOUT:
a b
a b
a b
-
+
-
--
## END
## BUG zsh STDOUT:
a b
a b
a b

+

--
## END

#### set -o lists options
# NOTE: osh doesn't use the same format yet.
set -o | grep -o noexec
## STDOUT:
noexec
## END

#### set without args lists variables
__GLOBAL=g
f() {
  local __mylocal=L
  local __OTHERLOCAL=L
  __GLOBAL=mutated
  set | grep '^__'
}
g() {
  local __var_in_parent_scope=D
  f
}
g
## status: 0
## STDOUT:
__GLOBAL=mutated
__OTHERLOCAL=L
__mylocal=L
__var_in_parent_scope=D
## END
## OK mksh STDOUT:
__GLOBAL=mutated
__var_in_parent_scope=D
__OTHERLOCAL=L
__mylocal=L
## END
## OK dash STDOUT:
__GLOBAL='mutated'
__OTHERLOCAL='L'
__mylocal='L'
__var_in_parent_scope='D'
## END

#### 'set' and 'eval' round trip

# NOTE: not testing arrays and associative arrays!
_space='[ ]'
_whitespace=$'[\t\r\n]'
_sq="'single quotes'"
_backslash_dq="\\ \""
_unicode=$'[\u03bc]'

# Save the variables
varfile=$TMP/vars-$(basename $SH).txt

set | grep '^_' > "$varfile"

# Unset variables
unset _space _whitespace _sq _backslash_dq _unicode
echo [ $_space $_whitespace $_sq $_backslash_dq $_unicode ]

# Restore them

. $varfile
echo "Code saved to $varfile" 1>&2  # for debugging

test "$_space" = '[ ]' && echo OK
test "$_whitespace" = $'[\t\r\n]' && echo OK
test "$_sq" = "'single quotes'" && echo OK
test "$_backslash_dq" = "\\ \"" && echo OK
test "$_unicode" = $'[\u03bc]' && echo OK

## STDOUT:
[ ]
OK
OK
OK
OK
OK
## END

#### set without args and array variables (not in OSH)
declare -a __array
__array=(1 2 '3 4')
set | grep '^__'
## STDOUT:
__array=([0]="1" [1]="2" [2]="3 4")
## END
## OK mksh STDOUT:
__array[0]=1
__array[1]=2
__array[2]='3 4'
## N-I dash stdout-json: ""
## N-I dash status: 2
## N-I osh stdout-json: ""
## N-I osh status: 1

#### set without args and assoc array variables (not in OSH)
typeset -A __assoc
__assoc['k e y']='v a l'
__assoc[a]=b
set | grep '^__'
## STDOUT:
__assoc=([a]="b" ["k e y"]="v a l" )
## END
## N-I mksh stdout-json: ""
## N-I mksh status: 1
## N-I dash stdout-json: ""
## N-I dash status: 1
## N-I osh stdout-json: ""
## N-I osh status: 1

#### shopt -q
shopt -q nullglob
echo nullglob=$?

# set it
shopt -s nullglob

shopt -q nullglob
echo nullglob=$?

shopt -q nullglob failglob
echo nullglob,failglob=$?

# set it
shopt -s failglob
shopt -q nullglob failglob
echo nullglob,failglob=$?

## STDOUT:
nullglob=1
nullglob=0
nullglob,failglob=1
nullglob,failglob=0
## END
## N-I dash/mksh STDOUT:
nullglob=127
nullglob=127
nullglob,failglob=127
nullglob,failglob=127
## END

#### shopt -q invalid
shopt -q invalidZZ
echo invalidZZ=$?
## STDOUT:
invalidZZ=2
## END
## OK bash STDOUT:
invalidZZ=1
## END
## N-I dash/mksh STDOUT:
invalidZZ=127
## END

#### shopt -s strict:all
n=2

show-strict() {
  shopt -p | grep 'strict_' | head -n $n
  echo -
}

show-strict
shopt -s strict:all
show-strict
shopt -u strict_arith
show-strict
## STDOUT:
shopt -u strict_argv
shopt -u strict_arith
-
shopt -s strict_argv
shopt -s strict_arith
-
shopt -s strict_argv
shopt -u strict_arith
-
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I bash/mksh STDOUT:
-
-
-
## END

#### shopt allows for backward compatibility like bash

# doesn't have to be on, but just for testing
set -o errexit

shopt -p nullglob || true  # bash returns 1 here?  Like -q.

# This should set nullglob, and return 1, which can be ignored
shopt -s nullglob strict_OPTION_NOT_YET_IMPLEMENTED 2>/dev/null || true
echo status=$?

shopt -p nullglob || true

## STDOUT:
shopt -u nullglob
status=0
shopt -s nullglob
## END
## N-I dash/mksh STDOUT:
status=0
## END
## N-I dash/mksh status: 0

#### shopt -p validates option names
shopt -p nullglob invalid failglob
echo status=$?
# same thing as -p, slightly different format in bash
shopt nullglob invalid failglob > $TMP/out.txt
status=$?
sed --regexp-extended 's/\s+/ /' $TMP/out.txt  # make it easier to assert
echo status=$status
## STDOUT:
status=2
status=2
## END
## OK bash STDOUT:
shopt -u nullglob
shopt -u failglob
status=1
nullglob off
failglob off
status=1
## END
## N-I dash/mksh STDOUT:
status=127
status=127
## END

#### shopt -p -o validates option names
shopt -p -o errexit invalid nounset
echo status=$?
## STDOUT:
set +o errexit
status=2
## END
## OK bash STDOUT:
set +o errexit
set +o nounset
status=1
## END
## N-I dash/mksh STDOUT:
status=127
## END

#### stubbed out bash options
shopt -s ignore_shopt_not_impl
for name in foo autocd cdable_vars checkwinsize; do
  shopt -s $name
  echo $?
done
## STDOUT:
2
0
0
0
## END
## OK bash STDOUT:
1
0
0
0
## END
## OK dash/mksh STDOUT:
127
127
127
127
## END

#### shopt -s nounset works in YSH, not in bash
case $SH in
  *dash|*mksh)
    echo N-I
    exit
    ;;
esac
shopt -s nounset
echo status=$?

# get rid of extra space in bash output
set -o | grep nounset | sed 's/[ \t]\+/ /g'

## STDOUT:
status=0
set -o nounset
## END
## OK bash STDOUT:
status=1
nounset off
# END
## N-I dash/mksh STDOUT:
N-I
## END

#### Unimplemented options - print, query, set, unset
case $SH in dash|mksh) exit ;; esac

opt_name=xpg_echo

shopt -p xpg_echo
shopt -q xpg_echo; echo q=$?

shopt -s xpg_echo
shopt -p xpg_echo

shopt -u xpg_echo
shopt -p xpg_echo
echo p=$?  # weird, bash also returns a status

shopt xpg_echo >/dev/null
echo noflag=$?

shopt -o errexit >/dev/null
echo set=$?

## STDOUT:
q=2
p=2
noflag=2
set=1
## END

## OK bash STDOUT:
shopt -u xpg_echo
q=1
shopt -s xpg_echo
shopt -u xpg_echo
p=1
noflag=1
set=1
## END

## N-I dash/mksh STDOUT:
## END

#### Unimplemented options - OSH shopt -s ignore_shopt_not_impl
case $SH in dash|mksh) exit ;; esac

shopt -s ignore_shopt_not_impl

opt_name=xpg_echo

shopt -p xpg_echo
shopt -q xpg_echo; echo q=$?

shopt -s xpg_echo
shopt -p xpg_echo

shopt -u xpg_echo
shopt -p xpg_echo
echo p=$?  # weird, bash also returns a status

shopt xpg_echo >/dev/null
echo noflag=$?

shopt -o errexit >/dev/null
echo set=$?

## STDOUT:
shopt -u xpg_echo
q=1
shopt -s xpg_echo
shopt -u xpg_echo
p=1
noflag=1
set=1
## END

## N-I dash/mksh STDOUT:
## END

#### shopt -p exit code (regression)
case $SH in dash|mksh) exit ;; esac

shopt -p > /dev/null
echo status=$?

## STDOUT:
status=0
## END

## N-I dash/mksh STDOUT:
## END

#### no-ops not shown by shopt -p

shopt -p | grep xpg
echo --
## STDOUT:
--
## END
## OK bash STDOUT:
shopt -u xpg_echo
--
## END


