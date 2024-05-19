## oils_failures_allowed: 8
## compare_shells: dash bash mksh zsh

#### exec builtin 
exec echo hi
## stdout: hi

#### exec builtin with redirects
exec 1>&2
echo 'to stderr'
## stdout-json: ""
## stderr: to stderr

#### exec builtin with here doc
# This has in a separate file because both code and data can be read from
# stdin.
$SH $REPO_ROOT/spec/bin/builtins-exec-here-doc-helper.sh
## STDOUT:
x=one
y=two
DONE
## END

#### exec builtin accepts --
exec -- echo hi
## STDOUT:
hi
## END
## BUG dash status: 127
## BUG dash stdout-json: ""

#### exec -- 2>&1
exec -- 3>&1
echo stdout 1>&3
## STDOUT:
stdout
## END
## BUG dash status: 127
## BUG dash stdout-json: ""
## BUG mksh status: -11
## BUG mksh stdout-json: ""

#### Exit out of function
f() { exit 3; }
f
exit 4
## status: 3

#### Exit builtin with invalid arg 
exit invalid
# Rationale: runtime errors are 1
## status: 1
## OK dash/bash status: 2
## BUG zsh status: 0

#### Exit builtin with too many args
# This is a parse error in OSH.
exit 7 8 9
echo status=$?
## status: 2
## stdout-json: ""
## BUG bash/zsh status: 0
## BUG bash/zsh stdout: status=1
## BUG dash status: 7
## BUG dash stdout-json: ""
## OK mksh status: 1
## OK mksh stdout-json: ""

#### time with brace group argument

err=_tmp/time-$(basename $SH).txt
{
  time {
    sleep 0.01
    sleep 0.02
  }
} 2> $err

grep --only-matching user $err
echo result=$?

# Regression: check fractional seconds
gawk '
BEGIN { ok = 0 }
match( $0, /\.([0-9]+)/, m) {
  if (m[1] > 0) {  # check fractional seconds
    ok = 1
  }
}
END { if (ok) { print "non-zero" } }
' $err

## status: 0
## STDOUT:
user
result=0
non-zero
## END

# time doesn't accept a block?
## BUG zsh STDOUT:
result=1
## END

# dash doesn't have time keyword
## N-I dash status: 2
## N-I dash stdout-json: ""


#### get umask
umask | grep '[0-9]\+'  # check for digits
## status: 0

#### set umask in octal
rm -f $TMP/umask-one $TMP/umask-two
umask 0002
echo one > $TMP/umask-one
umask 0022
echo two > $TMP/umask-two
stat -c '%a' $TMP/umask-one $TMP/umask-two
## status: 0
## stdout-json: "664\n644\n"
## stderr-json: ""

#### set umask symbolically
umask 0002  # begin in a known state for the test
rm -f $TMP/umask-one $TMP/umask-two
echo one > $TMP/umask-one
umask g-w,o-w
echo two > $TMP/umask-two
stat -c '%a' $TMP/umask-one $TMP/umask-two
## status: 0
## STDOUT:
664
644
## END
## stderr-json: ""

#### ulimit with no flags is like -f

ulimit > no-flags.txt
echo status=$?

ulimit -f > f.txt
echo status=$?

diff -u no-flags.txt f.txt
echo diff=$?

# Print everything
# ulimit -a

## STDOUT:
status=0
status=0
diff=0
## END


#### ulimit too many args

ulimit 1 2
if test $? -ne 0; then
  echo pass
else
  echo fail
fi

#ulimit -f

## STDOUT:
pass
## END

## BUG bash/zsh STDOUT:
fail
## END


#### ulimit negative flag

ulimit -f

# interpreted as a flag
ulimit -f -42
if test $? -ne 0; then
  echo pass
else
  echo fail
fi

## STDOUT:
unlimited
pass
## END

#### ulimit negative arg

ulimit -f

# an arg
ulimit -f -- -42
if test $? -ne 0; then
  echo pass
else
  echo fail
fi

## STDOUT:
unlimited
pass
## END

## BUG mksh STDOUT:
unlimited
fail
## END

## BUG bash STDOUT:
unlimited
unlimited
fail
## END

#### ulimit -a doesn't take arg
case $SH in bash) exit ;; esac

ulimit -a 42
if test $? -ne 0; then
  echo 'failure that was expected'
fi

## STDOUT:
failure that was expected
## END
## BUG bash STDOUT:
## END


#### ulimit doesn't accept multiple flags - reduce confusion between shells

# - bash, zsh, busybox ash accept multiple "commands", which requires custom
#   flag parsing, like

#   ulimit -f 999 -n
#   ulimit -f 999 -n 888
#
# - dash and mksh accept a single ARG
#
# we want to make it clear we're like the latter

# can't print all and -f
ulimit -f -a >/dev/null
echo status=$?

ulimit -f -n >/dev/null
echo status=$?

ulimit -f -n 999 >/dev/null
echo status=$?

## STDOUT:
status=2
status=2
status=2
## END

## BUG dash/bash/mksh STDOUT:
status=0
status=0
status=0
## END

# zsh is better - it checks that -a and -f are exclusive

## BUG zsh STDOUT:
status=1
status=0
status=0
## END



#### ulimit accepts 'unlimited'

for arg in zz unlimited; do
  echo "  arg $arg"
  ulimit -f
  echo status=$?
  ulimit -f $arg
  if test $? -ne 0; then
    echo 'FAILED'
  fi
  echo
done
## STDOUT:
  arg zz
unlimited
status=0
FAILED

  arg unlimited
unlimited
status=0

## END


#### ulimit of 2**32, 2**31 (int overflow)

echo -n 'one '; ulimit -f


ulimit -f $(( 1 << 32 ))

echo -n 'two '; ulimit -f


# mksh fails because it overflows signed int, turning into negative number
ulimit -f $(( 1 << 31 ))

echo -n 'three '; ulimit -f

## STDOUT:
one unlimited
two 4294967296
three 2147483648
## END
## BUG mksh STDOUT:
one unlimited
two 1
three 1
## END


#### ulimit of 2 ** 62

echo -n 'before '; ulimit -f

# 1 << 63 overflows signed int

# bash says this is out of range
ulimit -f $(( 1 << 62 ))

echo -n 'after '; ulimit -f

## STDOUT:
before unlimited
after unlimited
## END

## BUG dash/zsh STDOUT:
before unlimited
after 0
## END

## BUG mksh STDOUT:
before unlimited
after 1073741824
## END

#### ulimit -f 1 prevents files larger than 1024 bytes, or 512 bytes

# dash and zsh give too much spew
# mksh gives 512 byte files?

case $SH in dash|zsh|mksh) exit ;; esac

rm -f err.txt
touch err.txt

bytes() {
  local n=$1
  local st=0
  for i in $(seq $n); do
    echo -n x
    st=$?
    if test $st -ne 0; then
      echo "ERROR: echo failed with status $st" >> err.txt
    fi
  done
}


ulimit -f 1

bytes 1024 > ok.txt
echo 1024 status=$?

bytes 1025 > too-big.txt
echo 1025 status=$?
echo

wc --bytes ok.txt too-big.txt
echo

cat err.txt

## STDOUT:
1024 status=0
1025 status=0

1024 ok.txt
1024 too-big.txt
2048 total

ERROR: echo failed with status 1
## END

## BUG dash/zsh/mksh STDOUT:
## END

#### ulimit -S for soft limit (default), -H for hard limit

# note: ulimit -n -S 1111 is OK in osh/dash/mksh, but not bash/zsh

ulimit -S -n 1111
ulimit -H -n 9999

ulimit -n
ulimit -n -S
ulimit -n -H

## STDOUT:
1111
1111
9999
## END

