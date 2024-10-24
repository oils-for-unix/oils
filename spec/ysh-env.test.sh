## oils_failures_allowed: 2

#### Can read from ENV Dict
shopt -s ysh:upgrade

pp test_ (type(ENV))

sh=$[ENV.SH]
env -i PATH=$[ENV.PATH] ZZ=zz $sh -c 'echo "ZZ is $[ENV.ZZ]"'

## STDOUT:
(Str)   "Dict"
ZZ is zz
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

