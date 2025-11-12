## compare_shells: bash dash mksh zsh ash
## oils_failures_allowed: 4

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

#### set -u failure in eval doesn't exit the parent process
set -u
test_function() {
    x=$1
}

echo "before"
eval test_function
# bash spec says that set -u failures should exit the shell
# posix spec says that eval shall read and execute a command by the current shell, so the
# running shell should exit too
echo "after"
## status: 1
## OK ash/dash status: 2
## BUG mksh/zsh status: 0
## STDOUT:
before
## END
## BUG zsh/mksh STDOUT:
before
after
## END

#### set -u nested evals
set -u
test_function_2() {
    x=$blarg
}
test_function() {
    eval "test_function_2"
}

echo "before"
eval test_function
echo "after"
## status: 1
## OK ash/dash status: 2
## BUG mksh/zsh status: 0
## STDOUT:
before
## END
## BUG zsh/mksh STDOUT:
before
after
## END

#### set -u no eval
set -u

echo "before"
x=$blarg
echo "after"
## status: 1
## OK ash/dash status: 2
## STDOUT:
before
## END

#### builtin cat crashes a subshell (#2530)

((/usr/bin/cat </dev/zero; echo $? >&7) | true) 7>&1

((cat </dev/zero; echo $? >&7) | true) 7>&1

## STDOUT:
141
141
## END
