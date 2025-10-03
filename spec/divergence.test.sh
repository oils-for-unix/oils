## compare_shells: bash dash mksh zsh ash
## oils_failures_allowed: 6

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


#### ((( with nested subshells

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

#### Nested subshell (#2398)

# found on line 137 of the zdiff util from gzip
((echo foo) | tr o 0)
## STDOUT:
f00
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

#### Executing command with same name as directory in PATH (#2429)

# Make the following directory structure. File type and permission bits are
# given on the left.
# [drwxr-xr-x]  _tmp
# +-- [drwxr-xr-x]  bin
# |   \-- [-rwxr-xr-x]  hello
# +-- [drwxr-xr-x]  notbin
# |   \-- [-rw-r--r--]  hello
# \-- [drwxr-xr-x]  dir
#     \-- [drwxr-xr-x]  hello
mkdir -p _tmp/bin
mkdir -p _tmp/bin2
mkdir -p _tmp/notbin
mkdir -p _tmp/dir/hello
printf '#!/usr/bin/env sh\necho hi\n' >_tmp/notbin/hello
printf '#!/usr/bin/env sh\necho hi\n' >_tmp/bin/hello
chmod +x _tmp/bin/hello

DIR=$PWD/_tmp/dir
BIN=$PWD/_tmp/bin
NOTBIN=$PWD/_tmp/notbin

# The command resolution will search the path for matching *files* (not
# directories) WITH the execute bit set.

# Should find executable hello right away and run it
PATH="$BIN:$PATH" hello
echo status=$?

hash -r  # Needed to clear the PATH cache

# Will see hello dir, skip it and then find&run the hello exe
PATH="$DIR:$BIN:$PATH" hello
echo status=$?

hash -r  # Needed to clear the PATH cache

# Will see hello (non-executable) file, skip it and then find&run the hello exe
PATH="$NOTBIN:$BIN:$PATH" hello
echo status=$?

## STDOUT:
hi
status=0
hi
status=0
hi
status=0
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
