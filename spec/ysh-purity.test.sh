## oils_failures_allowed: 10

# Not disallowed:
#   setglobal, mutating arguments with setvar

#### eval() is a pure function
shopt --set ysh:upgrade

var pure = ^(
  const a = 1
  const b = 2
)

var d = eval(pure, to_dict=true)
pp test_ (d)

var impure = ^(seq 3 | wc -l)

try {
  call eval(impure)
}
#= _error
echo impure code=$[_error.code]

# Can run impure code after pure code
call io->eval(impure)

## STDOUT:
(Dict)   {"a":1,"b":2}
impure code=5
3
## END

#### evalExpr() is a pure function
shopt --set ysh:upgrade

var x = 42
var pure = ^[x + 1]
echo pure=$[evalExpr(pure)]

var impure = ^[x + $(echo 3)]
try {
  echo impure code=$[evalExpr(impure)]
}
echo impure code=$[_error.code]

# Can run impure code after pure code
echo impure=$[io->evalExpr(impure)]

## STDOUT:
pure=43
impure code=5
impure=45
## END

#### Idiom to handle purity errors from untrusted config files

echo "TODO: what's the idiom?"

# trap PURE ?  Is this like trap ERR?
# You can handle these errors
#
# OILS_CRASH_DUMP_DIR=?
#
# Or do you need 2 more flags?
#
# --eval-pure-str 'try { source user-config.ysh }'
# --eval-str
#
# That is a bit annoying?
#
# --eval      pure:foo.hay
# --eval-str 'pure:echo hi'
# --eval      any:foo.hay
# --eval-str 'any:echo hi'

## STDOUT:
## END

#### Can log to stderr in pure mode

echo "TODO: log builtin?"

## STDOUT:
## END

#### Executor: can run user-defined Procs (and Hay, for now)
shopt --set ysh:upgrade

hay define Package/INSTALL

Package foo {
  version = '1.1'
  INSTALL { echo hi }
}

= _hay()

proc p {
  echo myproc
}

p

## STDOUT:
## END


#### Executor: External Commands not allowed

echo TODO

## STDOUT:
## END


#### Command subs, pipelines not allowed with --eval-pure

echo >command-sub.sh 'x=$(echo command sub)'
echo >command-sub.ysh 'var x = $(echo command sub)'

$SH --eval command-sub.sh -c 'echo $x'
$SH --eval-pure command-sub.sh -c 'echo command-sub.sh=$?'
$SH --eval-pure command-sub.ysh -c 'echo command-sub.ysh=$?'

echo

echo >pipeline.sh 'seq 3 | wc -l'

$SH --eval pipeline.sh -c 'echo eval'
$SH --eval-pure pipeline.sh -c 'echo pipeline.sh=$?'


## status: 0
## STDOUT:
command sub
command-sub.sh=5
command-sub.ysh=5

3
eval
pipeline.sh=5
## END

#### Process subs, subshells not allowed with eval()
shopt --set ysh:upgrade

var cmd = ^( cat <(echo 1) <(echo 2) )
call io->eval(cmd)

try {
  call eval(cmd)
}
echo code=$[_error.code] message=$[_error.message]
echo

var cmd = ^(( echo subshell ) )
call io->eval(cmd)

try {
  call eval(cmd)
}
echo code=$[_error.code] message=$[_error.message]

## STDOUT:
1
2
code=5 message=Process subs aren't allowed in pure mode (OILS-ERR-204)

subshell
code=5 message=Subshells aren't allowed in pure mode (OILS-ERR-204)
## END

#### Background job &
shopt --set ysh:upgrade

var cmd = ^( sleep 0.01 & wait )
call io->eval(cmd)

try {
  call eval(cmd)
}
echo code=$[_error.code] message=$[_error.message]

var cmd = ^( seq 3 | wc -l )
call io->eval(cmd)

try {
  call eval(cmd)
}
echo code=$[_error.code] message=$[_error.message]

## STDOUT:
code=5 message=Background jobs aren't allowed in pure mode (OILS-ERR-204)
3
code=5 message=Pipelines aren't allowed in pure mode (OILS-ERR-204)
## END

#### Are any builtins allowed?  true, false

# what other builtins should be allowed?
# - set and shopt could be dangerous?
# - set -- 1 2 3 may be OK
# - test -n is safe, but test --file is not
#   - YSH mostly won't need it
# - not part of YSH
#   - unset
#   - printf -v (otherwise printf does I/O)
#   - shift - use ARGV
#   - getopts
#   - alias
# Other:
#   - type - some of this does I/O
#
# If we only consider YSH, everything has a trivial replacement, e.g. true and
# false.  false can be assert [false]

var cmd = ^(
  true
  echo true
  builtin true
  echo builtin true
  command true
  echo command true

  builtin false
  echo builtin false
)

call eval (cmd)

## status: 1
## STDOUT:
true
builtin true
command true
## END

#### Are source or use builtins allowed?

# Problem: they cna "steal" information with directory traversal attacks?
# maybe only allow them in the same dirs
#
# Or maybe have a $PATH - $OILS_LIB_PATH
# and it can only be set by the caller, via command line flag?
#
# use foo.ysh  # relative to the path


echo TODO

## STDOUT:
## END

#### io and vm are not allowed

= vm.getFrame(-1)
= vm.id({})

= io.stdin

## STDOUT:
## END

#### Can't make an alias of io->eval and call it, etc.

# The --eval-pure could be make an alias, and then "trick" the post-amble into
# calling it.

var f = io->eval

var cmd = ^(echo hi)

call f(cmd)

## STDOUT:
## END

#### $RANDOM $SECONDS

echo not-implemented=$RANDOM
echo $SECONDS

## STDOUT:
## END

#### Purely-evaluated code can't set traps for later

# this follows from 'no builtins', but probably good to test

echo TODO

## STDOUT:
## END
