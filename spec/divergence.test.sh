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

#### builtin cat crashes a subshell (#2530)

((/usr/bin/cat </dev/zero; echo $? >&7) | true) 7>&1

((cat </dev/zero; echo $? >&7) | true) 7>&1

## STDOUT:
141
141
## END
