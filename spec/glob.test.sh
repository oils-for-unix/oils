#
# NOTE: Could move spec/03-glob.sh here.

#### glob double quote escape
echo "*.sh"
## stdout: *.sh

#### glob single quote escape
echo "*.sh"
## stdout: *.sh

#### glob backslash escape
echo \*.sh
## stdout: *.sh

#### 1 char glob
cd $REPO_ROOT
echo [b]in
## stdout: bin

#### 0 char glob -- does NOT work
echo []bin
## stdout: []bin

#### looks like glob at the start, but isn't
echo [bin
## stdout: [bin

#### looks like glob plus negation at the start, but isn't
echo [!bin
## stdout: [!bin

#### glob can expand to command and arg
cd $REPO_ROOT
spec/testdata/echo.s[hz]
## stdout: spec/testdata/echo.sz

#### glob after var expansion
touch _tmp/a.A _tmp/aa.A _tmp/b.B
f="_tmp/*.A"
g="$f _tmp/*.B"
echo $g
## stdout: _tmp/a.A _tmp/aa.A _tmp/b.B

#### quoted var expansion with glob meta characters
touch _tmp/a.A _tmp/aa.A _tmp/b.B
f="_tmp/*.A"
echo "[ $f ]"
## stdout: [ _tmp/*.A ]

#### glob after "$@" expansion
fun() {
  echo "$@"
}
fun '_tmp/*.B'
## stdout: _tmp/*.B

#### glob after $@ expansion
touch _tmp/b.B
fun() {
  echo $@
}
fun '_tmp/*.B'
## stdout: _tmp/b.B

#### no glob after ~ expansion
HOME=*
echo ~/*.py
## stdout: */*.py

#### store literal globs in array then expand
touch _tmp/a.A _tmp/aa.A _tmp/b.B
g=("_tmp/*.A" "_tmp/*.B")
echo ${g[@]}
## stdout: _tmp/a.A _tmp/aa.A _tmp/b.B
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2

#### glob inside array
touch _tmp/a.A _tmp/aa.A _tmp/b.B
g=(_tmp/*.A _tmp/*.B)
echo "${g[@]}"
## stdout: _tmp/a.A _tmp/aa.A _tmp/b.B
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2

#### glob with escaped - in char class
touch _tmp/foo.-
touch _tmp/c.C
echo _tmp/*.[C-D] _tmp/*.[C\-D]
## stdout: _tmp/c.C _tmp/c.C _tmp/foo.-

#### glob with char class expression
# note: mksh doesn't support [[:punct:]] ?
touch _tmp/e.E _tmp/foo.-
echo _tmp/*.[[:punct:]E]
## stdout: _tmp/e.E _tmp/foo.-
## BUG mksh stdout: _tmp/*.[[:punct:]E]

#### glob double quotes
# note: mksh doesn't support [[:punct:]] ?
touch _tmp/\"quoted.py\"
echo _tmp/\"*.py\"
## stdout: _tmp/"quoted.py"

#### glob escaped
# - mksh doesn't support [[:punct:]] ?
# - python shell fails because \[ not supported!
touch _tmp/\[abc\] _tmp/\?
echo _tmp/\[???\] _tmp/\?
## stdout: _tmp/[abc] _tmp/?

#### : escaped
touch _tmp/foo.-
echo _tmp/*.[[:punct:]] _tmp/*.[[:punct\:]]
## stdout: _tmp/foo.- _tmp/*.[[:punct:]]
## BUG mksh stdout: _tmp/*.[[:punct:]] _tmp/*.[[:punct:]]
## BUG ash stdout: _tmp/foo.- _tmp/foo.-

#### Glob after var manipulation
touch _tmp/foo.zzz _tmp/bar.zzz
g='_tmp/*.zzzZ'
echo $g ${g%Z}
## stdout: _tmp/*.zzzZ _tmp/bar.zzz _tmp/foo.zzz

#### Glob after part joining
touch _tmp/foo.yyy _tmp/bar.yyy
g='_tmp/*.yy'
echo $g ${g}y
## stdout: _tmp/*.yy _tmp/bar.yyy _tmp/foo.yyy

#### Glob flags on file system
touch _tmp/-n _tmp/zzzzz
cd _tmp
echo -* hello zzzz?
## stdout-json: "hello zzzzz"

#### set -o noglob
cd $REPO_ROOT
touch _tmp/spec-tmp/a.zz _tmp/spec-tmp/b.zz
echo _tmp/spec-tmp/*.zz
set -o noglob
echo _tmp/spec-tmp/*.zz
## stdout-json: "_tmp/spec-tmp/a.zz _tmp/spec-tmp/b.zz\n_tmp/spec-tmp/*.zz\n"

#### set -o noglob (bug #698)
var='\z'
set -f
echo $var
## STDOUT:
\z
## END

#### shopt -s nullglob
argv.py _tmp/spec-tmp/*.nonexistent
shopt -s nullglob
argv.py _tmp/spec-tmp/*.nonexistent
## stdout-json: "['_tmp/spec-tmp/*.nonexistent']\n[]\n"
## N-I dash/mksh/ash stdout-json: "['_tmp/spec-tmp/*.nonexistent']\n['_tmp/spec-tmp/*.nonexistent']\n"

#### shopt -s failglob in command context
argv.py *.ZZ
shopt -s failglob
argv.py *.ZZ  # nothing is printed, not []
echo status=$?
## STDOUT:
['*.ZZ']
status=1
## END
## N-I dash/mksh/ash STDOUT:
['*.ZZ']
['*.ZZ']
status=0
## END

#### shopt -s failglob in loop context
for x in *.ZZ; do echo $x; done
echo status=$?
shopt -s failglob
for x in *.ZZ; do echo $x; done
echo status=$?
## STDOUT:
*.ZZ
status=0
status=1
## END
## N-I dash/mksh/ash STDOUT:
*.ZZ
status=0
*.ZZ
status=0
## END

#### shopt -s failglob in array literal context
myarr=(*.ZZ)
echo "${myarr[@]}"
shopt -s failglob
myarr=(*.ZZ)
echo status=$?
## STDOUT:
*.ZZ
status=1
## END
## N-I mksh STDOUT:
*.ZZ
status=0
## END
## N-I dash/ash stdout-json: ""
## N-I dash/ash status: 2

#### shopt -s failglob exits properly in command context with set -e
set -e
argv.py *.ZZ
shopt -s failglob
argv.py *.ZZ
echo status=$?
## STDOUT:
['*.ZZ']
## END
## status: 1
## N-I dash/mksh/ash STDOUT:
['*.ZZ']
## END
## N-I dash/mksh/ash status: 127

#### shopt -s failglob exits properly in loop context with set -e
set -e
for x in *.ZZ; do echo $x; done
echo status=$?
shopt -s failglob
for x in *.ZZ; do echo $x; done
echo status=$?
## STDOUT:
*.ZZ
status=0
## END
## status: 1
## N-I dash/mksh/ash STDOUT:
*.ZZ
status=0
## END
## N-I dash/mksh/ash status: 127

#### shopt -s failglob behavior on single line with semicolon
# bash behaves differently when commands are separated by a semicolon than when
# separated by a newline. This behavior doesn't make sense or seem to be
# intentional, so osh does not mimic it.

shopt -s failglob
echo *.ZZ; echo status=$? # bash doesn't execute the second part!
echo *.ZZ
echo status=$? # bash executes this

## STDOUT:
status=1
## END

## OK osh STDOUT:
status=1
status=1
## END

## N-I dash/mksh/ash STDOUT:
*.ZZ
status=0
*.ZZ
status=0
## END

#### Don't glob flags on file system with GLOBIGNORE
# This is a bash-specific extension.
expr $0 : '.*/osh$' >/dev/null && exit 99  # disabled until cd implemented
touch _tmp/-n _tmp/zzzzz
cd _tmp  # this fail in osh
GLOBIGNORE=-*:zzzzz  # colon-separated pattern list
echo -* hello zzzz?
## stdout-json: "-* hello zzzz?\n"
## N-I dash/mksh/ash stdout-json: "hello zzzzz"
## status: 0

#### Splitting/Globbing doesn't happen on local assignment
cd $REPO_ROOT

f() {
  # Dash splits words and globs before handing it to the 'local' builtin.  But
  # ash doesn't!
  local foo=$1
  echo "$foo"
}
f 'void *'
## stdout: void *
## BUG dash stdout-json: ""
## BUG dash status: 2

#### Glob of unescaped [[] and []]
touch $TMP/[ $TMP/]
cd $TMP
echo [\[z] [\]z]  # the right way to do it
echo [[z] []z]    # also accepted
## STDOUT:
[ ]
[ ]
## END

#### Glob of negated unescaped [[] and []]
# osh does this "correctly" because it defers to libc!
touch $TMP/_G
cd $TMP
echo _[^\[z] _[^\]z]  # the right way to do it
echo _[^[z] _[^]z]    # also accepted
## STDOUT:
_G _G
_G _G
## END
## BUG dash/mksh STDOUT:
_[^[z] _[^]z]
_[^[z] _[^]z]
## END

#### PatSub of unescaped [[] and []]
x='[foo]'
echo ${x//[\[z]/<}  # the right way to do it
echo ${x//[\]z]/>}
echo ${x//[[z]/<}  # also accepted
echo ${x//[]z]/>}
## STDOUT:
<foo]
[foo>
<foo]
[foo>
## END
## N-I dash stdout-json: ""
## N-I dash status: 2

#### PatSub of negated unescaped [[] and []]
x='[foo]'
echo ${x//[^\[z]/<}  # the right way to do it
echo ${x//[^\]z]/>}
echo ${x//[^[z]/<}  # also accepted
#echo ${x//[^]z]/>}  # only busybox ash interprets as ^\]
## STDOUT:
[<<<<
>>>>]
[<<<<
## END
# mksh is doing something very odd, ignoring ^ altogether?
## BUG mksh STDOUT:
<foo]
[foo>
<foo]
## END
## N-I dash stdout-json: ""
## N-I dash status: 2

#### Glob unicode char

touch $TMP/__a__
touch $TMP/__μ__
cd $TMP

echo __?__

## STDOUT:
__a__ __μ__
## END
## BUG dash/mksh/ash STDOUT:
__a__
## END
# note: zsh also passes this, but it doesn't run with this file.

#### dotglob (bash option that dashglob is roughly consistent with)
mkdir -p $TMP/dotglob
cd $TMP/dotglob
touch .foorc other

echo *
shopt -s dotglob
echo *
## STDOUT:
other
.foorc other
## END
## N-I dash/mksh/ash STDOUT:
other
other
## END
