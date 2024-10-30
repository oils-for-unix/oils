## oils_failures_allowed: 4

#### Can read from ENV Dict
shopt -s ysh:upgrade

pp test_ (type(ENV))
#pp test_ (ENV)

# Set by the spec test harness

if (ENV.SH ~~ '*osh') {
  echo ok
}

#echo SH=$[ENV.SH]

## STDOUT:
(Str)   "Dict"
ok
## END

#### YSH doesn't have exported vars (declare -x)

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

#### Temp bindings A=a B=b my-command push to ENV dict
shopt -s ysh:upgrade

_A=a _B=b env | grep '^_' | sort

## STDOUT:
_A=a
_B=b
## END

#### setglobal ENV.PYTHONPATH = 'foo' changes child process state
shopt -s ysh:upgrade

setglobal ENV.PYTHONPATH = 'foo'

pp test_ (ENV)

#export PYTHONPATH=zz

# execute POSIX shell
sh -c 'echo pythonpath=$PYTHONPATH'

## STDOUT:
## END

#### export builtin still works
shopt -s ysh:upgrade

export PYTHONPATH='foo'

#pp test_ (ENV)

# execute POSIX shell
sh -c 'echo pythonpath=$PYTHONPATH'

## STDOUT:
pythonpath=foo
## END


#### PS4 environment variable is respected
shopt -s ysh:upgrade

setglobal ENV.PS4 = '%%% '

$[ENV.SH] -c 'set -x; echo 1; echo 2'

## STDOUT:
TODO
## END


#### ENV works in different modules
shopt -s ysh:upgrade

setglobal ENV.PS4 = '%%% '

use $[ENV.REPO_ROOT]/spec/testdata/module2/env.ysh

## STDOUT:
env.ysh
OSH ok
## END


#### HOME var
shopt --set ysh:upgrade

#setvar HOME = 'yo'

# TODO: this should consult ENV.HOME
echo ~

# not set by spec test framework
echo $[ENV.HOME]

#echo ~root

#echo ~bob/

## STDOUT:
## END
