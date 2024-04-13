
#### module
shopt --set ysh:upgrade

module 'main' || return 0
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

#### runproc
shopt --set parse_proc parse_at

f() {
  write -- f "$@"
}
proc p {
  write -- p @ARGV
}
runproc f 1 2
echo status=$?

runproc p 3 4
echo status=$?

runproc invalid 5 6
echo status=$?

runproc
echo status=$?

## STDOUT:
f
1
2
status=0
p
3
4
status=0
status=1
status=2
## END

#### runproc typed args
shopt --set parse_brace parse_proc

proc p {
  echo hi
}

# The block is ignored for now
runproc p { 
  echo myblock 
}
## STDOUT:
hi
## END

