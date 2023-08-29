
#### module
shopt --set oil:upgrade

module 'main' || return 0
source $REPO_ROOT/spec/testdata/module/common.ysh
source $REPO_ROOT/spec/testdata/module/module1.ysh
## STDOUT:
common
module1
## END


#### runproc
shopt --set parse_proc

f() {
  write -- f "$@"
}
proc p {
  write -- p "$@"
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

