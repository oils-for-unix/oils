## compare_shells: bash dash mksh zsh ash
## oils_failures_allowed: 3

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
