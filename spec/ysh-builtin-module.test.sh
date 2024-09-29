## oils_failures_allowed: 1

#### source-guard is an old way of preventing redefinition - could remove it
shopt --set ysh:upgrade

source-guard 'main' || return 0
source $REPO_ROOT/spec/testdata/module/common.ysh
source $REPO_ROOT/spec/testdata/module/module1.ysh
## STDOUT:
common
module1
## END

#### is-main

# This sources lib.ysh
$SH $REPO_ROOT/spec/testdata/module/main.ysh

# Run it directly
$SH $REPO_ROOT/spec/testdata/module/lib.ysh

## STDOUT:
lib.ysh is not the main module
hi from main.ysh
hi from lib.ysh
## END

#### is-main with -c and stdin

$SH -c 'echo -c; is-main; echo status=$?'

echo 'echo stdin; is-main; echo status=$?' | $SH

## STDOUT:
-c
status=0
stdin
status=0
## END

#### use foo.ysh creates a value.Obj

use $REPO_ROOT/spec/testdata/module2/util.ysh

var methods = Object(null, {})
var obj = Object(methods, {x: 1})
pp test_ (obj)
pp test_ (methods)


# This is a value.Obj
pp test_ (util)

util log 'hello'

## STDOUT:
## END

#### use builtin usage

use
echo no-arg=$?

use foo
echo one-arg=$?

use --extern foo
echo extern=$?

use --bad-flag
echo bad-flag=$?

use too many
echo too-many=$?

use ///no-builtin
echo no-builtin=$?


## STDOUT:
no-arg=2
one-arg=1
extern=1
bad-flag=2
too-many=2
no-builtin=1
## END

