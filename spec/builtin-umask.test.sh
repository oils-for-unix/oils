## compare_shells: dash bash mksh zsh
## oils_failures_allowed: 4

#### 'umask' prints the umask
umask | tail --bytes 4  # 0022 versus 022
echo status=$?

## STDOUT:
022
status=0
## END

#### 'umask -S' prints symbolic umask
umask -S | grep 'u=[rwx]*,g=[rwx]*,o=[rwx]*' 
echo status=$?

## STDOUT:
u=rwx,g=rx,o=rx
status=0
## END

#### 'umask -p' prints a form that can be eval'd
umask -p
echo status=$?

## STDOUT:
umask 0022
status=0
## END
## N-I mksh/zsh STDOUT:
status=1
## END
## N-I dash STDOUT:
status=2
## END

#### 'umask 0002' sets the umask
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

#### set umask with symbolic mode: g-w,o-w

umask 0002  # begin in a known state for the test
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

#### set umask with symbolic mode: u-rw  ...  u=,g+,o-  ...

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

#### umask with too many arguments (i.e. extra spaces)
umask 0111
# spaces are an error in bash
# dash & mksh only interpret the first one
umask u=, g+, o-
if test $? -ne 0; then
  echo ok
fi
umask | tail -c 4
## status: 0
## STDOUT:
ok
111
## END
## BUG dash/mksh STDOUT:
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

