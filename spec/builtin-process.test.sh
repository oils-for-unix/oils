## compare_shells: dash bash mksh zsh
## oils_failures_allowed: 4
## oils_cpp_failures_allowed: 5
# case #24 with ulimit -f 1 is different under C++ for some reason - could be due to the python2
# intepreter and SIGXFSZ

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

err=time-$(basename $SH).txt
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
## STDOUT:
664
644
## END
## stderr-json: ""

#### set umask symbolically
umask 0002  # begin in a known state for the test
rm -f $TMP/umask-one $TMP/umask-two
# open()s 'umask-one' with mask 0666, then subtracts 0002 -> 0664
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

#### umask -p
umask -p | grep 'umask [0-9][0-9][0-9][0-9]'
## status: 0
## N-I dash/mksh/zsh status: 1

#### umask -S
# current mask as symbolic
umask -S | grep 'u=[rwx]*,g=[rwx]*,o=[rwx]*' 
## status: 0

#### umask symbolic parsing

umask 0000
umask u-rw
echo status0=$?
umask | tail -c 4

umask 0700
umask u=r
echo status1=$?
umask | tail -c 4

umask 0000
umask u=r,g=w,o=x
echo status2=$?
umask | tail -c 4

umask 0777
umask u+r,g+w,o+x
echo status3=$?
umask | tail -c 4

umask 0000
umask u-r,g-w,o-x
echo status4=$?
umask | tail -c 4

umask 0137
umask u=,g+,o-
echo status5=$?
umask | tail -c 4

## status: 0
## STDOUT:
status0=0
600
status1=0
300
status2=0
356
status3=0
356
status4=0
421
status5=0
737
## END

#### umask symbolic parsing with spaces
umask 0111
# spaces are an error in bash
# dash & mksh only interpret the first one
umask u=, g+, o-
echo status=$?
umask | tail -c 4
## status: 0
## STDOUT:
status=2
111
## END
## OK bash/zsh STDOUT:
status=1
111
## END
## BUG dash/mksh STDOUT:
status=0
711
## END

#### umask bad symbolic input
umask b=rwx
## status: 1
## OK dash status: 2

#### umask octal number out of range
umask 0022
umask 1234567
# osh currently treats 0o1234567 as 0o0567
echo status=$?
umask | tail -c 4
## status: 0
## STDOUT:
status=1
022
## END
## BUG mksh/zsh/dash STDOUT:
status=0
567
## END

#### umask allow overwriting and duplicates
umask 0111
umask u=rwx,u=rw,u=r,u=,g=rwx
umask | tail -c 4
## status: 0
## STDOUT:
701
## END

#### umask a is valid who
umask 0732
umask a=rwx
umask | tail -c 4

umask 0124
umask a+r
umask | tail -c 4

umask 0124
umask a-r
umask | tail -c 4
## status: 0
## STDOUT:
000
120
564
## END

#### umask X perm
umask 0124
umask a=X
echo ret0 = $?
umask | tail -c 4

umask 0246
umask a=X
echo ret1 = $?
umask | tail -c 4

umask 0246
umask a-X
echo ret2 = $?
umask | tail -c 4
## status: 0
## STDOUT:
ret0 = 0
666
ret1 = 0
777
ret2 = 0
246
## END
## BUG dash/mksh STDOUT:
ret0 = 0
666
ret1 = 0
666
ret2 = 0
357
## END
## N-I bash/zsh STDOUT:
ret0 = 1
124
ret1 = 1
246
ret2 = 1
246
## END

#### umask s perm
umask 0124
umask a-s
echo ret0 = $?
umask | tail -c 4

umask 0124
umask a+s
echo ret1 = $?
umask | tail -c 4

umask 0124
umask a=s
echo ret2 = $?
umask | tail -c 4
## status: 0
## STDOUT: 
ret0 = 0
124
ret1 = 0
124
ret2 = 0
777
## END
## N-I bash/zsh STDOUT:
ret0 = 1
124
ret1 = 1
124
ret2 = 1
124
## END

#### umask t perm
umask 0124
umask a-t
echo ret0 = $?
umask | tail -c 4

umask 0124
umask a+t
echo ret1 = $?
umask | tail -c 4

umask 0124
umask a=t
echo ret2 = $?
umask | tail -c 4
## status: 0
## STDOUT: 
ret0 = 0
124
ret1 = 0
124
ret2 = 0
777
## END
## N-I bash/zsh/mksh STDOUT:
ret0 = 1
124
ret1 = 1
124
ret2 = 1
124
## END
## N-I dash STDOUT:
ret0 = 2
124
ret1 = 2
124
ret2 = 2
124
## END

#### umask default who
umask 0124
umask =
umask | tail -c 4

umask 0124
umask =rx
echo ret = $?
umask | tail -c 4

umask 0124
umask +
umask | tail -c 4

umask 0124
# zsh ALSO treats this as just `umask`
umask - >/dev/null
umask | tail -c 4
## status: 0
## BUG zsh status: 1
## STDOUT: 
777
ret = 0
222
124
124
## END
## BUG zsh STDOUT:
777
## END

#### umask bare op
umask 0124
umask =+=
umask | tail -c 4

umask 0124
umask +=
umask | tail -c 4

umask 0124
umask =+rwx+rx
umask | tail -c 4
## status: 0
## BUG zsh status: 1
## STDOUT: 
777
777
000
## END
## N-I bash STDOUT: 
124
124
124
## END
## BUG zsh STDOUT: 
## END

#### umask bare op -
umask 0124
umask -rwx
umask | tail -c 4

umask 0124
umask -wx
umask | tail -c 4

umask 0124
umask -=+
umask | tail -c 4
## status: 0
## STDOUT:
777
337
777
## END
## N-I dash/bash/mksh/zsh STDOUT:
124
124
124
## END

#### umask permcopy
umask 0124 
umask a=u
umask | tail -c 4

umask 0365
umask a=g
umask | tail -c 4

umask 0124
umask a=o
umask | tail -c 4
## status: 0
## STDOUT:
111
666
444
## END
## N-I bash/zsh STDOUT:
124
365
124
## END

#### umask permcopy running value
umask 0124
umask a=,a=u
umask | tail -c 4

umask 0124
umask a=
umask a=u
umask | tail -c 4
## status: 0
## STDOUT:
111
777
## END
## N-I bash/zsh STDOUT:
124
777
## END

#### umask sequential actions
umask 0124
umask u+r+w+x
umask | tail -c 4

umask 0124
umask a+r+w+x,o-w
umask | tail -c 4

umask 0124
umask a+x+wr-r
umask | tail -c 4
## status: 0
## STDOUT: 
024
002
444
## END
## N-I bash/zsh STDOUT:
124
124
124
## END


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


#### YSH readability: ulimit --all the same as ulimit -a

case $SH in bash|dash|mksh|zsh) exit ;; esac

ulimit -a > short.txt
ulimit --all > long.txt

wc -l short.txt long.txt

diff -u short.txt long.txt
echo status=$?

## STDOUT:
  8 short.txt
  8 long.txt
 16 total
status=0
## END

## N-I bash/dash/mksh/zsh STDOUT:
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


#### ulimit that is 64 bits

# no 64-bit integers
case $SH in mksh) exit ;; esac

echo -n 'before '; ulimit -f

# 1 << 63 overflows signed int

# 512 is 1 << 9, so make it 62-9 = 53 bits

lim=$(( 1 << 53 ))
#echo $lim

# bash says this is out of range
ulimit -f $lim

echo -n 'after '; ulimit -f

## STDOUT:
before unlimited
after 9007199254740992
## END

## BUG mksh STDOUT:
## END


#### arg that would overflow 64 bits is detected

# no 64-bit integers
case $SH in mksh) exit ;; esac

echo -n 'before '; ulimit -f

# 1 << 63 overflows signed int

lim=$(( (1 << 62) + 1 ))
#echo lim=$lim

# bash detects that this is out of range
# so does osh-cpp, but not osh-cpython

ulimit -f $lim
echo -n 'after '; ulimit -f

## STDOUT:
before unlimited
after unlimited
## END

## BUG dash/zsh STDOUT:
before unlimited
after 1
## END

## BUG mksh STDOUT:
## END


#### ulimit -f 1 prevents files larger 512 bytes
trap - XFSZ  # don't handle this

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

bytes 512 > ok.txt
echo 512 status=$?

bytes 513 > too-big.txt
echo 513 status=$?
echo

wc --bytes ok.txt too-big.txt
echo

cat err.txt

## status: -25
## STDOUT:
512 status=0
## END

## OK disabledosh status: 0
## OK disabledosh STDOUT:
512 status=0
513 status=0

 512 ok.txt
 512 too-big.txt
1024 total

ERROR: echo failed with status 1
## END

## BUG bash status: 0
## BUG bash STDOUT:
512 status=0
513 status=0

 512 ok.txt
 513 too-big.txt
1025 total

## END

#### write big file with ulimit

# I think this will test write() errors, rather than the final flush() error
# (which is currently skipped by C++

{ echo 'ulimit -f 1'
  # More than 8 KiB may cause a flush()
  python2 -c 'print("echo " + "X"*9000 + " >out.txt")'
  echo 'echo inner=$?'
} > big.sh

$SH big.sh
echo outer=$?

## STDOUT:
outer=153
## END

# not sure why this is different
## OK osh STDOUT:
inner=1
outer=0
## END


#### ulimit -S for soft limit (default), -H for hard limit
case $SH in dash|zsh) exit ;; esac

# Note: ulimit -n -S 1111 is OK in osh/dash/mksh, but not bash/zsh
# Mus be ulimit -S -n 1111

show_state() {
  local msg=$1
  echo "$msg"
  echo -n '  '; ulimit -S -t
  echo -n '  '; ulimit -H -t
  echo
}

show_state 'init'

ulimit -S -t 123456
show_state '-S'

ulimit -H -t 123457
show_state '-H'

ulimit -t 123455
show_state 'no flag'

echo 'GET'

ulimit -S -t 123454
echo -n '  '; ulimit -t
echo -n '  '; ulimit -S -t
echo -n '  '; ulimit -H -t

## STDOUT:
init
  unlimited
  unlimited

-S
  123456
  unlimited

-H
  123456
  123457

no flag
  123455
  123455

GET
  123454
  123454
  123455
## END

## BUG dash/zsh STDOUT:
## END

#### Changing resource limit is denied

# Not sure why these don't work
case $SH in dash|mksh) exit ;; esac


flag=-t

ulimit -S -H $flag 100
echo both=$?

ulimit -S $flag 90
echo soft=$?

ulimit -S $flag 95
echo soft=$?

ulimit -S $flag 105
if test $? -ne 0; then
  echo soft OK
else
  echo soft fail
fi

ulimit -H $flag 200
if test $? -ne 0; then
  echo hard OK
else
  echo hard fail
fi

## STDOUT:
both=0
soft=0
soft=0
soft OK
hard OK
## END

## BUG dash/mksh STDOUT:
## END

#### ulimit -n limits file descriptors

# OSH bug
# https://oilshell.zulipchat.com/#narrow/channel/502349-osh/topic/alpine.20build.20failures.20-.20make.20-.20ulimit.20-n.2064/with/519691301

$SH -c 'ulimit -n 64; echo hi >out'
echo status=$?

$SH -c 'ulimit -n 0; echo hi >out'
echo status=$?

## STDOUT:
status=0
status=1
## END

## OK dash STDOUT:
status=0
status=2
## END
