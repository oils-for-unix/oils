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

call eval(impure)

## status: 1
## STDOUT:
(Dict)   {"a":1,"b":2}
## END

#### evalExpr() is a pure function

var x = 42
var pure = ^[x + 1]
echo pure=$[evalExpr(pure)]

var impure = ^[x + $(echo 1)]
echo impure=$[evalExpr(impure)]

## status: 1
## STDOUT:
pure=43
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


#### Executor: Command subs, pipelines, etc. not allowed

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
command-sub.sh=1
command-sub.ysh=1

3
eval
pipeline.sh=1
## END

#### Executor: Builtins not allowed

mapfile lines < <(seq 3)
echo "${lines[@]}"

## STDOUT:
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
