## oils_failures_allowed: 2

#### Can read from ENV Obj
shopt -s ysh:upgrade

pp test_ (type(ENV))
#pp test_ (ENV)

# Set by the spec test harness

if (ENV.SH ~~ '*osh') {
  echo ok
}
#echo SH=$[ENV.SH]

## STDOUT:
(Str)   "Obj"
ok
## END

#### ENV works in different modules
shopt -s ysh:upgrade

setglobal ENV.PS4 = '%%% '

use $[ENV.REPO_ROOT]/spec/testdata/module2/env.ysh

## STDOUT:
env.ysh
OSH ok
## END


#### bin/ysh doesn't have exported vars (declare -x)

osh=$SH  # this file is run by OSH

case $osh in
  *osh)
    echo 'OSH ok'
    ;;
esac

var ysh = osh.replace('osh', 'ysh')

# NOT exported
$ysh -c 'echo sh=$[getVar("SH")]'

## STDOUT:
OSH ok
sh=null
## END

#### Temp bindings A=a B=b my-command push to ENV Obj (ysh:all)
shopt -s ysh:all

_A=a _B=b env | grep '^_' | sort

## STDOUT:
_A=a
_B=b
## END

#### Nested temp bindings

f2() {
  echo "  f2 AA=$AA BB=$BB"
  env | egrep 'AA|BB'
}

f1() {
  echo "> f1 AA=$AA"
  AA=aaaa BB=bb f2
  echo "< f1 AA=$AA"
}

AA=a f1

#
# Now with ysh:upgrade
#

shopt --set ysh:upgrade
echo

proc p2 {
  echo "  p2 AA=$[get(ENV, 'AA')] BB=$[get(ENV, 'BB')]"
  env | egrep 'AA|BB'
}

proc p1 {
  echo "> p1 AA=$[get(ENV, 'AA')]"
  AA=aaaa BB=bb p2
  echo "< p1 AA=$[get(ENV, 'AA')]"
}

AA=a p1

#
# Now with ysh:all
#

shopt --set ysh:all
echo

AA=a p1


## STDOUT:
## END

#### setglobal ENV.PYTHONPATH = 'foo' changes child process state
shopt -s ysh:upgrade

setglobal ENV.PYTHONPATH = 'foo'

#pp test_ (ENV)
#export PYTHONPATH=zz

# execute POSIX shell
sh -c 'echo pythonpath=$PYTHONPATH'

## STDOUT:
pythonpath=foo
## END

#### export builtin is disabled in ysh:all, in favor of setglobal
shopt -s ysh:all

setglobal ENV.ZZ = 'setglobal'

# execute POSIX shell
sh -c 'echo ZZ=$ZZ'

export ZZ='export'  # fails

sh -c 'echo ZZ=$ZZ'  # not reached

## status: 1
## STDOUT:
ZZ=setglobal
## END

#### ysh:upgrade can use both export builtin and setglobal ENV
shopt -s ysh:upgrade

export ZZ='export'  # fails

sh -c 'echo ZZ=$ZZ'  # not reached

setglobal ENV.ZZ = 'setglobal'  # this takes precedence

# execute POSIX shell
sh -c 'echo ZZ=$ZZ'

## STDOUT:
ZZ=export
ZZ=setglobal
## END


#### PS4 environment variable is respected
shopt -s ysh:upgrade

setglobal ENV.PS4 = '%%% '

$[ENV.SH] -c 'set -x; echo 1; echo 2'

## STDOUT:
1
2
## END
## STDERR:
%%% echo 1
%%% echo 2
## END


#### ENV.HOME is respected

HOME=zz-osh
echo ~/src

shopt --set ysh:upgrade

setvar ENV.HOME = 'ysh-zz'

# TODO: this should consult ENV.HOME
echo ~/src

# not set by spec test framework
#echo $[ENV.HOME]

## STDOUT:
zz-osh/src
ysh-zz/src
## END

#### exec builtin respects ENV

shopt --set ysh:upgrade

#export ZZ=zzz
setglobal ENV.ZZ = 'zz'

env sh -c 'echo child ZZ=$ZZ'

exec env sh -c 'echo exec ZZ=$ZZ'

## STDOUT:
child ZZ=zz
exec ZZ=zz
## END
