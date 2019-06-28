#!/usr/bin/env bash
#
# In this file:
#
# - strict-control-flow: break/continue at the top level should be fatal!
#
# Other tests:
# - spec/errexit-strict: command subs inherit errexit
#   - TODO: does bash 4.4. use inherit_errexit?
#
# - spec/var-op-other tests strict-word-eval (negative indices and invalid
#   utf-8)
#   - hm I think these should be the default?  compat-word-eval?
#
# - spec/arith tests strict-arith - invalid strings become 0
#   - OSH has a warning that can turn into an error.  I think the error could
#     be the default (since this was a side effect of "ShellMathShock")

# - strict-array: unimplemented.
#   - WAS undef[2]=x, but bash-completion relied on the associative array
#     version of that.
#   - TODO: It should disable decay_array EVERYWHERE except a specific case like:
#     - s="${a[*]}"  # quoted, the unquoted ones glob in a command context
# - spec/dbracket has array comparison relevant to the case below
#
# Most of those options could be compat-*.
#
# One that can't: strict-scope disables dynamic scope.


#### strict-arith option
shopt -s strict-arith
## status: 0
## N-I bash status: 1
## N-I dash/mksh status: 127

#### Sourcing a script that returns at the top level
echo one
. spec/testdata/return-helper.sh
echo $?
echo two
## STDOUT:
one
return-helper.sh
42
two
## END

#### top level control flow
$SH spec/testdata/top-level-control-flow.sh
## status: 0
## STDOUT:
SUBSHELL
BREAK
CONTINUE
RETURN
## OK bash STDOUT:
SUBSHELL
BREAK
CONTINUE
RETURN
DONE
## END

#### errexit and top-level control flow
$SH -o errexit spec/testdata/top-level-control-flow.sh
## status: 2
## OK bash status: 1
## STDOUT:
SUBSHELL
## END

#### shopt -s strict-control-flow
shopt -s strict-control-flow || true
echo break
break
echo hi
## STDOUT:
break
## END
## status: 1
## N-I dash/bash/mksh STDOUT:
break
hi
# END
## N-I dash/bash/mksh status: 0

#### return at top level is an error
return
echo "status=$?"
## stdout-json: ""
## OK bash STDOUT:
status=1
## END

#### continue at top level is NOT an error
# NOTE: bash and mksh both print warnings, but don't exit with an error.
continue
echo status=$?
## stdout: status=0

#### break at top level is NOT an error
break
echo status=$?
## stdout: status=0

#### empty argv WITHOUT strict-argv
x=''
$x
echo status=$?

if $x; then
  echo VarSub
fi

if $(echo foo >/dev/null); then
  echo CommandSub
fi

if "$x"; then
  echo VarSub
else
  echo VarSub FAILED
fi

if "$(echo foo >/dev/null)"; then
  echo CommandSub
else
  echo CommandSub FAILED
fi

## STDOUT:
status=0
VarSub
CommandSub
VarSub FAILED
CommandSub FAILED
## END

#### strict-argv: no first word but exit code (DUPE of if `false` ??)

# POSIX has a special rule for this.  In OSH strict-argv is preferred so it
# becomes a moot point.  I think this is an artifact of the
# "stateful"/imperative nature of $? -- it can be "left over" from a prior
# command, and sometimes the prior argv is [].  OSH has a more "functional"
# implementation so it doesn't have this weirdness.

if $(false); then
  echo TRUE
else
  echo FALSE
fi
## STDOUT:
FALSE
## END

#### empty argv WITH strict-argv
shopt -s strict-argv || true
echo empty
x=''
$x
echo status=$?
## status: 1
## STDOUT:
empty
## END
## N-I dash/bash/mksh status: 0
## N-I dash/bash/mksh STDOUT:
empty
status=0
## END

#### Arrays should not be incorrectly compared like bash/mksh

# NOTE: from spec/dbracket has a test case like this
# sane-array should turn this ON.
# bash and mksh allow this because of decay

a=('a b' 'c d')
b=('a' 'b' 'c' 'd')
echo ${#a[@]}
echo ${#b[@]}
[[ "${a[@]}" == "${b[@]}" ]] && echo EQUAL
## status: 1
## STDOUT:
2
4
## END
## BUG bash/mksh status: 0
## BUG bash/mksh STDOUT:
2
4
EQUAL
## END
## N-I dash status: 2
## N-I dash stdout-json: ""

#### automatically creating arrays WITHOUT strict-array
undef[2]=x
undef[3]=y
argv "${undef[@]}"
## STDOUT:
['x', 'y']
## END
## N-I dash status: 2
## N-I dash stdout-json: ""

#### automatically creating arrays are INDEXED, not associative

undef[2]=x
undef[3]=y
x='bad'
# bad gets coerced to zero, but this is part of the RECURSIVE arithmetic
# behavior, which we want to disallow.  Consider disallowing in OSH.

undef[$x]=zzz
argv "${undef[@]}"
## STDOUT:
['zzz', 'x', 'y']
## END
## N-I dash status: 2
## N-I dash stdout-json: ""
