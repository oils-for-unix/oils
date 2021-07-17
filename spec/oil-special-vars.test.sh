#### _status

shopt --unset errexit {

  ( exit 3 )
  echo status=$_status

  ( exit 4 )

  var st = $_status
  echo st=$st
}

## STDOUT:
status=3
st=4
## END

#### _this_dir in main and oshrc

$SH $REPO_ROOT/spec/testdata/module/this_dir.oil

echo interactive

$SH -i --rcfile $REPO_ROOT/spec/testdata/module/this_dir.oil -c 'echo -c'

## STDOUT:
hi from this_dir.oil
$_this_dir = REPLACED/oil/spec/testdata/module
interactive
hi from this_dir.oil
$_this_dir = REPLACED/oil/spec/testdata/module
-c
## END

#### _this_dir not set on stdin

echo ${_this_dir:-'not yet'}
## STDOUT:
not yet
## END


#### _this_dir in sourced module
source $REPO_ROOT/spec/testdata/module/this_dir.oil
## STDOUT:
hi from this_dir.oil
$_this_dir = REPLACED/oil/spec/testdata/module
## END


#### _this_dir not affected by 'cd'
cd /tmp
source $REPO_ROOT/spec/testdata/module/this_dir.oil
## STDOUT:
hi from this_dir.oil
$_this_dir = REPLACED/oil/spec/testdata/module
## END

#### _this_dir used with relative path
cd $REPO_ROOT
source spec/testdata/module/this_dir.oil
## STDOUT:
hi from this_dir.oil
$_this_dir = REPLACED/oil/spec/testdata/module
## END
