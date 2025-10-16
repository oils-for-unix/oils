## compare_shells: bash dash mksh zsh ash
## oils_failures_allowed: 9

# This file relates to:
#
# - doc/known-differences.md
# - "divergence" tag on github:
#   https://github.com/oils-for-unix/oils/issues?q=is%3Aissue%20state%3Aopen%20label%3Adivergence

#### xz package: dirprefix="${line##*([}"

# https://oilshell.zulipchat.com/#narrow/channel/502349-osh/topic/alpine.20xz.20-.20.22.24.7Bline.23.23*.28.5B.7D.22.20interpreted.20as.20extended.20glob/with/519718284

# NOTE: spec/extglob-match shows that bash respects it
#
# echo 'strip ##' ${x##@(foo)}

shopt -s extglob


dirprefix="${line##*([}"
echo "-$dirprefix-"

# Now try with real data
line='*([foo'
dirprefix="${line##*([}"
echo "-$dirprefix-"

## STDOUT:
--
-foo-
## END

## N-I mksh/zsh status: 1
## N-I mksh/zsh STDOUT:
## END

#### !( as negation and subshell versus extended glob - #2463

have_icu_uc=false
have_icu_i18n=false

if !($have_icu_uc && $have_icu_i18n); then
  echo one
fi
echo two

## STDOUT:
one
two
## END

## BUG mksh STDOUT:
two
## END

#### Exit code when command sub evaluates to empty str, e.g. `false` (#2435)

# OSH exits with 0 while others exit with 1
`true`; echo $?
`false`; echo $?
$(true); echo $?
$(false); echo $?

# OSH and others agree on these
eval true; echo $?
eval false; echo $?
`echo true`; echo $?
`echo false`; echo $?
## STDOUT:
0
1
0
1
0
1
0
1
## END

#### Changing PATH will invalidate PATH cache

mkdir -p _tmp/bin
mkdir -p _tmp/bin2
printf '#!/usr/bin/env sh\necho hi\n' >_tmp/bin/hello
printf '#!/usr/bin/env sh\necho hey\n' >_tmp/bin2/hello
chmod +x _tmp/bin/hello
chmod +x _tmp/bin2/hello

BIN=$PWD/_tmp/bin
BIN2=$PWD/_tmp/bin2

# Will find _tmp/bin/hello
PATH="$BIN:$PATH" hello
echo status=$?

# Should invalidate cache and then find _tmp/bin2/hello
PATH="$BIN2:$PATH" hello
echo status=$?

# Same when PATH= and export PATH=
PATH="$BIN:$PATH"
hello
echo status=$?
PATH="$BIN2:$PATH"
hello
echo status=$?

export PATH="$BIN:$PATH"
hello
echo status=$?
export PATH="$BIN2:$PATH"
hello
echo status=$?

## STDOUT:
hi
status=0
hey
status=0
hi
status=0
hey
status=0
hi
status=0
hey
status=0
## END

#### test builtin - Unexpected trailing word '--' (#2409)

# Minimal repro of sqsh build error
set -- -o; test $# -ne 0 -a "$1" != "--"
echo status=$?

# Now hardcode $1
test $# -ne 0 -a "-o" != "--"
echo status=$?

# Remove quotes around -o
test $# -ne 0 -a -o != "--"
echo status=$?

# How about a different flag?
set -- -z; test $# -ne 0 -a "$1" != "--"
echo status=$?

# A non-flag?
set -- z; test $# -ne 0 -a "$1" != "--"
echo status=$?

## STDOUT:
status=0
status=0
status=0
status=0
status=0
## END

#### (( closed with ) ) after multiple lines - #2337

(( echo 1
echo 2
echo 3
) )

## STDOUT:
1
2
3
## END

#### $(( closed with ) ) after multiple lines - #2337

echo $(( echo 1
echo 2
echo 3
) )

## STDOUT:
1 2 3
## END

## BUG dash/ash status: 2
## BUG dash/ash STDOUT:
## END

#### Nested subshell with ((( - #2337

# https://oilshell.zulipchat.com/#narrow/channel/502349-osh/topic/.28.28.28.20not.20parsed.20like.20bash/with/518874141

# spaces help
good() {
  cputype=`( ( (grep cpu /proc/cpuinfo | cut -d: -f2) ; ($PRTDIAG -v |grep -i sparc) ; grep -i cpu /var/run/dmesg.boot ) | head -n 1) 2> /dev/null`
}

bad() {
  cputype=`(((grep cpu /proc/cpuinfo | cut -d: -f2) ; ($PRTDIAG -v |grep -i sparc) ; grep -i cpu /var/run/dmesg.boot ) | head -n 1) 2> /dev/null`
  #echo cputype=$cputype
}

good
bad

## STDOUT:
## END

#### Nested subshell with (( - zdiff #2337

# found on line 137 of the zdiff util from gzip
((echo foo) | tr o 0)
## STDOUT:
f00
## END

