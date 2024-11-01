## oils_failures_allowed: 1
## compare_shells: dash bash mksh zsh

#### cd and $PWD
cd /
echo $PWD
## stdout: /

#### cd BAD/..

# Odd divergence in shells: dash and mksh normalize the path and don't check
# this error.
# TODO: I would like OSH to behave like bash and zsh, but separating chdir_arg
# and pwd_arg breaks case 17.

cd nonexistent_ZZ/..
echo status=$?
## STDOUT:
status=1
## END
## BUG dash/mksh STDOUT:
status=0
## END

#### cd with 2 or more args

mkdir -p foo
cd foo
echo status=$?
cd ..
echo status=$?


cd foo bar
st=$?
if test $st -ne 0; then
  echo 'failed with multiple args'
fi

## STDOUT:
status=0
status=0
failed with multiple args
## END

## BUG dash STDOUT:
status=0
status=0
## END

#### cd - without OLDPWD

cd - > /dev/null  # silence dash output
echo status=$?
#pwd

## STDOUT:
status=1
## END

## OK mksh STDOUT:
status=2
## END

## BUG dash/zsh STDOUT:
status=0
## END

#### $OLDPWD
cd /
cd $TMP
echo "old: $OLDPWD"
env | grep OLDPWD  # It's EXPORTED too!
cd -
## STDOUT:
old: /
OLDPWD=/
/
## END
## BUG mksh STDOUT:
old: /
/
## END
## BUG zsh STDOUT:
old: /
OLDPWD=/
## END

#### pwd
cd /
pwd
## STDOUT:
/
## END

#### pwd after cd ..
dir=$TMP/dir-one/dir-two
mkdir -p $dir
cd $dir
echo $(basename $(pwd))
cd ..
echo $(basename $(pwd))
## STDOUT:
dir-two
dir-one
## END

#### pwd with symlink and -P
tmp=$TMP/builtins-pwd-1
mkdir -p $tmp/target
ln -s -f $tmp/target $tmp/symlink

cd $tmp/symlink

echo pwd:
basename $(pwd)

echo pwd -P:
basename $(pwd -P)

## STDOUT:
pwd:
symlink
pwd -P:
target
## END

#### setting $PWD doesn't affect the value of 'pwd' builtin
dir=/tmp/oil-spec-test/pwd
mkdir -p $dir
cd $dir

PWD=foo
echo before $PWD
pwd
echo after $PWD
## STDOUT:
before foo
/tmp/oil-spec-test/pwd
after foo
## END

#### unset PWD; then pwd
dir=/tmp/oil-spec-test/pwd
mkdir -p $dir
cd $dir

unset PWD
echo PWD=$PWD
pwd
echo PWD=$PWD
## STDOUT:
PWD=
/tmp/oil-spec-test/pwd
PWD=
## END

#### 'unset PWD; pwd' before any cd (tickles a rare corner case)
dir=/tmp/oil-spec-test/pwd-2
mkdir -p $dir
cd $dir

# ensure clean shell process state
$SH -c 'unset PWD; pwd'

## STDOUT:
/tmp/oil-spec-test/pwd-2
## END

#### lie about PWD; pwd before any cd
dir=/tmp/oil-spec-test/pwd-3
mkdir -p $dir
cd $dir

# ensure clean shell process state
$SH -c 'PWD=foo; pwd'

## STDOUT:
/tmp/oil-spec-test/pwd-3
## END

#### remove pwd dir
dir=/tmp/oil-spec-test/pwd
mkdir -p $dir
cd $dir
pwd
rmdir $dir
echo status=$?
pwd
echo status=$?
## STDOUT:
/tmp/oil-spec-test/pwd
status=0
/tmp/oil-spec-test/pwd
status=0
## END
## OK mksh STDOUT:
/tmp/oil-spec-test/pwd
status=0
status=1
## END

#### pwd in symlinked dir on shell initialization
tmp=$TMP/builtins-pwd-2
mkdir -p $tmp
mkdir -p $tmp/target
ln -s -f $tmp/target $tmp/symlink

cd $tmp/symlink
$SH -c 'basename $(pwd)'
unset PWD
$SH -c 'basename $(pwd)'

## STDOUT:
symlink
target
## END
## OK mksh STDOUT:
target
target
## END
## stderr-json: ""

#### Test the current directory after 'cd ..' involving symlinks
dir=$TMP/symlinktest
mkdir -p $dir
cd $dir
mkdir -p a/b/c
mkdir -p a/b/d
ln -s -f a/b/c c > /dev/null
cd c
cd ..
# Expecting a c/ (since we are in symlinktest) but osh gives c d (thinks we are
# in b/)
ls
## STDOUT:
a
c
## END

#### cd with no arguments
HOME=$TMP/home
mkdir -p $HOME
cd
test $(pwd) = "$HOME" && echo OK
## stdout: OK

#### cd to nonexistent dir
cd /nonexistent/dir
echo status=$?
## stdout: status=1
## OK dash/mksh stdout: status=2

#### cd away from dir that was deleted
dir=$TMP/cd-nonexistent
mkdir -p $dir
cd $dir
rmdir $dir
cd $TMP
echo $(basename $OLDPWD)
echo status=$?
## STDOUT:
cd-nonexistent
status=0
## END

#### cd permits double bare dash
cd -- /
echo $PWD
## stdout: /

#### cd to symlink with -L and -P
targ=$TMP/cd-symtarget
lnk=$TMP/cd-symlink
mkdir -p $targ
ln -s $targ $lnk

# -L behavior is the default
cd $lnk
test $PWD = "$TMP/cd-symlink" && echo OK

cd -L $lnk
test $PWD = "$TMP/cd-symlink" && echo OK

cd -P $lnk
test $PWD = "$TMP/cd-symtarget" && echo OK || echo $PWD
## STDOUT:
OK
OK
OK
## END

#### cd to relative path with -L and -P
die() { echo "$@"; exit 1; }

targ=$TMP/cd-symtarget/subdir
lnk=$TMP/cd-symlink
mkdir -p $targ
ln -s $TMP/cd-symtarget $lnk

# -L behavior is the default
cd $lnk/subdir
test $PWD = "$TMP/cd-symlink/subdir" || die "failed"
cd ..
test $PWD = "$TMP/cd-symlink" && echo OK

cd $lnk/subdir
test $PWD = "$TMP/cd-symlink/subdir" || die "failed"
cd -L ..
test $PWD = "$TMP/cd-symlink" && echo OK

cd $lnk/subdir
test $PWD = "$TMP/cd-symlink/subdir" || die "failed"
cd -P ..
test $PWD = "$TMP/cd-symtarget" && echo OK || echo $PWD
## STDOUT:
OK
OK
OK
## END


#### unset PWD; cd /tmp is allowed (regression)

unset PWD; cd /tmp
pwd

## STDOUT:
/tmp
## END



