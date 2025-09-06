## compare_shells: bash dash mksh zsh

#### can continue after unknown option 
#
# TODO: this is the posix special builtin logic?
# dash and mksh make this a fatal error no matter what.

set -o errexit
set -o STRICT || true # unknown option
echo hello
## stdout: hello
## status: 0
## BUG dash/mksh/zsh stdout-json: ""
## BUG dash status: 2
## BUG mksh/zsh status: 1

#### set with both options and argv
set -o errexit a b c
echo "$@"
false
echo done
## stdout: a b c
## status: 1


#### nounset with "$@"
set a b c
set -u  # shouldn't touch argv
echo "$@"
## stdout: a b c

#### set -u -- clears argv
set a b c
set -u -- # shouldn't touch argv
echo "$@"
## stdout: 

#### set -u -- x y z
set a b c
set -u -- x y z
echo "$@"
## stdout: x y z

#### reset option with long flag
set -o errexit
set +o errexit
echo "[$unset]"
## stdout: []
## status: 0

#### reset option with short flag
set -u 
set +u
echo "[$unset]"
## stdout: []
## status: 0

#### set -eu (flag parsing)
set -eu 
echo "[$unset]"
echo status=$?
## stdout-json: ""
## status: 1
## OK dash status: 2

#### set - -
set a b
echo "$@"
set - a b
echo "$@"
set -- a b
echo "$@"
set - -
echo "$@"
set - +
echo "$@"
set + -
echo "$@"
set -- --
echo "$@"

# note: zsh is different, and yash is totally different
## STDOUT:
a b
a b
a b
-
+
+
--
## END
## OK osh/yash STDOUT:
a b
- a b
a b
- -
- +
+ -
--
## END
## BUG mksh STDOUT:
a b
a b
a b
-
+
-
--
## END
## BUG zsh STDOUT:
a b
a b
a b

+

--
## END

#### set -o lists options
# NOTE: osh doesn't use the same format yet.
set -o | grep -o noexec
## STDOUT:
noexec
## END

#### 'set' and 'eval' round trip

# NOTE: not testing arrays and associative arrays!
_space='[ ]'
_whitespace=$'[\t\r\n]'
_sq="'single quotes'"
_backslash_dq="\\ \""
_unicode=$'[\u03bc]'

# Save the variables
varfile=$TMP/vars-$(basename $SH).txt

set | grep '^_' > "$varfile"

# Unset variables
unset _space _whitespace _sq _backslash_dq _unicode
echo [ $_space $_whitespace $_sq $_backslash_dq $_unicode ]

# Restore them

. $varfile
echo "Code saved to $varfile" 1>&2  # for debugging

test "$_space" = '[ ]' && echo OK
test "$_whitespace" = $'[\t\r\n]' && echo OK
test "$_sq" = "'single quotes'" && echo OK
test "$_backslash_dq" = "\\ \"" && echo OK
test "$_unicode" = $'[\u03bc]' && echo OK

## STDOUT:
[ ]
OK
OK
OK
OK
OK
## END

## BUG zsh status: 1
## BUG zsh STDOUT:
[ ]
## END
