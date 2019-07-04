#!/usr/bin/env bash

#### Eval
eval "a=3"
echo $a
## stdout: 3

#### Source
lib=$TMP/spec-test-lib.sh
echo 'LIBVAR=libvar' > $lib
. $lib  # dash doesn't have source
echo $LIBVAR
## stdout: libvar

#### Source nonexistent
source /nonexistent/path
echo status=$?
## stdout: status=1
## OK dash/zsh stdout: status=127

#### Source with no arguments
source
echo status=$?
## stdout: status=2
## OK mksh/zsh stdout: status=1
## N-I dash stdout: status=127

#### Source with arguments
. spec/testdata/show-argv.sh foo bar  # dash doesn't have source
## STDOUT:
show-argv: foo bar
## END
## N-I dash STDOUT:
show-argv:
## END

#### Source from a function, mutating argv and defining a local var
f() {
  . spec/testdata/source-argv.sh              # no argv
  . spec/testdata/source-argv.sh args to src  # new argv
  echo $@
  echo foo=$foo  # defined in source-argv.sh
}
f args to func
echo foo=$foo  # not defined
## STDOUT:
source-argv: args to func
source-argv: args to src
to func
foo=foo_val
foo=
## END
## N-I dash STDOUT:
source-argv: args to func
source-argv: to func
func
foo=foo_val
foo=
## END

#### Source with syntax error
# TODO: We should probably use dash behavior of a fatal error.
# Although set-o errexit handles this.  We don't want to break the invariant
# that a builtin like 'source' behaves like an external program.  An external
# program can't halt the shell!
echo 'echo >' > $TMP/syntax-error.sh
. $TMP/syntax-error.sh
echo status=$?
## stdout: status=2
## OK bash/mksh stdout: status=1
## OK zsh stdout: status=126
## OK dash stdout-json: ""
## OK dash status: 2

#### Eval with syntax error
eval 'echo >'
echo status=$?
## stdout: status=2
## OK bash/zsh stdout: status=1
## OK dash stdout-json: ""
## OK dash status: 2
## OK mksh stdout-json: ""
## OK mksh status: 1

#### Eval in does tilde expansion

x="~"
eval y="$x"  # scalar
test "$x" = "$y" || echo FALSE
[[ $x == /* ]] || echo FALSE  # doesn't start with /
[[ $y == /* ]] && echo TRUE

#argv "$x" "$y"

## STDOUT:
FALSE
FALSE
TRUE
## END
## BUG dash status: 127
## BUG dash stdout-json: "FALSE\n"
## BUG mksh status: 1
## BUG mksh stdout-json: "FALSE\n"

#### Eval in bash does tilde expansion in array

# the "make" plugin in bash-completion relies on this?  wtf?
x="~"

# UPSTREAM CODE

#eval array=( "$x" )

# FIXED CODE -- proper quoting.

eval 'array=(' "$x" ')'  # array

test "$x" = "${array[0]}" || echo FALSE
[[ $x == /* ]] || echo FALSE  # doesn't start with /
[[ "${array[0]}" == /* ]] && echo TRUE
## STDOUT:
FALSE
FALSE
TRUE
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
## BUG mksh status: 1
## BUG mksh STDOUT:
FALSE
## END
## BUG zsh status: 1
## BUG zsh STDOUT:
FALSE
FALSE
## END

#### source works for files in current directory
echo "echo current dir" > cmd
. cmd
rm cmd
## STDOUT:
current dir
## N-I dash stdout-json: ""
## N-I dash status: 2
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### source gives precendence to PATH
mkdir -p dir
echo "echo path" > dir/cmd
echo "echo current dir" > cmd
PATH="dir:$PATH"
. cmd
rm -r dir cmd
## STDOUT:
path
