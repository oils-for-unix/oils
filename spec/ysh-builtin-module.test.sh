## oils_failures_allowed: 6

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
extern=0
bad-flag=2
too-many=2
no-builtin=1
## END


#### use --extern is a no-op, for static analysis

use --extern grep sed awk
echo status=$?

use --extern zzz
echo status=$?

## STDOUT:
status=0
status=0
## END

#### use foo.ysh creates a value.Obj, and it's cached on later invocations

shopt --set ysh:upgrade

var caller_no_leak = 42

use $REPO_ROOT/spec/testdata/module2/util.ysh

# This is a value.Obj
pp test_ (['util', util])
var id1 = id(util)

var saved_util = util

use $REPO_ROOT/spec/testdata/module2/util.ysh
pp test_ (['repeated', util])
var id2 = id(util)

# Create a symlink to test normalization

ln -s $REPO_ROOT/spec/testdata/module2/util.ysh symlink.ysh

use symlink.ysh
pp test_ (['symlink', symlink])
var id3 = id(symlink)

#pp test_ ([id1, id2, id3])

# Make sure they are all the same object
assert [id1 === id2]
assert [id2 === id3]

# Doesn't leak from util.ysh
echo "setvar_noleak $[getVar('setvar_noleak')]"
echo "setglobal_noleak $[getVar('setglobal_noleak')]"

## STDOUT:
caller_no_leak = null
(List)   ["util",{"MY_INTEGER":42,"log":<Proc>,"die":<Proc>,"setvar_noleak":"util.ysh","setglobal_noleak":"util.ysh"}]
(List)   ["repeated",{"MY_INTEGER":42,"log":<Proc>,"die":<Proc>,"setvar_noleak":"util.ysh","setglobal_noleak":"util.ysh"}]
(List)   ["symlink",{"MY_INTEGER":42,"log":<Proc>,"die":<Proc>,"setvar_noleak":"util.ysh","setglobal_noleak":"util.ysh"}]
setvar_noleak null
setglobal_noleak null
## END

#### procs in a module can call setglobal on globals in that module
shopt --set ysh:upgrade

use $REPO_ROOT/spec/testdata/module2/globals.ysh

# get() should work on Obj too.  Possibly we should get rid of the default
var myproc = get(propView(globals), 'mutate-g1', null)
call setVar('mutate-g1', myproc)

# you can mutate it internally, but the mutation isn't VISIBLE.  GAH!
# I wonder if you make Cell a value? or something
mutate-g1
echo

# PROBLEM: This is a value.Obj COPY, not the fucking original!!!
# immutable objects??

#pp test_ ([id(globals.d), globals.d])

call globals.mutateG2()
echo

#= propView(globals)

# these are not provided
echo "globals.g1 = $[get(globals, 'g1', null)]"
echo "globals.g2 = $[get(globals, 'g2', null)]"
echo

#pp frame_vars_
# Shouldn't appear here
echo "importer g1 = $[getVar('g1')]"
echo "importer g2 = $[getVar('g2')]"

## STDOUT:
g1 = g1
g1 = proc mutated

g2 = g2
g2 = func mutated

globals.g1 = null
globals.g2 = null

importer g1 = null
importer g2 = null
## END

#### no provided names
shopt --set ysh:upgrade

use $REPO_ROOT/spec/testdata/module2/no-provide.ysh

## status: 1
## STDOUT:
## END

#### bad provide type
shopt --set ysh:upgrade

use $REPO_ROOT/spec/testdata/module2/bad-provide-type.ysh

## status: 1
## STDOUT:
## END

#### invalid provide entries
shopt --set ysh:upgrade

use $REPO_ROOT/spec/testdata/module2/bad-provide.ysh

## status: 1
## STDOUT:
## END

#### use foo.ysh creates a value.Obj with __invoke__
shopt --set ysh:upgrade

use $REPO_ROOT/spec/testdata/module2/util.ysh

# This is a value.Obj
pp test_ (util)

util log 'hello'
util die 'hello'

## STDOUT:
## END

#### circular import is an error?

echo hi

## STDOUT:
## END


#### user can inspect __modules__ cache

echo 'TODO: Dict view of realpath() string -> Obj instance'

## STDOUT:
## END

#### use foo.ysh --pick a b

echo TODO

## STDOUT:
## END


#### use foo.ysh --all-provided

echo TODO

## STDOUT:
## END


#### use foo.ysh --all-for-testing

echo TODO

## STDOUT:
## END
