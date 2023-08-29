## our_shell: ysh

#### _this_dir in main and oshrc

$SH $REPO_ROOT/spec/testdata/module/this_dir.ysh

echo interactive

$SH -i --rcfile $REPO_ROOT/spec/testdata/module/this_dir.ysh -c 'echo -c'

## STDOUT:
hi from this_dir.ysh
$_this_dir = REPLACED/oil/spec/testdata/module
interactive
hi from this_dir.ysh
$_this_dir = REPLACED/oil/spec/testdata/module
-c
## END

#### _this_dir not set on stdin

echo ${_this_dir:-'not yet'}
## STDOUT:
not yet
## END


#### _this_dir in sourced module
source $REPO_ROOT/spec/testdata/module/this_dir.ysh
## STDOUT:
hi from this_dir.ysh
$_this_dir = REPLACED/oil/spec/testdata/module
## END


#### _this_dir not affected by 'cd'
cd /tmp
source $REPO_ROOT/spec/testdata/module/this_dir.ysh
## STDOUT:
hi from this_dir.ysh
$_this_dir = REPLACED/oil/spec/testdata/module
## END

#### _this_dir used with relative path
cd $REPO_ROOT
source spec/testdata/module/this_dir.ysh
## STDOUT:
hi from this_dir.ysh
$_this_dir = REPLACED/oil/spec/testdata/module
## END
